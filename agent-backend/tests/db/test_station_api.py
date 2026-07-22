"""节点下拉接口：按项目省份读取 ir_spot_station 维表。"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.session import get_db_session
from app.main import app


@pytest.fixture
async def client(db_engine):
    maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_station_list_returns_an_empty_list_for_a_province_without_stations(client, db_engine):
    async with db_engine.begin() as connection:
        await connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ir_spot_station (
                province VARCHAR(64) NOT NULL,
                station_name VARCHAR(128) NOT NULL,
                last_seen DATE NOT NULL,
                PRIMARY KEY (province, station_name)
            )
        """))

    response = await client.get('/ir/calc/stations', params={'province': '宁夏'})

    assert response.status_code == 200
    assert response.json()['data'] == {'items': []}
