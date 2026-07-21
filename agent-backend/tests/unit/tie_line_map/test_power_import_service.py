"""联络线功率导入应用服务测试。"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import ValidationException
from app.infrastructure.database.base import Base
from app.modules.tie_line_map.application.power_import_service import (
    POWER_TIME_COLUMNS,
    PowerImportRecord,
    PowerImportService,
)
from app.modules.tie_line_map.infrastructure.persistence.orm import (
    TieLineMapORM,
    TieLinePowerORM,
)


@pytest.fixture
async def power_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as session:
        line = TieLineMapORM(
            name="吉泉直流", start_point="起点", end_point="终点",
            start_region="西北", end_region="华东",
            start_longitude=100, start_latitude=38,
            end_longitude=120, end_latitude=30,
        )
        session.add(line)
        await session.commit()
        yield session, line.id
    await engine.dispose()


def _record(value: Decimal = Decimal("8799"), *, name: str = "吉泉直流") -> PowerImportRecord:
    return PowerImportRecord(
        data_date=date(2025, 1, 1),
        line_name=name,
        voltage_text="±1100kV",
        powers={time: value for time in POWER_TIME_COLUMNS},
    )


@pytest.mark.asyncio
async def test_import_replaces_same_business_key_and_uses_matched_line_id(power_session):
    session, line_id = power_session
    service = PowerImportService()

    first = await service.import_records(session, [_record()])
    await session.commit()
    second = await service.import_records(session, [_record(Decimal("8800"))])
    await session.commit()

    row = (await session.execute(select(TieLinePowerORM))).scalar_one()
    assert first.deleted_count == 0
    assert first.inserted_count == 1
    assert second.deleted_count == 1
    assert second.inserted_count == 1
    assert row.line_id == line_id
    assert row.power_0015_mw == Decimal("8800")


@pytest.mark.asyncio
async def test_import_rejects_unknown_line_before_writing(power_session):
    session, _ = power_session

    with pytest.raises(ValidationException, match="未匹配"):
        await PowerImportService().import_records(session, [_record(name="不存在的线路")])

    assert (await session.scalar(select(func.count()).select_from(TieLinePowerORM))) == 0


def test_validate_records_rejects_duplicate_keys_and_incomplete_times():
    service = PowerImportService()

    with pytest.raises(ValidationException, match="重复"):
        service.validate_records([_record(), _record()])

    incomplete = _record()
    incomplete.powers.pop("24:00")
    with pytest.raises(ValidationException, match="时段"):
        service.validate_records([incomplete])
