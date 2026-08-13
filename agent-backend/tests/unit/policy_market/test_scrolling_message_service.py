from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.policy_market.application.scrolling_message_service import ScrollingMessageService
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM
from app.modules.policy_market.interface.serializers import serialize_messages


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
    async with maker() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_messages_returns_only_active_nonexpired_rows_in_display_order(session):
    now = datetime(2026, 7, 23, 9, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="最高", status=1, is_deleted=0, sort_order=10,
            rating=Decimal("4.50"), publish_time=now, tags="政策, 储能",
        ),
        ScrollingMessageORM(
            title="次高", status=1, is_deleted=0, sort_order=10,
            rating=Decimal("3.00"), publish_time=now,
        ),
        ScrollingMessageORM(
            title="已过期", status=1, is_deleted=0,
            expire_time=now - timedelta(seconds=1),
        ),
        ScrollingMessageORM(title="禁用", status=0, is_deleted=0),
        ScrollingMessageORM(title="删除", status=1, is_deleted=1),
    ])
    await session.commit()

    messages = await ScrollingMessageService().list_messages(session, now=now)

    assert [message.title for message in messages] == ["最高", "次高"]
    assert serialize_messages(messages)[0]["tags"] == ["政策", "储能"]


@pytest.mark.asyncio
async def test_list_messages_supports_filters_and_preserves_order(session):
    now = datetime(2026, 7, 23, 12, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="本月内蒙古储能一", province="内蒙古", publish_time=datetime(2026, 7, 5, 9, 0, 0),
            tags="储能, 政策", status=1, is_deleted=0, sort_order=10, rating=Decimal("4.50"),
        ),
        ScrollingMessageORM(
            title="本月内蒙古储能二", province="内蒙古", publish_time=datetime(2026, 7, 6, 9, 0, 0),
            tags="储能", status=1, is_deleted=0, sort_order=8, rating=Decimal("4.00"),
        ),
        ScrollingMessageORM(
            title="上月内蒙古储能", province="内蒙古", publish_time=datetime(2026, 6, 6, 9, 0, 0),
            tags="储能", status=1, is_deleted=0, sort_order=20, rating=Decimal("5.00"),
        ),
        ScrollingMessageORM(
            title="本月山东储能", province="山东", publish_time=datetime(2026, 7, 7, 9, 0, 0),
            tags="储能", status=1, is_deleted=0, sort_order=30, rating=Decimal("5.00"),
        ),
    ])
    await session.commit()

    messages = await ScrollingMessageService().list_messages(
        session,
        province="内蒙古",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 23),
        topic="储能",
        now=now,
    )

    assert [message.title for message in messages] == ["本月内蒙古储能一", "本月内蒙古储能二"]


@pytest.mark.asyncio
async def test_get_overview_filters_real_messages_and_returns_top_topics_and_trend(session):
    now = datetime(2026, 7, 23, 12, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="本月储能一", province="内蒙古", publish_time=datetime(2026, 7, 5, 9, 0, 0),
            tags="储能, 政策", status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="本月储能二", province="内蒙古", publish_time=datetime(2026, 7, 10, 9, 0, 0),
            tags="储能", status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="上月储能", province="内蒙古", publish_time=datetime(2026, 6, 5, 9, 0, 0),
            tags="储能,市场", status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="其他省份", province="山东", publish_time=datetime(2026, 7, 8, 9, 0, 0),
            tags="储能", status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="过期资讯", province="内蒙古", publish_time=datetime(2026, 7, 12, 9, 0, 0),
            tags="储能", status=1, is_deleted=0, expire_time=now - timedelta(seconds=1),
        ),
    ])
    await session.commit()

    overview = await ScrollingMessageService().get_overview(
        session,
        province="内蒙古",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 23),
        topic="储能",
        now=now,
    )

    assert overview.total == 2
    assert overview.trend_percent == 100.0
    assert overview.range_label == "内蒙古 · 2026/07/01 至 2026/07/23"
    assert [(item.value, item.count) for item in overview.topic_options] == [
        ("储能", 2),
        ("政策", 1),
    ]
