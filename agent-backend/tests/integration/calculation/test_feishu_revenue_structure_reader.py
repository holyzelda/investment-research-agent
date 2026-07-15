"""表2《各省收益结构》飞书真读 · 桩测试（httpx MockTransport，不连真网络）。

覆盖：token → sheets/query(v3) → values_batch_get(v2) 三步链路；A:S 列映射到省份画像；
空行跳过；未知省份返回 None。
"""
import httpx
import pytest

from app.core.config.settings import FeishuConfig
from app.modules.calculation.infrastructure.revenue_structure_reader import (
    FeishuRevenueStructureReader,
)

# A地区 B中长期 C/D两档 E现货 F调频 G/H两档 I容量 J补贴 K租赁 L单价 M达成率
# N干预 O/P两档 Q其他 R收过网费 S返还过网费  —— 与 param_dict 列布局一致
_GANSU = ["甘肃", 0, None, None, 1, 1, None, None, 1, 0, 0, None, None, 0, None, None, "", 1, 0]
_NINGXIA = ["宁夏", 1, 240, 480, 1, 1, 100, 200, 1, 0, 1, 20, 0.9, 1, 330, 540, "", 1, 1]
_BLANK = ["", "", ""]   # 表尾冗余空行（A4:S40 会带出来）


def _handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    if p.endswith("/tenant_access_token/internal"):
        return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-1", "expire": 7200})
    if p.endswith("/sheets/query"):
        return httpx.Response(200, json={"code": 0, "data": {
            "sheets": [{"sheet_id": "shtRev", "title": "各省收益结构"}]}})
    if p.endswith("/values_batch_get"):
        return httpx.Response(200, json={"code": 0, "data": {"valueRanges": [
            {"range": "shtRev!A4:S40", "values": [_GANSU, _NINGXIA, _BLANK]}]}})
    return httpx.Response(404, json={"code": 1, "msg": "nope"})


def _reader() -> FeishuRevenueStructureReader:
    FeishuRevenueStructureReader.cache_clear()  # 防跨用例缓存泄漏
    cfg = FeishuConfig(
        enabled=True, app_id="a", app_secret="s",
        revenue_structure_token="rev", revenue_structure_sheet="各省收益结构",
        revenue_structure_range="A4:S40",
    )
    client = httpx.Client(transport=httpx.MockTransport(_handler), base_url="https://open.feishu.cn")
    return FeishuRevenueStructureReader(config=cfg, ttl=0.0, client=client)  # ttl=0 每次重读


def test_reads_and_maps_switches():
    p = _reader().get_profile("甘肃")
    assert p is not None
    assert p.mid_long == 0 and p.spot == 1 and p.frequency == 1 and p.capacity == 1
    assert p.collect_grid_fee == 1 and p.return_grid_fee == 0


def test_maps_tiers_and_lease():
    p = _reader().get_profile("宁夏")
    assert p.mid_long_tier.t2 == 240 and p.mid_long_tier.t4 == 480
    assert p.frequency_tier.t2 == 100 and p.frequency_tier.t4 == 200
    assert p.intervention_tier.t2 == 330 and p.intervention_tier.t4 == 540
    assert p.lease_unit_price == 20 and p.lease_achievement_rate == 0.9


def test_empty_tiers_are_none():
    p = _reader().get_profile("甘肃")  # 甘肃两档留空
    assert p.mid_long_tier.t2 is None and p.frequency_tier.t4 is None
    assert p.lease_unit_price is None


def test_unknown_province_returns_none():
    assert _reader().get_profile("火星省") is None


def test_blank_row_skipped():
    r = _reader()
    r.get_profile("甘肃")            # 触发整表加载
    assert "" not in r._table()      # 空行未变成"省份"
