"""飞书电子表格网关（真实实现）· 关键节点测试（httpx 打桩，不连真网络）。

只测有价值的契约点：
1. 复制副本携带 Bearer token、目标文件夹，返回新副本 token。
2. write_input 按参数字典 api_cell 映射到 <sheetId>!cell（标题→sheetId 解析正确）。
3. read_output 按顺序把各 output 单元格值映射回 param_id。
4. read_meta 归一化 status（与业务约定值一致才置 done）并读回 request_id。
5. 飞书错误码/HTTP 状态映射到 Retryable/NonRetryable；token 失效自动刷新一次后成功。
"""
import json

import httpx
import pytest

from app.core.config.settings import FeishuConfig
from app.modules.calculation.domain.execution import (
    NonRetryableCalcError,
    RetryableCalcError,
)
from app.modules.calculation.domain.param_dictionary import ParamDictionary
from app.modules.calculation.infrastructure.feishu_http_client import HttpFeishuGateway


def _param_dict() -> ParamDictionary:
    return ParamDictionary.from_raw({"parameters": [
        {"id": "power_mw", "cn": "功率", "source": "dialog", "direction": "input",
         "api_cell": "API_INPUT!B2", "writable": True},
        {"id": "capacity_mwh", "cn": "容量", "source": "dialog", "direction": "input",
         "api_cell": "API_INPUT!B3", "writable": True},
        {"id": "project_irr", "cn": "IRR", "source": "output", "direction": "output",
         "api_cell": "API_OUTPUT!C5"},
        {"id": "first_year_total_revenue", "cn": "首年总收益", "source": "output",
         "direction": "output", "api_cell": "API_OUTPUT!C6"},
        {"id": "main_business_cost", "cn": "主营成本(序列)", "source": "output",
         "direction": "output", "api_cell": "API_OUTPUT!C2:E2"},
    ]})


class FakeFeishu:
    """飞书开放平台打桩：路由各端点、记录请求，支持配置错误响应与读值。"""

    def __init__(self, *, update_responses=None, get_values=None):
        self.sheets = {"API_INPUT": "shtI", "API_OUTPUT": "shtO", "API_META": "shtM"}
        self.update_responses = list(update_responses or [])   # 队列：(status_code, json)
        self.get_values = get_values                            # 按 range 顺序的二维值
        self.token_calls = 0
        self.copy_calls = 0
        self.batch_updates = []     # 捕获的 valueRanges
        self.copy_auth = None
        self.copy_body = None
        self.get_params = None      # 捕获最近一次 values_batch_get 的查询参数

    def handler(self, request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p.endswith("/tenant_access_token/internal"):
            self.token_calls += 1
            return httpx.Response(200, json={
                "code": 0, "msg": "ok", "tenant_access_token": f"t-{self.token_calls}", "expire": 7200})
        if p.endswith("/copy"):
            self.copy_calls += 1
            self.copy_auth = request.headers.get("authorization")
            self.copy_body = json.loads(request.content)
            return httpx.Response(200, json={
                "code": 0, "data": {"file": {"token": "cp-token", "name": "n", "type": "sheet"}}})
        if p.endswith("/sheets/query"):
            return httpx.Response(200, json={"code": 0, "data": {
                "sheets": [{"sheet_id": sid, "title": t} for t, sid in self.sheets.items()]}})
        if p.endswith("/values_batch_update"):
            self.batch_updates.append(json.loads(request.content)["valueRanges"])
            if self.update_responses:
                sc, body = self.update_responses.pop(0)
                return httpx.Response(sc, json=body)
            return httpx.Response(200, json={"code": 0, "data": {}})
        if p.endswith("/values_batch_get"):
            self.get_params = dict(request.url.params)
            ranges = request.url.params.get("ranges", "").split(",")
            vrs = []
            for i, r in enumerate(ranges):
                v = self.get_values[i] if (self.get_values is not None and i < len(self.get_values)) else [[f"v{i}"]]
                vrs.append({"range": r, "values": v})
            return httpx.Response(200, json={"code": 0, "data": {"valueRanges": vrs}})
        return httpx.Response(404, json={"code": 1, "msg": "not found"})


def _gateway(fake: FakeFeishu, **cfg) -> HttpFeishuGateway:
    config = FeishuConfig(
        enabled=True, app_id="a", app_secret="s",
        template_token="tmpl", target_folder_token="fold", **cfg,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler), base_url="https://open.feishu.cn")
    return HttpFeishuGateway(config=config, param_dict=_param_dict(), client=client)


@pytest.mark.asyncio
async def test_copy_carries_token_and_returns_new_doc():
    fake = FakeFeishu()
    gw = _gateway(fake)
    token = await gw.copy_template("宁夏-200/400-20260710091435")
    assert token == "cp-token"
    assert fake.copy_calls == 1
    assert fake.copy_auth == "Bearer t-1"
    assert fake.copy_body["folder_token"] == "fold"
    assert fake.copy_body["type"] == "sheet"
    assert fake.copy_body["name"] == "宁夏-200/400-20260710091435"  # 副本名透传
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_write_input_maps_api_cells_to_sheet_ranges():
    fake = FakeFeishu()
    gw = _gateway(fake)
    await gw.write_input("doc1", {"power_mw": 100, "capacity_mwh": 200, "not_in_dict": 9})
    assert fake.batch_updates == [[
        {"range": "shtI!B2:B2", "values": [[100]]},
        {"range": "shtI!B3:B3", "values": [[200]]},
    ]]
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_read_output_maps_cells_to_param_ids():
    # 标量取首格；区间（15 年序列同理）展平为列表
    fake = FakeFeishu(get_values=[[[8.5]], [[8600]], [[1, 2, 3]]])
    gw = _gateway(fake)
    out = await gw.read_output("doc1")
    assert out == {
        "project_irr": 8.5,
        "first_year_total_revenue": 8600,
        "main_business_cost": [1, 2, 3],
    }
    # 读值必须带 valueRenderOption，否则飞书返回公式文本本身（非计算值）
    assert fake.get_params.get("valueRenderOption") == "UnformattedValue"
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_read_meta_normalizes_status_and_reads_request_id():
    fake = FakeFeishu(get_values=[[["done"]], [["R-1"]]])
    gw = _gateway(fake)
    assert await gw.read_meta("doc1") == {"status": "done", "request_id": "R-1"}
    await gw._client.aclose()

    # status 非约定"算完"值 → 原样返回（引擎据此继续轮询）
    fake2 = FakeFeishu(get_values=[[["计算中"]], [["R-1"]]])
    gw2 = _gateway(fake2)
    assert (await gw2.read_meta("doc1"))["status"] == "计算中"
    await gw2._client.aclose()


@pytest.mark.asyncio
async def test_permission_error_is_non_retryable():
    fake = FakeFeishu(update_responses=[(200, {"code": 1310213, "msg": "no perm"})])
    gw = _gateway(fake)
    with pytest.raises(NonRetryableCalcError):
        await gw.write_input("doc1", {"power_mw": 1})
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_server_error_is_retryable():
    fake = FakeFeishu(update_responses=[(500, {})])
    gw = _gateway(fake)
    with pytest.raises(RetryableCalcError):
        await gw.write_input("doc1", {"power_mw": 1})
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_token_invalid_refreshes_once_then_succeeds():
    fake = FakeFeishu(update_responses=[
        (200, {"code": 99991663, "msg": "token invalid"}),  # 第一次写入：token 失效
        (200, {"code": 0, "data": {}}),                      # 刷新后重试成功
    ])
    gw = _gateway(fake)
    await gw.write_input("doc1", {"power_mw": 1})  # 不抛
    assert fake.token_calls == 2  # 初次 + 刷新
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_content_processing_retries_then_succeeds():
    # copy 异步：副本 ContentMeta 处理中(601124041) → 退避重试同一请求，就绪后成功
    fake = FakeFeishu(update_responses=[
        (200, {"code": 601124041, "msg": "ContentMeta is processing"}),
        (200, {"code": 0, "data": {}}),
    ])
    gw = _gateway(fake)
    gw._processing_backoff = 0  # 测试不真的等
    await gw.write_input("doc1", {"power_mw": 1})  # 不抛
    await gw._client.aclose()


@pytest.mark.asyncio
async def test_content_processing_exhausts_to_retryable():
    # 一直处理中 → 退避耗尽后抛 Retryable（交外层重试策略继续兜）
    fake = FakeFeishu(update_responses=[(200, {"code": 601124041, "msg": "processing"})] * 3)
    gw = _gateway(fake)
    gw._processing_retries, gw._processing_backoff = 2, 0
    with pytest.raises(RetryableCalcError):
        await gw.write_input("doc1", {"power_mw": 1})
    await gw._client.aclose()
