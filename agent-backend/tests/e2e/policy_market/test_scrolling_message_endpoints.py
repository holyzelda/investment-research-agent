from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


@pytest.fixture
async def seeded_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    now = datetime.now()
    async with maker() as session:
        session.add_all([
            ScrollingMessageORM(
                id=1, title="置顶资讯", summary="储能市场动态",
                link_url="https://example.test/top", province="内蒙古",
                publish_time=datetime(2026, 7, 23, 9, 0, 0), tags="政策,储能",
                status=1, is_deleted=0, sort_order=10, rating=Decimal("4.50"),
            ),
            ScrollingMessageORM(
                id=2, title="普通资讯", status=1, is_deleted=0,
                sort_order=0, rating=Decimal("1.00"), publish_time=datetime(2026, 7, 22, 9, 0, 0),
            ),
            ScrollingMessageORM(title="已过期", status=1, is_deleted=0, expire_time=now - timedelta(days=1)),
            ScrollingMessageORM(title="禁用", status=0, is_deleted=0),
            ScrollingMessageORM(title="删除", status=1, is_deleted=1),
        ])
        await session.commit()

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"userId": "policy-market-pytest", "username": "__pytest__"},
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_scrolling_messages_returns_response_shell_and_camel_case_dto(seeded_client):
    response = await seeded_client.get("/ir/policy-market/messages")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert [item["title"] for item in body["data"]] == ["置顶资讯", "普通资讯"]
    assert body["data"][0] == {
        "id": 1,
        "title": "置顶资讯",
        "summary": "储能市场动态",
        "linkUrl": "https://example.test/top",
        "province": "内蒙古",
        "publishTime": "2026-07-23T09:00:00",
        "tags": ["政策", "储能"],
    }


@pytest.mark.asyncio
async def test_market_overview_returns_real_stats_and_rejects_invalid_period(seeded_client):
    response = await seeded_client.get(
        "/ir/policy-market/messages/overview",
        params={"province": "内蒙古", "period": "all", "topic": "储能"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == {
        "total": 1,
        "trendPercent": None,
        "rangeLabel": "内蒙古 · 全部时间",
        "topicOptions": [
            {"value": "储能", "label": "储能", "count": 1},
            {"value": "政策", "label": "政策", "count": 1},
        ],
    }

    filtered_messages = await seeded_client.get(
        "/ir/policy-market/messages",
        params={"province": "内蒙古", "period": "month", "topic": "储能"},
    )
    assert filtered_messages.status_code == 200
    assert [item["title"] for item in filtered_messages.json()["data"]] == ["置顶资讯"]

    invalid = await seeded_client.get(
        "/ir/policy-market/messages/overview",
        params={"period": "year"},
    )

    assert invalid.status_code == 400
    assert invalid.json()["code"] == 400
