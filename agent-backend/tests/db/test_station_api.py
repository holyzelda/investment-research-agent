"""节点下拉接口：按项目省份搜索并以节点名游标分批读取。"""
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
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"userId": "station-pytest", "username": "__pytest__"},
    ) as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def station_rows(db_engine):
    async with db_engine.begin() as connection:
        await connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ir_spot_station (
                province VARCHAR(64) NOT NULL,
                station_name VARCHAR(128) NOT NULL,
                last_seen DATE NOT NULL,
                PRIMARY KEY (province, station_name)
            )
        """))
        await connection.execute(text(
            "DELETE FROM ir_spot_station WHERE province IN ('分页测试省', '另一测试省')"
        ))
        rows = [
            {"province": "分页测试省", "station": f"节点{index:02d}", "seen": "2026-08-16"}
            for index in range(35)
        ] + [
            {"province": "分页测试省", "station": "百分%节点", "seen": "2026-08-16"},
            {"province": "分页测试省", "station": "下划_节点", "seen": "2026-08-16"},
            {"province": "分页测试省", "station": "感叹!节点", "seen": "2026-08-16"},
            {"province": "另一测试省", "station": "节点00", "seen": "2026-08-16"},
        ]
        await connection.execute(text("""
            INSERT INTO ir_spot_station (province, station_name, last_seen)
            VALUES (:province, :station, :seen)
        """), rows)
    yield
    async with db_engine.begin() as connection:
        await connection.execute(text(
            "DELETE FROM ir_spot_station WHERE province IN ('分页测试省', '另一测试省')"
        ))


@pytest.mark.asyncio
async def test_station_list_returns_an_empty_batch_for_a_province_without_stations(client):
    response = await client.get('/ir/calc/stations', params={'province': '无节点测试省'})

    assert response.status_code == 200
    assert response.json()['data'] == {
        'items': [], 'hasMore': False, 'nextCursor': None,
    }


@pytest.mark.asyncio
async def test_station_list_loads_continuous_cursor_batches(client):
    first = await client.get('/ir/calc/stations', params={
        'province': '分页测试省', 'limit': 30,
    })
    first_data = first.json()['data']

    assert first.status_code == 200
    assert len(first_data['items']) == 30
    assert first_data['hasMore'] is True
    assert first_data['nextCursor'] == first_data['items'][-1]

    second = await client.get('/ir/calc/stations', params={
        'province': '分页测试省', 'limit': 30, 'cursor': first_data['nextCursor'],
    })
    second_data = second.json()['data']

    assert second.status_code == 200
    assert second_data['hasMore'] is False
    assert second_data['nextCursor'] is None
    assert not set(first_data['items']).intersection(second_data['items'])
    assert first_data['items'] + second_data['items'] == sorted(
        first_data['items'] + second_data['items']
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(('keyword', 'expected'), [
    ('节点1', [f'节点{index:02d}' for index in range(10, 20)]),
    ('%', ['百分%节点']),
    ('_', ['下划_节点']),
    ('!', ['感叹!节点']),
])
async def test_station_list_searches_substrings_and_escapes_like_wildcards(
    client, keyword, expected,
):
    response = await client.get('/ir/calc/stations', params={
        'province': '分页测试省', 'keyword': keyword,
    })

    assert response.status_code == 200
    assert response.json()['data']['items'] == expected


@pytest.mark.asyncio
async def test_station_list_filters_province_exactly(client):
    response = await client.get('/ir/calc/stations', params={
        'province': '另一测试省', 'keyword': '节点00',
    })

    assert response.status_code == 200
    assert response.json()['data']['items'] == ['节点00']


@pytest.mark.asyncio
async def test_station_list_rejects_limit_outside_contract(client):
    response = await client.get('/ir/calc/stations', params={
        'province': '分页测试省', 'limit': 101,
    })

    assert response.status_code == 400
    assert response.json()['code'] == 400
