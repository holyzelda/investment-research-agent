from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


@pytest_asyncio.fixture
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
    yesterday = now.date() - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, time.min)
    top_publish_time = yesterday_start + timedelta(hours=9)
    plain_publish_time = yesterday_start + timedelta(hours=8)
    async with maker() as session:
        session.add_all([
            ScrollingMessageORM(
                id=1, title="置顶资讯", summary="储能市场动态",
                link_url="https://example.test/top", province="内蒙古",
                publish_time=top_publish_time, tags="政策,储能",
                status=1, is_deleted=0, sort_order=10, rating=Decimal("4.50"),
            ),
            ScrollingMessageORM(
                id=2, title="普通资讯", status=1, is_deleted=0,
                sort_order=0, rating=Decimal("1.00"), publish_time=plain_publish_time,
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
        yield client, yesterday, now.date()
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_scrolling_messages_returns_response_shell_and_camel_case_dto(seeded_client):
    client, _, _ = seeded_client
    response = await client.get("/ir/policy-market/messages")

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
        "publishTime": body["data"][0]["publishTime"],
        "tags": ["政策", "储能"],
    }
    assert body["data"][0]["publishTime"] is not None


@pytest.mark.asyncio
async def test_market_overview_returns_real_stats_and_validates_date_range(seeded_client):
    client, yesterday, today = seeded_client
    response = await client.get(
        "/ir/policy-market/messages/overview",
        params={"province": "内蒙古", "topic": "储能"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == {
        "total": 1,
        "trendPercent": None,
        "rangeLabel": f"内蒙古 · {yesterday:%Y/%m/%d}",
        "topicOptions": [
            {"value": "储能", "label": "储能", "count": 1},
            {"value": "政策", "label": "政策", "count": 1},
        ],
    }

    filtered_messages = await client.get(
        "/ir/policy-market/messages",
        params={
            "province": "内蒙古",
            "startDate": yesterday.isoformat(),
            "endDate": today.isoformat(),
            "topic": "储能",
        },
    )
    assert filtered_messages.status_code == 200
    assert [item["title"] for item in filtered_messages.json()["data"]] == ["置顶资讯"]

    invalid = await client.get(
        "/ir/policy-market/messages/overview",
        params={"startDate": "2026-08-02", "endDate": "2026-08-01"},
    )

    assert invalid.status_code == 400
    assert invalid.json()["code"] == 400

    incomplete = await client.get(
        "/ir/policy-market/messages",
        params={"startDate": "2026-08-01"},
    )
    assert incomplete.status_code == 400
    assert incomplete.json()["code"] == 400
