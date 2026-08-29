from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.modules.calculation.infrastructure.spot_precompute import run_precompute
from app.modules.calculation.infrastructure.spot_price_algo import PrecomputeSpotPriceAlgo


_DDL_HENAN = "CREATE TABLE ir_spot_daily_optimal_henan (province TEXT,region TEXT,business_date TEXT,k INTEGER,charge_sum NUMERIC,discharge_sum NUMERIC,slot_count INTEGER,PRIMARY KEY(province,region,k,business_date))"
_DDL_PROV = "CREATE TABLE ir_spot_daily_optimal_province (province TEXT,business_date TEXT,k INTEGER,charge_sum NUMERIC,discharge_sum NUMERIC,slot_count INTEGER,PRIMARY KEY(province,k,business_date))"
_DDL_NODE = "CREATE TABLE ir_spot_daily_optimal_node (province TEXT,station_name TEXT,business_date TEXT,k INTEGER,charge_sum NUMERIC,discharge_sum NUMERIC,slot_count INTEGER,PRIMARY KEY(province,station_name,k,business_date))"


class _Repo:
    def fetch_daily_prices(self, area, mode, start, end):
        return {date(2026, 7, 12): [Decimal(1)] * 96}

    def fetch_daily_dual_prices(self, area, charge_mode, discharge_mode, start, end, *, discharge_area=None):
        discharge = 5 if discharge_area is None else {
            "豫北": 10, "豫西": 20, "豫中东": 30, "豫南": 40,
        }[discharge_area]
        return {date(2026, 7, 12): ([Decimal(1)] * 96, [Decimal(discharge)] * 96)}


def _engine(*tables):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        for ddl in tables:
            conn.execute(text(ddl))
    return engine


def test_henan_dual_prices_are_written_separately():
    engine = _engine(_DDL_HENAN, _DDL_PROV, _DDL_NODE)
    stats = run_precompute(
        date(2026, 7, 13), [], workers=1, cleanup_old=False,
        province_repo=_Repo(), ir_engine=engine,
    )
    assert stats["dual_province_days_written"] == 5
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT region, COUNT(*) FROM ir_spot_daily_optimal_henan GROUP BY region"
        )).all()
    assert {region: count for region, count in rows} == {
        "省级": 19, "豫北": 19, "豫西": 19, "豫中东": 19, "豫南": 19,
    }


def test_henan_algo_reads_city_region_and_ignores_node_name():
    engine = _engine(_DDL_HENAN, _DDL_NODE)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO ir_spot_daily_optimal_henan VALUES "
            "('河南','豫中东','2025-08-01',8,80,240,8),"
            "('河南','豫西','2025-08-01',8,80,160,8)"
        ))
    algo = PrecomputeSpotPriceAlgo({}, engine=engine, run_date_provider=lambda: date(2026, 7, 10))
    assert algo.compute("河南", "不存在的节点", 400, 200, 1, city="郑州") == (0.01, 0.03)
    assert algo.compute("河南", None, 400, 200, 1, city="洛阳市") == (0.01, 0.02)


def test_henan_cityless_does_not_use_regional_data():
    engine = _engine(_DDL_HENAN)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO ir_spot_daily_optimal_henan VALUES "
            "('河南','豫北','2025-08-01',8,80,800,8)"
        ))
    algo = PrecomputeSpotPriceAlgo({}, engine=engine, run_date_provider=lambda: date(2026, 7, 10))
    assert algo.compute("河南", None, 400, 200, 1) == (None, None)


    engine = _engine(_DDL_HENAN)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO ir_spot_daily_optimal_henan VALUES "
            "('河南','省级','2025-08-01',8,80,800,8)"
        ))
    algo = PrecomputeSpotPriceAlgo({}, engine=engine, run_date_provider=lambda: date(2026, 7, 10))
    assert algo.compute("河南", None, 400, 200, 1, city="安阳") == (0.01, 0.1)
