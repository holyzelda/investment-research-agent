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


def _period(row: IndexMapPeriodORM) -> IndexPeriod:
    return IndexPeriod(period=row.period, label=row.label, updated_at=row.updated_at)


def _summary(row: IndexMapProvinceORM) -> ProvinceIndexSummary:
    return ProvinceIndexSummary(
        province_code=row.province_code, province_name=row.province_name, map_name=row.map_name,
        index_score=row.index_score, grade=row.grade, opened=row.opened, rank=row.rank,
        annualized_return=row.annualized_return, updated_at=row.updated_at,
    )


def _overview(period: IndexPeriod, provinces: tuple[ProvinceIndexSummary, ...]) -> IndexOverview:
    score_rows = tuple(sorted(provinces, key=lambda item: (item.index_score is None, -(item.index_score or Decimal(0)), item.province_code)))
    return_rows = tuple(sorted(provinces, key=lambda item: (item.annualized_return is None, -(item.annualized_return or Decimal(0)), item.province_code)))
    valid_scores = [item.index_score for item in provinces if item.index_score is not None]
    counts = {grade: sum(1 for item in provinces if item.opened and item.grade == grade) for grade in ("S", "A", "B")}
    return IndexOverview(
        period=period, provinces=provinces,
        national_average=(sum(valid_scores) / len(valid_scores)) if valid_scores else None,
        leader=score_rows[0] if score_rows and score_rows[0].index_score is not None else None,
        opened_province_count=sum(counts.values()), opened_grade_counts=counts,
        high_potential_count=6,
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
            overview = _overview(period_model, PROVINCES)
            # Excel 的“其他信息”页给出投资均值 89.2；它不等于仅五个已开通省份的算术均值。
            return IndexOverview(**{**overview.__dict__, "national_average": Decimal("89.2")})
        rows = (await session.scalars(select(IndexMapProvinceORM).where(IndexMapProvinceORM.period == period))).all()
        return _overview(period_model, tuple(_summary(row) for row in rows))

    async def get_province_detail(self, session: AsyncSession | None, *, period: str, province_code: str) -> ProvinceIndexDetail | None:
        await self._get_period(session, period)
        if not _USE_DATABASE:
            detail = DETAILS.get(province_code)
            if detail is None:
                raise NotFoundException("省份指数不存在")
            return detail
        row = await session.scalar(select(IndexMapProvinceORM).where(IndexMapProvinceORM.period == period, IndexMapProvinceORM.province_code == province_code))
        if row is None:
            raise NotFoundException("省份指数不存在")
        return ProvinceIndexDetail(summary=_summary(row), payload=row.detail_payload) if row.detail_payload else None
