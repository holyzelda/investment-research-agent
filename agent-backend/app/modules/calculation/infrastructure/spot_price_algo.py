"""calculation 基础设施 · 现货电价查表适配器（查 ir_agent 预计算表，接 SpotPriceAlgo 端口）。

唯一的生产取数方式：容量/功率/循环 → K = k_from_inputs → 查 ir_spot_daily_optimal_* 表
按滚动一年窗口 SUM(charge_sum/discharge_sum/slot_count) → 均价 → ×省份系数 → ÷1000（MWh→kWh）。毫秒级。

- 逐日最优结果由离线脚本 tools/spot_precompute.py 预算好；本类只查表求和，不跑 DP、不连电价源库。
- node_name 有值查节点表(按 province+station_name)，否则查省级表(按 province)；系数按 province 取（口径b：节点随省）。
- 系数不进表（表存原始 元/MWh），此处应用 → 支持后续热更（挂账#13）。
- 查不到/槽数为 0（未回填/无正价差）→ (None, None)。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.modules.calculation.domain.ports import SpotPriceAlgo
from app.modules.calculation.domain.spot_pricing import k_from_inputs

_PROVINCE_SQL = (
    "SELECT SUM(charge_sum), SUM(discharge_sum), SUM(slot_count) "
    "FROM ir_spot_daily_optimal_province "
    "WHERE province=:p AND k=:k AND business_date>=:s AND business_date<:e"
)
_NODE_SQL = (
    "SELECT SUM(charge_sum), SUM(discharge_sum), SUM(slot_count) "
    "FROM ir_spot_daily_optimal_node "
    "WHERE province=:p AND station_name=:st AND k=:k AND business_date>=:s AND business_date<:e"
)


def _rolling_year(run_date: date) -> tuple[date, date]:
    """[run_date 往前一个日历年, run_date)；business_date < run_date。"""
    try:
        start = run_date.replace(year=run_date.year - 1)
    except ValueError:          # 2/29 → 回落 2/28
        start = run_date.replace(year=run_date.year - 1, day=28)
    return start, run_date


class PrecomputeSpotPriceAlgo(SpotPriceAlgo):
    def __init__(
        self,
        coefficients: dict,                      # {province: ProvincePriceCoefficient}
        engine: Optional[Engine] = None,         # ir_agent 引擎；测试可注入 sqlite
        ir_dsn: Optional[str] = None,
        run_date_provider=None,
    ):
        self._coeff = coefficients or {}
        self._engine = engine or create_engine(ir_dsn, pool_pre_ping=True)
        self._run_date = run_date_provider or date.today

    def compute(self, province, node_name, capacity_mwh, power_mw, daily_cycles):
        k = k_from_inputs(Decimal(str(capacity_mwh)), Decimal(str(power_mw)), Decimal(str(daily_cycles)))
        start, end = _rolling_year(self._run_date())
        if node_name:
            sql, params = _NODE_SQL, {"p": province, "st": node_name, "k": k, "s": start, "e": end}
        else:
            sql, params = _PROVINCE_SQL, {"p": province, "k": k, "s": start, "e": end}
        with self._engine.connect() as conn:
            sum_c, sum_d, sum_slots = conn.execute(text(sql), params).first()
        if not sum_slots:
            return None, None
        avg_c = Decimal(sum_c) / sum_slots
        avg_d = Decimal(sum_d) / sum_slots
        coeff = self._coeff.get(province)
        cf = Decimal(str(coeff.charge)) if coeff else Decimal(1)
        df = Decimal(str(coeff.discharge)) if coeff else Decimal(1)
        return float(avg_c * cf / 1000), float(avg_d * df / 1000)
