"""现货电价库取数 · 纯函数单测（网格/解析/完整日过滤；不连真 MySQL）。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text

from app.modules.calculation.infrastructure.spot_price_repo import (
    GRID_LABELS,
    ProvinceSpotRepository,
    _complete_days,
    _parse_date,
    _to_decimal,
)


def test_grid_labels_96_points_0015_to_2400():
    assert len(GRID_LABELS) == 96
    assert GRID_LABELS[0] == "00:15"
    assert GRID_LABELS[-1] == "24:00"
    assert "01:00" in GRID_LABELS and "12:00" in GRID_LABELS and "23:45" in GRID_LABELS
    assert len(set(GRID_LABELS)) == 96  # 无重复


def test_to_decimal():
    assert _to_decimal("5.5") == Decimal("5.5")
    assert _to_decimal(Decimal("3")) == Decimal("3")
    assert _to_decimal("-0.12") == Decimal("-0.12")   # 负电价合法
    assert _to_decimal("") is None
    assert _to_decimal(None) is None
    assert _to_decimal("abc") is None


def test_parse_date():
    assert _parse_date("2026-07-09") == date(2026, 7, 9)
    assert _parse_date("2026/07/09") == date(2026, 7, 9)
    assert _parse_date(date(2026, 7, 9)) == date(2026, 7, 9)
    assert _parse_date("garbage") is None


def test_complete_days_keeps_only_full_96():
    full = {label: Decimal("1") for label in GRID_LABELS}
    partial = {label: Decimal("1") for label in GRID_LABELS[:95]}    # 缺 1 点
    holey = dict(full); holey["12:00"] = None                        # 有点但不可解析
    out = _complete_days({
        date(2026, 1, 1): full,
        date(2026, 1, 2): partial,
        date(2026, 1, 3): holey,
    })
    assert list(out.keys()) == [date(2026, 1, 1)]
    assert len(out[date(2026, 1, 1)]) == 96


def test_province_repository_uses_mode_from_each_call():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE points (business_date TEXT, time TEXT, price TEXT, "
            "market TEXT, mode TEXT, area TEXT)"
        ))
        for mode, price in (("日前", "1"), ("实时", "2")):
            conn.execute(text(
                "INSERT INTO points VALUES (:d, :t, :p, :market, :mode, :area)"
            ), [
                {
                    "d": "2026-01-01", "t": label, "p": price,
                    "market": "省内市场", "mode": mode, "area": "甘肃",
                }
                for label in GRID_LABELS
            ])

    repo = ProvinceSpotRepository("sqlite://", "points", "省内市场")
    repo._engine = engine

    daily = repo.fetch_daily_prices("甘肃", "实时", date(2026, 1, 1), date(2026, 1, 2))

    assert daily == {date(2026, 1, 1): [Decimal("2")] * 96}
