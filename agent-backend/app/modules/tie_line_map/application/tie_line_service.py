"""tie_line_map 应用层 · 联络线取数用例（只读）。

与 conversation_history_service 一致：application 直接用 SQLAlchemy select
读取 ORM，装配为 domain 值对象返回；表现层聚合（统计/筛选项）由 interface
serializer 派生。联络线为公共基础数据，不做用户归属过滤。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.tie_line_map.application.power_import_service import POWER_TIME_COLUMNS
from app.modules.tie_line_map.domain.models import TieLine, TieLinePowerPoint, TieLinePowerTrend
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM, TieLinePowerORM


def _to_float(value: Decimal | float | None) -> float:
    """经纬度存为 Numeric（Decimal），转 float 供前端/地图直接消费。"""
    return float(value) if value is not None else 0.0


def _to_domain(row: TieLineMapORM) -> TieLine:
    return TieLine(
        id=row.id,
        name=row.name,
        start_point=row.start_point,
        end_point=row.end_point,
        start_region=row.start_region,
        end_region=row.end_region,
        start_longitude=_to_float(row.start_longitude),
        start_latitude=_to_float(row.start_latitude),
        end_longitude=_to_float(row.end_longitude),
        end_latitude=_to_float(row.end_latitude),
        length_text=row.length_text,
        voltage_text=row.voltage_text,
        rated_capacity_mw=row.rated_capacity_mw,
        operation_year=row.operation_year,
        coordinate_basis=row.coordinate_basis,
        data_basis_note=row.data_basis_note,
        source_note=row.source_note,
    )


def _power_attribute_name(time_column: str) -> str:
    return f"power_{time_column.replace(':', '')}_mw"


def _average_power(rows: list[TieLinePowerORM], time_column: str) -> float | None:
    values = [
        value
        for row in rows
        if (value := getattr(row, _power_attribute_name(time_column))) is not None
    ]
    if not values:
        return None
    return float(sum(values, Decimal("0")) / len(values))


class TieLineService:
    async def list_lines(self, session: AsyncSession) -> list[TieLine]:
        rows = (await session.execute(
            select(TieLineMapORM).order_by(TieLineMapORM.name.asc(), TieLineMapORM.id.asc())
        )).scalars().all()
        return [_to_domain(row) for row in rows]

    async def get_line(self, session: AsyncSession, *, line_id: int) -> TieLine:
        row = await session.get(TieLineMapORM, line_id)
        if row is None:
            raise NotFoundException("联络线不存在")
        return _to_domain(row)

    async def get_power_trend(
        self,
        session: AsyncSession,
        *,
        line_id: int,
        start_date: date,
        end_date: date,
    ) -> TieLinePowerTrend:
        line = await session.get(TieLineMapORM, line_id)
        if line is None:
            raise NotFoundException("联络线不存在")

        rows = (await session.execute(
            select(TieLinePowerORM)
            .where(
                TieLinePowerORM.line_id == line_id,
                TieLinePowerORM.data_date >= start_date,
                TieLinePowerORM.data_date <= end_date,
            )
            .order_by(TieLinePowerORM.data_date.asc())
        )).scalars().all()
        return TieLinePowerTrend(
            line_id=line_id,
            start_date=start_date,
            end_date=end_date,
            data_date_count=len(rows),
            points=tuple(
                TieLinePowerPoint(
                    time=time_column,
                    power_mw=_average_power(rows, time_column),
                )
                for time_column in POWER_TIME_COLUMNS
            ),
        )
