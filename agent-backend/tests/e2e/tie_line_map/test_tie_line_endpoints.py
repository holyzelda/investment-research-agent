"""e2e：联络线地图只读接口（ASGITransport + 内存 sqlite 种子数据）。

按项目边界，端点测试不用 Starlette TestClient；用 StaticPool 单连接内存库
建表插种子，并 override get_db_session 注入该会话。
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM


def _seed_rows() -> list[TieLineMapORM]:
    return [
        TieLineMapORM(
            name="祁韶直流", start_point="祁连换流站", end_point="韶关换流站",
            start_region="西北", end_region="南方",
            start_longitude=100.200000, start_latitude=38.400000,
            end_longitude=113.600000, end_latitude=24.800000,
            length_text="3,584.9 km", voltage_text="±800 kV",
            rated_capacity_mw=8000, operation_year=2017,
            coordinate_basis="换流站经纬度", data_basis_note="额定容量",
            source_note="公开资料整理",
        ),
        TieLineMapORM(
            name="宁东直流", start_point="宁东换流站", end_point="绍兴换流站",
            start_region="西北", end_region="华东",
            start_longitude=106.800000, start_latitude=38.000000,
            end_longitude=120.600000, end_latitude=30.000000,
            voltage_text="±660 kV", rated_capacity_mw=4000, operation_year=2011,
        ),
    ]


@pytest.fixture
async def seeded_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        session.add_all(_seed_rows())
        await session.commit()

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_tie_lines(seeded_client):
    resp = await seeded_client.get("/ir/tie-lines")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    # 静态统计（不含任何 MW 时序）
    assert data["stats"]["lineCount"] == 2
    assert data["stats"]["regionCount"] == 3  # 西北/南方/华东
    assert data["stats"]["voltageLevelCount"] == 2
    assert data["stats"]["totalCapacityMw"] == 12000
    # 筛选项
    assert set(data["filters"]["voltageOptions"]) == {"±800 kV", "±660 kV"}
    assert "西北" in data["filters"]["regionOptions"]
    # camelCase 坐标字段齐备
    line = next(x for x in data["items"] if x["name"] == "祁韶直流")
    assert line["startLng"] == 100.2 and line["endLat"] == 24.8
    assert line["voltageText"] == "±800 kV" and line["ratedCapacityMw"] == 8000


@pytest.mark.asyncio
async def test_get_tie_line_detail(seeded_client):
    listed = (await seeded_client.get("/ir/tie-lines")).json()["data"]["items"]
    target = next(x for x in listed if x["name"] == "祁韶直流")
    resp = await seeded_client.get(f"/ir/tie-lines/{target['id']}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    # 详情多出溯源字段
    assert detail["sourceNote"] == "公开资料整理"
    assert detail["coordinateBasis"] == "换流站经纬度"
    assert detail["startPoint"] == "祁连换流站"


@pytest.mark.asyncio
async def test_get_tie_line_not_found(seeded_client):
    resp = await seeded_client.get("/ir/tie-lines/999999")
    assert resp.json()["code"] == 404
