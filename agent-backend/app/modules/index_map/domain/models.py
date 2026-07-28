"""全国指数地图领域模型。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class IndexPeriod:
    period: str
    label: str
    updated_at: datetime


@dataclass(frozen=True)
class ProvinceIndexSummary:
    province_code: str
    province_name: str
    map_name: str
    index_score: Decimal | None
    grade: str | None
    opened: bool
    rank: int | None
    annualized_return: Decimal | None
    updated_at: datetime


@dataclass(frozen=True)
class IndexOverview:
    period: IndexPeriod
    provinces: tuple[ProvinceIndexSummary, ...]
    national_average: Decimal | None
    leader: ProvinceIndexSummary | None
    opened_province_count: int
    opened_grade_counts: dict[str, int]
    high_potential_count: int
    investment_heat: tuple[ProvinceIndexSummary, ...]
    return_stability: tuple[ProvinceIndexSummary, ...]


@dataclass(frozen=True)
class ProvinceIndexDetail:
    summary: ProvinceIndexSummary
    payload: dict[str, Any]
