from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import NotFoundException
from app.infrastructure.database.base import Base
from app.modules.index_map.application.index_map_service import IndexMapService
from app.modules.index_map.infrastructure.persistence.orm import IndexMapPeriodORM, IndexMapProvinceORM

NOW = datetime(2026, 7, 28, 10, 0, 0)


def _province(period, code, score, grade, opened, rank, annualized_return, payload=None):
    return IndexMapProvinceORM(
        period=period,
        province_code=code,
        province_name=code,
        map_name=code,
        index_score=score,
        grade=grade,
        opened=opened,
        rank=rank,
        annualized_return=annualized_return,
        detail_payload=payload,
        updated_at=NOW,
    )


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_overview_uses_score_then_code_for_heat_ranking(session):
    session.add_all([
        IndexMapPeriodORM(period="2026-06", label="2026年6月", updated_at=NOW),
        IndexMapPeriodORM(period="2026-07", label="2026年7月", updated_at=NOW),
        _province("2026-07", "B", 90, "S", True, 2, 7.1),
        _province("2026-07", "A", 90, "S", True, 1, 8.1),
        _province("2026-07", "C", 60, "C", False, 3, 9.1),
        _province("2026-07", "X", None, "X", False, None, None),
    ])
    await session.commit()

    overview = await IndexMapService().get_overview(session, period="2026-07")

    assert [item.province_code for item in overview.investment_heat] == ["A", "B", "C", "X"]
    assert [item.province_code for item in overview.return_stability] == ["C", "A", "B", "X"]
    assert overview.opened_grade_counts == {"S": 2, "A": 0, "B": 0}
    assert overview.high_potential_count == 1
    assert overview.national_average == Decimal("80.00")
    assert overview.leader.province_code == "A"


@pytest.mark.asyncio
async def test_periods_descend_and_detail_requires_existing_payload(session):
    session.add_all([
        IndexMapPeriodORM(period="old", label="旧期", updated_at=datetime(2026, 6, 1)),
        IndexMapPeriodORM(period="new", label="新期", updated_at=datetime(2026, 7, 1)),
        _province("new", "NMG", 95, "S", True, 1, 8.9),
    ])
    await session.commit()
    service = IndexMapService()

    assert [item.period for item in await service.list_periods(session)] == ["new", "old"]
    assert await service.get_province_detail(session, period="new", province_code="NMG") is None
    with pytest.raises(NotFoundException):
        await service.get_overview(session, period="missing")
    with pytest.raises(NotFoundException):
        await service.get_province_detail(session, period="new", province_code="missing")
