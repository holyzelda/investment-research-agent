"""run_precompute() · 冒烟测试（sqlite 注入，不连真 MySQL、workers=1 避免进程池开销）。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.modules.calculation.infrastructure.spot_precompute import (
    PROVINCE_PRECOMPUTE_SPECS,
    run_precompute,
)

_DDL_PROV = (
    "CREATE TABLE ir_spot_daily_optimal_province (province TEXT, business_date TEXT, k INTEGER,"
    " charge_sum NUMERIC, discharge_sum NUMERIC, slot_count INTEGER,"
    " PRIMARY KEY (province,k,business_date))"
)


class _FakeProvinceRepo:
    """一天 96 点合成价格：前 48 点低价、后 48 点高价，制造正价差。"""

    def __init__(self):
        self.calls = []

    def fetch_daily_prices(self, area, mode, start, end):
        self.calls.append((area, mode))
        cheap = [Decimal(1)] * 48
        dear = [Decimal(10)] * 48
        return {date(2026, 7, 12): cheap + dear}


def _ir_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with eng.begin() as c:
        c.execute(text(_DDL_PROV))
    return eng


def test_run_precompute_writes_province_day_then_skips_when_rerun():
    eng = _ir_engine()
    repo = _FakeProvinceRepo()

    first = run_precompute(
        run_date=date(2026, 7, 13), node_stations=[],
        workers=1, cleanup_old=False, province_repo=repo, ir_engine=eng,
    )
    assert first["province_days_written"] == 29
    assert len(PROVINCE_PRECOMPUTE_SPECS) == 29
    assert ("蒙西-全网", "实时", "蒙西") in PROVINCE_PRECOMPUTE_SPECS
    assert ("江苏-全网", "日前", "江苏") in PROVINCE_PRECOMPUTE_SPECS
    assert ("蒙西-全网", "实时") in repo.calls

    with eng.connect() as c:
        rows = c.execute(text("SELECT COUNT(*) FROM ir_spot_daily_optimal_province")).scalar()
        mengxi_rows = c.execute(text(
            "SELECT COUNT(*) FROM ir_spot_daily_optimal_province WHERE province='蒙西'"
        )).scalar()
        source_rows = c.execute(text(
            "SELECT COUNT(*) FROM ir_spot_daily_optimal_province WHERE province='蒙西-全网'"
        )).scalar()
    assert rows > 0
    assert mengxi_rows > 0
    assert source_rows == 0

    second = run_precompute(
        run_date=date(2026, 7, 13), node_stations=[],
        workers=1, cleanup_old=False, province_repo=repo, ir_engine=eng,
    )
    assert second["province_days_written"] == 0
