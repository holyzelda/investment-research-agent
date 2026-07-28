"""全国指数地图 JSON 序列化。"""
from __future__ import annotations

from decimal import Decimal

from app.modules.index_map.domain.models import IndexOverview, IndexPeriod, ProvinceIndexDetail, ProvinceIndexSummary


def _number(value: Decimal | None):
    return float(value) if value is not None else None


def _summary(item: ProvinceIndexSummary) -> dict:
    return {
        "provinceCode": item.province_code,
        "provinceName": item.province_name,
        "mapName": item.map_name,
        "indexScore": _number(item.index_score),
        "grade": item.grade,
        "opened": item.opened,
        "rank": item.rank,
        "annualizedReturn": _number(item.annualized_return),
        "updatedAt": item.updated_at.isoformat(),
    }


def serialize_periods(items: list[IndexPeriod]) -> dict:
    return {"items": [
        {"period": item.period, "label": item.label, "updatedAt": item.updated_at.isoformat()}
        for item in items
    ]}


def serialize_overview(overview: IndexOverview) -> dict:
    return {
        "period": overview.period.period,
        "updatedAt": overview.period.updated_at.isoformat(),
        "provinces": [_summary(item) for item in overview.provinces],
        "summary": {
            "nationalAverage": _number(overview.national_average),
            "leader": _summary(overview.leader) if overview.leader else None,
            "openedProvinceCount": overview.opened_province_count,
            "openedGradeCounts": overview.opened_grade_counts,
            "highPotentialCount": overview.high_potential_count,
        },
        "rankings": {
            "investmentHeat": [_summary(item) for item in overview.investment_heat],
            "returnStability": [_summary(item) for item in overview.return_stability],
        },
    }


def serialize_province_detail(detail: ProvinceIndexDetail | None) -> dict | None:
    if detail is None:
        return None
    return {**_summary(detail.summary), **detail.payload}
