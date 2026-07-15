"""PrecomputeSpotPriceAlgo · 单测（查预计算表；用 sqlite 内存库注入，不连真 MySQL）。

验证：K 折算、按省/节点路由、滚动一年窗口求和 → 均价、×省份系数、÷1000(MWh→kWh)、无数据→None。
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.core.config.settings import ProvincePriceCoefficient
from app.modules.calculation.infrastructure.spot_price_algo import PrecomputeSpotPriceAlgo

_DDL_PROV = (
    "CREATE TABLE ir_spot_daily_optimal_province (province TEXT, business_date TEXT, k INTEGER,"
    " charge_sum NUMERIC, discharge_sum NUMERIC, slot_count INTEGER,"
    " PRIMARY KEY (province,k,business_date))"
)
_DDL_NODE = (
    "CREATE TABLE ir_spot_daily_optimal_node (province TEXT, station_name TEXT, business_date TEXT,"
    " k INTEGER, charge_sum NUMERIC, discharge_sum NUMERIC, slot_count INTEGER,"
    " PRIMARY KEY (province,station_name,k,business_date))"
)


def _engine_with_rows(prov_rows=(), node_rows=()):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with eng.begin() as c:
        c.execute(text(_DDL_PROV))
        c.execute(text(_DDL_NODE))
        for r in prov_rows:
            c.execute(text("INSERT INTO ir_spot_daily_optimal_province VALUES (:p,:d,:k,:cs,:ds,:sl)"), r)
        for r in node_rows:
            c.execute(text("INSERT INTO ir_spot_daily_optimal_node VALUES (:p,:st,:d,:k,:cs,:ds,:sl)"), r)
    return eng


def _algo(engine, coeff=None):
    return PrecomputeSpotPriceAlgo(
        coefficients=coeff or {}, engine=engine, run_date_provider=lambda: date(2026, 7, 10))


# 容量400/功率200/循环1 → K=8
_ARGS = dict(capacity_mwh=400, power_mw=200, daily_cycles=1)


def test_province_sum_average_no_coeff():
    rows = [
        {"p": "宁夏", "d": "2025-08-01", "k": 8, "cs": 100, "ds": 800, "sl": 8},
        {"p": "宁夏", "d": "2025-08-02", "k": 8, "cs": 140, "ds": 1000, "sl": 8},
    ]
    algo = _algo(_engine_with_rows(prov_rows=rows))
    c, d = algo.compute("宁夏", None, **_ARGS)
    # avg_c=(100+140)/16=15 → ÷1000=0.015；avg_d=(800+1000)/16=112.5 → 0.1125
    assert c == 0.015 and d == 0.1125


def test_province_coefficient_applied():
    rows = [{"p": "宁夏", "d": "2025-08-01", "k": 8, "cs": 120, "ds": 960, "sl": 8}]
    coeff = {"宁夏": ProvincePriceCoefficient(charge=0.8, discharge=0.6)}
    algo = _algo(_engine_with_rows(prov_rows=rows), coeff)
    c, d = algo.compute("宁夏", None, **_ARGS)
    # avg_c=15×0.8÷1000=0.012；avg_d=120×0.6÷1000=0.072
    assert c == 0.012 and d == 0.072


def test_node_route_uses_node_table_and_province_coeff():
    node = [{"p": "蒙西", "st": "祥泰站", "d": "2025-09-01", "k": 8, "cs": 80, "ds": 800, "sl": 8}]
    coeff = {"蒙西": ProvincePriceCoefficient(charge=0.5, discharge=0.5)}
    algo = _algo(_engine_with_rows(node_rows=node), coeff)
    c, d = algo.compute("蒙西", "祥泰站", **_ARGS)   # 有节点 → 查节点表；系数按省(蒙西)
    # avg_c=10×0.5÷1000=0.005；avg_d=100×0.5÷1000=0.05
    assert c == 0.005 and d == 0.05


def test_none_when_no_rows():
    algo = _algo(_engine_with_rows())
    assert algo.compute("宁夏", None, **_ARGS) == (None, None)


def test_out_of_window_rows_ignored():
    # 窗口 [2025-07-10, 2026-07-10)；这条 2025-07-01 在窗口外 → 不计入 → None
    rows = [{"p": "宁夏", "d": "2025-07-01", "k": 8, "cs": 100, "ds": 800, "sl": 8}]
    algo = _algo(_engine_with_rows(prov_rows=rows))
    assert algo.compute("宁夏", None, **_ARGS) == (None, None)


def test_wrong_k_not_matched():
    # 表里只有 k=32 的行，查询 K=8 → 无匹配 → None
    rows = [{"p": "宁夏", "d": "2025-08-01", "k": 32, "cs": 100, "ds": 800, "sl": 8}]
    algo = _algo(_engine_with_rows(prov_rows=rows))
    assert algo.compute("宁夏", None, **_ARGS) == (None, None)
