"""e2e：联络线功率趋势查询接口。"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.tie_line_map.application.power_import_service import POWER_TIME_COLUMNS
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM, TieLinePowerORM


def _powers(**overrides):
    return {
        f"power_{time.replace(':', '')}_mw": overrides.get(time, Decimal("10.000"))
        for time in POWER_TIME_COLUMNS
    }


@pytest.fixture
async def seeded_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yesterday = date.today() - timedelta(days=1)
    async with maker() as session:
        line = TieLineMapORM(
            name="甲乙线",
            start_point="甲站",
            end_point="乙站",
            start_region="西北",
            end_region="华南",
            start_longitude=100,
            start_latitude=30,
            end_longitude=110,
            end_latitude=25,
        )
        other = TieLineMapORM(
            name="丙丁线",
            start_point="丙站",
            end_point="丁站",
            start_region="华北",
            end_region="华东",
            start_longitude=115,
            start_latitude=35,
            end_longitude=120,
            end_latitude=31,
        )
        session.add_all([line, other])
        await session.flush()
        session.add_all([
            TieLinePowerORM(
                line_id=line.id,
                data_date=yesterday,
                line_name="甲乙线",
                voltage_text="±800 kV",
                **_powers(**{"00:15": Decimal("100.000"), "00:30": None}),
            ),
            TieLinePowerORM(
                line_id=line.id,
                data_date=yesterday - timedelta(days=1),
                line_name="甲乙线",
                voltage_text="±800 kV",
                **_powers(**{"00:15": Decimal("200.000"), "00:30": None}),
            ),
            TieLinePowerORM(
                line_id=other.id,
                data_date=yesterday,
                line_name="丙丁线",
                voltage_text="±500 kV",
                **_powers(**{"00:15": Decimal("999.000")}),
            ),
        ])
        await session.commit()

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"userId": "tie-line-pytest", "username": "__pytest__"},
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


async def _line_id(client: AsyncClient, name: str) -> int:
    data = (await client.get("/ir/tie-lines")).json()["data"]
    return next(item["id"] for item in data["items"] if item["name"] == name)


@pytest.mark.asyncio
async def test_single_day_power_returns_all_96_original_points(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")

    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={"startDate": yesterday.isoformat(), "endDate": yesterday.isoformat()},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["lineId"] == line_id
    assert data["startDate"] == yesterday.isoformat()
    assert data["endDate"] == yesterday.isoformat()
    assert data["dataDateCount"] == 1
    assert len(data["points"]) == 96
    assert data["points"][0] == {"time": "00:15", "powerMw": 100.0}
    assert data["points"][1] == {"time": "00:30", "powerMw": None}
    assert data["points"][-1]["time"] == "24:00"


@pytest.mark.asyncio
async def test_multi_day_power_averages_each_time_and_ignores_nulls(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")

    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={
            "startDate": (yesterday - timedelta(days=1)).isoformat(),
            "endDate": yesterday.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dataDateCount"] == 2
    assert data["points"][0] == {"time": "00:15", "powerMw": 150.0}
    assert data["points"][1] == {"time": "00:30", "powerMw": None}


@pytest.mark.asyncio
async def test_power_returns_null_points_when_range_has_no_records(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")

    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={
            "startDate": (yesterday - timedelta(days=10)).isoformat(),
            "endDate": (yesterday - timedelta(days=9)).isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dataDateCount"] == 0
    assert len(data["points"]) == 96
    assert all(point["powerMw"] is None for point in data["points"])


@pytest.mark.asyncio
async def test_power_returns_404_for_unknown_line(seeded_client):
    yesterday = date.today() - timedelta(days=1)

    response = await seeded_client.get(
        "/ir/tie-lines/999999/power",
        params={"startDate": yesterday.isoformat(), "endDate": yesterday.isoformat()},
    )

    assert response.status_code == 404
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_power_rejects_invalid_or_unfinished_dates(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    today = date.today()
    line_id = await _line_id(seeded_client, "甲乙线")

    cases = [
        {"startDate": yesterday.isoformat(), "endDate": (yesterday - timedelta(days=1)).isoformat()},
        {"startDate": today.isoformat(), "endDate": today.isoformat()},
        {"startDate": "not-a-date", "endDate": yesterday.isoformat()},
        {"endDate": yesterday.isoformat()},
    ]
    for params in cases:
        response = await seeded_client.get(f"/ir/tie-lines/{line_id}/power", params=params)
        assert response.status_code == 400
        assert response.json()["code"] == 400
