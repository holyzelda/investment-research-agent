"""联络线功率导入端点测试。"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.tie_line_map.application.power_import_service import POWER_TIME_COLUMNS
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM, TieLinePowerORM


@pytest.fixture
async def power_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as session:
        session.add(TieLineMapORM(
            name="祁韶直流", start_point="祁连换流站", end_point="韶关换流站",
            start_region="西北", end_region="南方",
            start_longitude=100, start_latitude=38,
            end_longitude=113, end_latitude=24,
        ))
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
        yield client, maker
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


def _payload(value: int = 100) -> dict:
    return {
        "records": [{
            "dataDate": "2025-01-01",
            "lineName": "祁韶直流",
            "voltageText": "±800kV",
            "powers": {time: value for time in POWER_TIME_COLUMNS},
        }],
    }


def _excel_bytes(value: int = 100, *, valid_header: bool = True) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "功率"
    header = ["日期", "名称", "电压等级", *POWER_TIME_COLUMNS]
    sheet.append(header if valid_header else ["错误列", *header[1:]])
    sheet.append([date(2025, 1, 2), "祁韶直流", "±800kV", *([value] * 96)])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_import_json_replaces_existing_record(power_client):
    client, maker = power_client
    first = await client.post("/ir/tie-lines/power/import", json=_payload(100))
    second = await client.post("/ir/tie-lines/power/import", json=_payload(200))

    assert first.status_code == 200
    assert first.json()["data"]["insertedCount"] == 1
    assert second.status_code == 200
    assert second.json()["data"]["deletedCount"] == 1
    assert second.json()["data"]["insertedCount"] == 1
    async with maker() as session:
        row = (await session.execute(select(TieLinePowerORM))).scalar_one()
        assert row.power_0015_mw == Decimal("200")


@pytest.mark.asyncio
async def test_import_excel_succeeds(power_client):
    client, maker = power_client
    response = await client.post(
        "/ir/tie-lines/power/import",
        files={"file": ("power.xlsx", _excel_bytes(300), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["insertedCount"] == 1
    async with maker() as session:
        assert await session.scalar(select(func.count()).select_from(TieLinePowerORM)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"json": {"records": [{**_payload()["records"][0], "powers": {"00:15": 1}}]}},
        {"json": {"records": [{**_payload()["records"][0], "lineName": "未知线路"}]}},
        {"json": {"records": [_payload()["records"][0], _payload()["records"][0]]}},
        {"files": {"file": ("power.xlsx", _excel_bytes(valid_header=False), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}},
        {"content": "plain", "headers": {"content-type": "text/plain"}},
    ],
)
async def test_import_invalid_request_returns_400_without_writing(power_client, request_kwargs):
    client, maker = power_client
    response = await client.post("/ir/tie-lines/power/import", **request_kwargs)

    assert response.status_code == 400
    assert response.json()["code"] == 400
    async with maker() as session:
        assert await session.scalar(select(func.count()).select_from(TieLinePowerORM)) == 0
