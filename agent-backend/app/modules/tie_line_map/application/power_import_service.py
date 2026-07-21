"""联络线功率导入应用服务。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from sqlalchemy import delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.modules.tie_line_map.infrastructure.persistence.orm import (
    TieLineMapORM,
    TieLinePowerORM,
)

POWER_TIME_COLUMNS = tuple(
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in (0, 15, 30, 45)
    if not (hour == 0 and minute == 0)
) + ("24:00",)


@dataclass(frozen=True)
class PowerImportRecord:
    data_date: date
    line_name: str
    voltage_text: str
    powers: Mapping[str, Decimal | None]


@dataclass(frozen=True)
class PowerImportResult:
    received_count: int
    deleted_count: int
    inserted_count: int
    matched_line_count: int


class PowerImportService:
    """校验、匹配并事务内覆盖写入联络线功率数据。"""

    def validate_records(self, records: Sequence[PowerImportRecord]) -> None:
        if not records:
            raise ValidationException("功率数据不能为空")

        keys: set[tuple[date, str, str]] = set()
        expected_times = set(POWER_TIME_COLUMNS)
        for index, record in enumerate(records, start=1):
            if not record.line_name.strip() or not record.voltage_text.strip():
                raise ValidationException(f"第 {index} 条记录的线路名称和电压等级不能为空")
            if set(record.powers) != expected_times:
                raise ValidationException(f"第 {index} 条记录的功率时段不完整或包含额外时段")
            for time_column, value in record.powers.items():
                if value is not None and not value.is_finite():
                    raise ValidationException(f"第 {index} 条记录的 {time_column} 功率必须为有限数值")
            key = (record.data_date, record.line_name, record.voltage_text)
            if key in keys:
                raise ValidationException("请求中存在重复的日期、名称、电压等级组合")
            keys.add(key)

    async def import_records(
        self, session: AsyncSession, records: Sequence[PowerImportRecord]
    ) -> PowerImportResult:
        self.validate_records(records)
        names = sorted({record.line_name for record in records})
        rows = (await session.execute(
            select(TieLineMapORM.id, TieLineMapORM.name).where(TieLineMapORM.name.in_(names))
        )).all()
        line_id_by_name = {name: line_id for line_id, name in rows}
        missing_names = sorted(set(names) - set(line_id_by_name))
        if missing_names:
            raise ValidationException(f"未匹配的联络线名称：{'、'.join(missing_names)}")

        business_keys = [
            (record.data_date, record.line_name, record.voltage_text) for record in records
        ]
        deleted = await session.execute(
            delete(TieLinePowerORM).where(
                tuple_(
                    TieLinePowerORM.data_date,
                    TieLinePowerORM.line_name,
                    TieLinePowerORM.voltage_text,
                ).in_(business_keys)
            )
        )
        entities = []
        for record in records:
            values = {
                "line_id": line_id_by_name[record.line_name],
                "data_date": record.data_date,
                "line_name": record.line_name,
                "voltage_text": record.voltage_text,
            }
            values.update({
                f"power_{time_column.replace(':', '')}_mw": record.powers[time_column]
                for time_column in POWER_TIME_COLUMNS
            })
            entities.append(TieLinePowerORM(**values))
        session.add_all(entities)
        await session.flush()
        return PowerImportResult(
            received_count=len(records),
            deleted_count=deleted.rowcount or 0,
            inserted_count=len(entities),
            matched_line_count=len(line_id_by_name),
        )
