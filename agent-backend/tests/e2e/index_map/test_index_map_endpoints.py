from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.index_map.infrastructure.persistence.orm import IndexMapPeriodORM, IndexMapProvinceORM

NOW = datetime(2026, 7, 28, 10, 0, 0)


@pytest.fixture
async def seeded_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        session.add(IndexMapPeriodORM(period="2026-07", label="2026年7月", updated_at=NOW))
        session.add(IndexMapProvinceORM(
            period="2026-07", province_code="NMG", province_name="蒙西", map_name="内蒙古",
            index_score=95, grade="S", opened=True, rank=1, annualized_return=8.9,
            detail_payload={
                "regionDescription": "内蒙古·西部东送基地",
                "investmentAdvice": "强烈推荐·立即布局",
                "maturity": {"scores": [{"key": "spot", "label": "现货", "score": 92}]},
                "factorContributions": [], "installedStructure": {"items": []},
            }, updated_at=NOW,
        ))
        await session.commit()

    async def override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"userId": "index-map-pytest", "username": "__pytest__"},
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_index_map_query_contract(seeded_client):
    periods = await seeded_client.get("/ir/index-map/periods")
    assert periods.status_code == 200
    assert periods.json()["data"]["items"][0]["period"] == "2026-07"

    overview = await seeded_client.get("/ir/index-map/overview", params={"period": "2026-07"})
    assert overview.status_code == 200
    item = overview.json()["data"]["provinces"][0]
    assert {"provinceCode", "mapName", "indexScore", "grade", "opened", "rank", "updatedAt"} <= item.keys()

    detail = await seeded_client.get("/ir/index-map/provinces/NMG", params={"period": "2026-07"})
    assert detail.status_code == 200
    assert detail.json()["data"]["maturity"]["scores"][0]["key"] == "energy"


@pytest.mark.asyncio
async def test_index_map_validates_period_and_not_found_resources(seeded_client):
    missing_period = await seeded_client.get("/ir/index-map/overview")
    assert missing_period.json()["code"] == 400
    missing_resource = await seeded_client.get("/ir/index-map/overview", params={"period": "unknown"})
    assert missing_resource.json()["code"] == 404
