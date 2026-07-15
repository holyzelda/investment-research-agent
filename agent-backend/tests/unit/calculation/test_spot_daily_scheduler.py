"""spot_daily_scheduler · 单测（假引擎模拟 GET_LOCK/RELEASE_LOCK，不连真 MySQL）。"""
from datetime import date

from app.core.config.settings import SpotPriceConfig
from app.modules.calculation.infrastructure.spot_daily_scheduler import (
    run_daily_update_once,
    start_spot_daily_scheduler,
    stop_spot_daily_scheduler,
)


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeConn:
    def __init__(self, lock_acquired: bool):
        self._lock_acquired = lock_acquired
        self.calls = []

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.calls.append(sql)
        if "GET_LOCK" in sql:
            return _FakeResult(1 if self._lock_acquired else 0)
        return _FakeResult(None)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self, lock_acquired: bool):
        self.conn = _FakeConn(lock_acquired)

    def connect(self):
        return self.conn


def _engine_factory(lock_acquired):
    def factory(dsn, **kwargs):
        return _FakeEngine(lock_acquired)
    return factory


def test_skips_precompute_when_lock_not_acquired():
    calls = []
    executed = run_daily_update_once(
        ir_dsn="mysql+pymysql://fake",
        run_date_provider=lambda: date(2026, 7, 14),
        precompute_fn=lambda **kw: calls.append(kw),
        engine_factory=_engine_factory(lock_acquired=False),
    )
    assert executed is False
    assert calls == []


def test_runs_precompute_and_releases_lock_when_lock_acquired():
    calls = []
    executed = run_daily_update_once(
        ir_dsn="mysql+pymysql://fake",
        node_province="蒙西",
        workers=4,
        run_date_provider=lambda: date(2026, 7, 14),
        precompute_fn=lambda **kw: calls.append(kw),
        engine_factory=_engine_factory(lock_acquired=True),
    )
    assert executed is True
    assert calls == [{
        "run_date": date(2026, 7, 14),
        "node_stations": ["*"],
        "node_province": "蒙西",
        "workers": 4,
        "cleanup_old": True,
    }]


def test_releases_lock_even_when_precompute_raises():
    def _boom(**kw):
        raise RuntimeError("源库不可达")

    engine = _FakeEngine(lock_acquired=True)
    executed = run_daily_update_once(
        ir_dsn="mysql+pymysql://fake",
        run_date_provider=lambda: date(2026, 7, 14),
        precompute_fn=_boom,
        engine_factory=lambda dsn, **kw: engine,
    )
    assert executed is True
    sql_calls = " | ".join(engine.conn.calls)
    assert "GET_LOCK" in sql_calls and "RELEASE_LOCK" in sql_calls


class _FakeSettings:
    def __init__(self, spot_price):
        self.spot_price = spot_price

        class _Database:
            url = "sqlite+aiomysql://fake"
        self.database = _Database()


def test_scheduler_registers_configured_daily_cron(monkeypatch):
    from app.core.config import settings as settings_module

    cfg = SpotPriceConfig(daily_update_enabled=True, daily_update_hour=3, daily_update_minute=30)
    monkeypatch.setattr(settings_module, "get_settings", lambda: _FakeSettings(cfg))

    scheduler = start_spot_daily_scheduler()
    try:
        job = scheduler.get_job("spot_daily_update")
        assert job is not None
        assert "hour='3'" in str(job.trigger)
        assert "minute='30'" in str(job.trigger)
    finally:
        stop_spot_daily_scheduler()
