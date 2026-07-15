"""calculation 基础设施 · 各省收益结构表读取（表2）。

两种实现，同一 RevenueStructureReader 端口：
- JsonRevenueStructureReader：读本地 revenue_structure.json（离线/回退，feishu 未启用时用）。
- FeishuRevenueStructureReader：飞书真读——表2《各省收益结构》独立电子表格（稳定 token，非底稿副本）。
  方案A："表2取数由本系统后端做"。整表一次读入并按 module 级 TTL 缓存（静态参照数据、罕变），
  get_profile 退化为字典查找、不阻塞每次测算；HTTP 走同步 httpx.Client（端口 get_profile 为同步契约）。

表2 列布局（sheet=各省收益结构，表头行2，省份数据行4起；与 param_dict 的 revenue_col/tier_cols 对齐、已核对底稿）：
  A 地区 | B 中长期开关 · C/D 中长期两档 | E 现货开关 |
  F 调频开关 · G/H 调频两档 | I 容量开关 | J 补贴开关 |
  K 租赁开关 · L 租赁单价 · M 租赁达成率 | N 干预开关 · O/P 干预两档 |
  Q 其他辅助(忽略) | R 收过网费 | S 返还过网费
"""
import time
from typing import Optional

import httpx

from app.core.config.settings import FeishuConfig
from app.modules.calculation.domain.execution import NonRetryableCalcError
from app.modules.calculation.domain.models import ProvinceRevenueProfile, TwoTier
from app.modules.calculation.domain.ports import RevenueStructureReader
from app.modules.calculation.infrastructure.data_loader import revenue_structure_raw


def _tt(d: dict) -> TwoTier:
    return TwoTier(t2=d.get("t2"), t4=d.get("t4"))


class JsonRevenueStructureReader(RevenueStructureReader):
    """从 revenue_structure.json 读取某省收益结构画像（离线/回退）。"""

    def get_profile(self, province: str) -> Optional[ProvinceRevenueProfile]:
        raw = revenue_structure_raw().get("provinces", {})
        row = raw.get(province)
        if row is None:
            return None
        sw = row.get("switch", {})
        return ProvinceRevenueProfile(
            province=province,
            mid_long=sw.get("mid_long"),
            spot=sw.get("spot"),
            frequency=sw.get("frequency"),
            capacity=sw.get("capacity"),
            subsidy=sw.get("subsidy"),
            lease=sw.get("lease"),
            intervention=sw.get("intervention"),
            collect_grid_fee=sw.get("collect_grid_fee"),
            return_grid_fee=sw.get("return_grid_fee"),
            mid_long_tier=_tt(row.get("mid_long_tier", {})),
            frequency_tier=_tt(row.get("frequency_tier", {})),
            intervention_tier=_tt(row.get("intervention_tier", {})),
            lease_unit_price=row.get("lease_unit_price"),
            lease_achievement_rate=row.get("lease_achievement_rate"),
        )


# ---- 飞书真读 ----

# 表2 A:S 各字段在行内的 0 基列索引（A=0）
_C_MID_LONG, _C_ML_T2, _C_ML_T4 = 1, 2, 3       # B / C / D
_C_SPOT = 4                                      # E
_C_FREQ, _C_FR_T2, _C_FR_T4 = 5, 6, 7            # F / G / H
_C_CAPACITY = 8                                  # I
_C_SUBSIDY = 9                                   # J
_C_LEASE, _C_LEASE_PRICE, _C_LEASE_RATE = 10, 11, 12  # K / L / M
_C_INTERV, _C_IV_T2, _C_IV_T4 = 13, 14, 15       # N / O / P
_C_COLLECT_GRID_FEE = 17                         # R（Q=16 其他辅助，忽略）
_C_RETURN_GRID_FEE = 18                          # S

# module 级缓存：revenue_structure_token -> (loaded_at, {province: ProvinceRevenueProfile})
_TABLE_CACHE: dict[str, tuple[float, dict]] = {}


def _switch(v) -> Optional[int]:
    """开关归一化为 1/0/None（空/异常 → None）。"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)) and v in (0, 1):
        return int(v)
    if isinstance(v, str) and v.strip() in ("0", "1"):
        return int(v.strip())
    return None


def _num(v) -> Optional[float]:
    """数值归一化为 float 或 None（空串/非数 → None）。"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _sync_check(r: httpx.Response) -> dict:
    """同步版最小错误检查：HTTP/飞书 code 非 0 → 抛出（表2 读多为配置/权限问题，不重试）。"""
    if r.status_code >= 400:
        raise NonRetryableCalcError(
            f"飞书表2读取 HTTP {r.status_code}", code=f"feishu_http_{r.status_code}")
    body = r.json()
    code = body.get("code", 0)
    if code != 0:
        raise NonRetryableCalcError(
            f"飞书表2错误 {code}：{body.get('msg')}", code=f"feishu_{code}")
    return body


class FeishuRevenueStructureReader(RevenueStructureReader):
    """飞书真读表2《各省收益结构》。整表按 TTL 缓存，get_profile 为字典查找。"""

    def __init__(self, config: FeishuConfig, ttl: float = 300.0,
                 client: Optional[httpx.Client] = None):
        self._cfg = config
        self._ttl = ttl
        self._client = client   # 测试可注入挂 MockTransport 的同步 client

    def get_profile(self, province: str) -> Optional[ProvinceRevenueProfile]:
        return self._table().get(province)

    @staticmethod
    def cache_clear() -> None:
        """清缓存（测试/表2 变更后强制重读用）。"""
        _TABLE_CACHE.clear()

    # ---- 缓存 ----
    def _table(self) -> dict:
        key = self._cfg.revenue_structure_token
        hit = _TABLE_CACHE.get(key)
        if hit and (time.time() - hit[0]) < self._ttl:
            return hit[1]
        table = self._load()
        _TABLE_CACHE[key] = (time.time(), table)
        return table

    # ---- 飞书读取（同步）----
    def _load(self) -> dict:
        table: dict = {}
        for r in self._read_rows():
            prov = str(r[0]).strip() if (r and r[0] not in (None, "")) else ""
            if not prov:
                continue  # 跳过空行/表尾冗余行
            table[prov] = self._to_profile(prov, r)
        return table

    def _read_rows(self) -> list:
        """token → sheet_id(v3 query) → values_batch_get(v2)，返回数据区二维数组。"""
        cfg = self._cfg
        client = self._client or httpx.Client(base_url=cfg.base_url, timeout=30.0)
        owned = self._client is None
        try:
            tok = _sync_check(client.post(
                "/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": cfg.app_id, "app_secret": cfg.app_secret},
            ))["tenant_access_token"]
            hdr = {"Authorization": f"Bearer {tok}"}
            q = _sync_check(client.get(
                f"/open-apis/sheets/v3/spreadsheets/{cfg.revenue_structure_token}/sheets/query",
                headers=hdr,
            ))
            ids = {s["title"]: s["sheet_id"] for s in q["data"]["sheets"]}
            sid = ids.get(cfg.revenue_structure_sheet)
            if sid is None:
                raise NonRetryableCalcError(
                    f"表2 sheet 不存在：{cfg.revenue_structure_sheet}",
                    code="feishu_revenue_sheet_not_found")
            body = _sync_check(client.get(
                f"/open-apis/sheets/v2/spreadsheets/{cfg.revenue_structure_token}/values_batch_get",
                params={"ranges": f"{sid}!{cfg.revenue_structure_range}",
                        "valueRenderOption": "UnformattedValue"},
                headers=hdr,
            ))
            vrs = body["data"]["valueRanges"]
            return (vrs[0].get("values") or []) if vrs else []
        finally:
            if owned:
                client.close()

    def _to_profile(self, prov: str, r: list) -> ProvinceRevenueProfile:
        def c(i):
            return r[i] if i < len(r) else None
        return ProvinceRevenueProfile(
            province=prov,
            mid_long=_switch(c(_C_MID_LONG)),
            spot=_switch(c(_C_SPOT)),
            frequency=_switch(c(_C_FREQ)),
            capacity=_switch(c(_C_CAPACITY)),
            subsidy=_switch(c(_C_SUBSIDY)),
            lease=_switch(c(_C_LEASE)),
            intervention=_switch(c(_C_INTERV)),
            collect_grid_fee=_switch(c(_C_COLLECT_GRID_FEE)),
            return_grid_fee=_switch(c(_C_RETURN_GRID_FEE)),
            mid_long_tier=TwoTier(_num(c(_C_ML_T2)), _num(c(_C_ML_T4))),
            frequency_tier=TwoTier(_num(c(_C_FR_T2)), _num(c(_C_FR_T4))),
            intervention_tier=TwoTier(_num(c(_C_IV_T2)), _num(c(_C_IV_T4))),
            lease_unit_price=_num(c(_C_LEASE_PRICE)),
            lease_achievement_rate=_num(c(_C_LEASE_RATE)),
        )
