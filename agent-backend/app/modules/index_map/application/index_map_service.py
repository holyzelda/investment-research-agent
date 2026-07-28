"""全国指数地图查询服务。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.index_map.domain.models import (
    IndexOverview,
    IndexPeriod,
    ProvinceIndexDetail,
    ProvinceIndexSummary,
)
from app.modules.index_map.infrastructure.persistence.orm import IndexMapPeriodORM, IndexMapProvinceORM

_VALID_GRADES = {"S", "A", "B", "C"}


def _period(row: IndexMapPeriodORM) -> IndexPeriod:
    return IndexPeriod(period=row.period, label=row.label, updated_at=row.updated_at)


def _summary(row: IndexMapProvinceORM) -> ProvinceIndexSummary:
    return ProvinceIndexSummary(
        province_code=row.province_code,
        province_name=row.province_name,
        map_name=row.map_name,
        index_score=row.index_score,
        grade=row.grade,
        opened=row.opened,
        rank=row.rank,
        annualized_return=row.annualized_return,
        updated_at=row.updated_at,
    )


class IndexMapService:
    async def list_periods(self, session: AsyncSession) -> list[IndexPeriod]:
        rows = (await session.scalars(
            select(IndexMapPeriodORM).order_by(
                IndexMapPeriodORM.updated_at.desc(), IndexMapPeriodORM.period.desc()
            )
        )).all()
        return [_period(row) for row in rows]

    async def _get_period(self, session: AsyncSession, period: str) -> IndexPeriod:
        row = await session.get(IndexMapPeriodORM, period)
        if row is None:
            raise NotFoundException("指数期次不存在")
        return _period(row)

    async def get_overview(self, session: AsyncSession, *, period: str) -> IndexOverview:
        period_model = await self._get_period(session, period)
        rows = (await session.scalars(
            select(IndexMapProvinceORM).where(IndexMapProvinceORM.period == period)
        )).all()
        provinces = tuple(_summary(row) for row in rows)
        score_rows = sorted(
            provinces,
            key=lambda item: (item.index_score is None, -(item.index_score or Decimal(0)), item.province_code),
        )
        return_rows = sorted(
            provinces,
            key=lambda item: (item.annualized_return is None, -(item.annualized_return or Decimal(0)), item.province_code),
        )
        valid_scores = [item.index_score for item in provinces if item.index_score is not None]
        counts = {grade: 0 for grade in ("S", "A", "B")}
        for item in provinces:
            if item.opened and item.grade in counts:
                counts[item.grade] += 1
        return IndexOverview(
            period=period_model,
            provinces=provinces,
            national_average=(sum(valid_scores) / len(valid_scores)) if valid_scores else None,
            leader=score_rows[0] if score_rows and score_rows[0].index_score is not None else None,
            opened_province_count=sum(1 for item in provinces if item.opened and item.grade in {"S", "A", "B"}),
            opened_grade_counts=counts,
            high_potential_count=sum(1 for item in provinces if item.grade == "C"),
            investment_heat=tuple(score_rows[:5]),
            return_stability=tuple(return_rows[:5]),
        )

    async def get_province_detail(
        self, session: AsyncSession, *, period: str, province_code: str
    ) -> ProvinceIndexDetail | None:
        await self._get_period(session, period)
        row = await session.scalar(
            select(IndexMapProvinceORM).where(
                IndexMapProvinceORM.period == period,
                IndexMapProvinceORM.province_code == province_code,
            )
        )
        if row is None:
            raise NotFoundException("省份指数不存在")
        if row.detail_payload is None:
            return None
        return ProvinceIndexDetail(summary=_summary(row), payload=row.detail_payload)
