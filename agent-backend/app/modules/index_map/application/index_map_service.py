"""全国指数地图查询服务。

当前数据表未投产，接口固定返回从 Excel 整理的本地模拟数据；保留数据库查询实现以便后续启用。
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.index_map.application.mock_data import DETAILS, PERIOD, PROVINCES
from app.modules.index_map.domain.models import IndexOverview, IndexPeriod, ProvinceIndexDetail, ProvinceIndexSummary
from app.modules.index_map.infrastructure.persistence.orm import IndexMapPeriodORM, IndexMapProvinceORM

_USE_DATABASE = False

# 评级完全由投资指数分数判定：90–100 S、80–<90 A、70–<80 B、60–<70 C；区间外或空值不赋级。
_GRADE_BANDS = (
    (Decimal("90"), Decimal("100"), "S"),
    (Decimal("80"), Decimal("90"), "A"),
    (Decimal("70"), Decimal("80"), "B"),
    (Decimal("60"), Decimal("70"), "C"),
)


def _grade_for_score(score: Decimal | None) -> str | None:
    if score is None:
        return None
    for low, high, grade in _GRADE_BANDS:
        if grade == "S":
            if low <= score <= high:
                return grade
        elif low <= score < high:
            return grade
    return None


def _normalize_provinces(provinces: tuple[ProvinceIndexSummary, ...]) -> tuple[ProvinceIndexSummary, ...]:
    """按分数统一判级并重排 rank，使评级、排行榜、tooltip、详情排名口径一致。"""
    ordered = sorted(
        provinces,
        key=lambda item: (item.index_score is None, -(item.index_score or Decimal(0)), item.province_code),
    )
    normalized: list[ProvinceIndexSummary] = []
    for rank, item in enumerate(ordered, 1):
        grade = _grade_for_score(item.index_score)
        normalized.append(ProvinceIndexSummary(**{**item.__dict__, "grade": grade, "rank": rank}))
    return tuple(normalized)


def _period(row: IndexMapPeriodORM) -> IndexPeriod:
    return IndexPeriod(period=row.period, label=row.label, updated_at=row.updated_at)


def _summary(row: IndexMapProvinceORM) -> ProvinceIndexSummary:
    return ProvinceIndexSummary(
        province_code=row.province_code, province_name=row.province_name, map_name=row.map_name,
        index_score=row.index_score, grade=row.grade, opened=row.opened, rank=row.rank,
        annualized_return=row.annualized_return, updated_at=row.updated_at,
    )


def _overview(period: IndexPeriod, provinces: tuple[ProvinceIndexSummary, ...]) -> IndexOverview:
    provinces = _normalize_provinces(provinces)
    score_rows = provinces  # 已按分数降序、同分按 province_code 稳定排序
    return_rows = tuple(
        ProvinceIndexSummary(**{**item.__dict__, "rank": rank})
        for rank, item in enumerate(
            sorted(
                (item for item in provinces if item.annualized_return is not None),
                key=lambda item: (-item.annualized_return, item.province_code),
            )[:5],
            1,
        )
    )
    valid_scores = [item.index_score for item in provinces if item.index_score is not None]
    counts = {grade: sum(1 for item in provinces if item.opened and item.grade == grade) for grade in ("S", "A", "B", "C")}
    return IndexOverview(
        period=period, provinces=provinces,
        national_average=(sum(valid_scores) / len(valid_scores)) if valid_scores else None,
        leader=score_rows[0] if score_rows and score_rows[0].index_score is not None else None,
        opened_province_count=sum(1 for item in provinces if item.opened),
        opened_grade_counts=counts,
        # “C 类区域”语义：按已开通的 C 类区域计数，与摘要第四张卡片一致。
        high_potential_count=counts["C"],
        investment_heat=score_rows[:5], return_stability=return_rows[:5],
    )


class IndexMapService:
    async def list_periods(self, session: AsyncSession | None) -> list[IndexPeriod]:
        if not _USE_DATABASE:
            return [PERIOD]
        rows = (await session.scalars(select(IndexMapPeriodORM).order_by(IndexMapPeriodORM.updated_at.desc(), IndexMapPeriodORM.period.desc()))).all()
        return [_period(row) for row in rows]

    async def _get_period(self, session: AsyncSession | None, period: str) -> IndexPeriod:
        if not _USE_DATABASE:
            if period != PERIOD.period:
                raise NotFoundException("指数期次不存在")
            return PERIOD
        row = await session.get(IndexMapPeriodORM, period)
        if row is None:
            raise NotFoundException("指数期次不存在")
        return _period(row)

    async def get_overview(self, session: AsyncSession | None, *, period: str) -> IndexOverview:
        period_model = await self._get_period(session, period)
        if not _USE_DATABASE:
            return _overview(period_model, PROVINCES)
        rows = (await session.scalars(select(IndexMapProvinceORM).where(IndexMapProvinceORM.period == period))).all()
        return _overview(period_model, tuple(_summary(row) for row in rows))

    async def get_province_detail(self, session: AsyncSession | None, *, period: str, province_code: str) -> ProvinceIndexDetail | None:
        await self._get_period(session, period)
        if not _USE_DATABASE:
            detail = DETAILS.get(province_code)
            if detail is None:
                raise NotFoundException("省份指数不存在")
            # 用与概览一致的分数驱动评级和排名归一化详情 summary，保证详情页排名/评级口径一致。
            normalized = {item.province_code: item for item in _normalize_provinces(PROVINCES)}
            return ProvinceIndexDetail(summary=normalized[province_code], payload=detail.payload)
        row = await session.scalar(select(IndexMapProvinceORM).where(IndexMapProvinceORM.period == period, IndexMapProvinceORM.province_code == province_code))
        if row is None:
            raise NotFoundException("省份指数不存在")
        return ProvinceIndexDetail(summary=_summary(row), payload=row.detail_payload) if row.detail_payload else None
