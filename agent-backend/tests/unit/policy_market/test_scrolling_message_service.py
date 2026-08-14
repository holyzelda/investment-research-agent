from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.policy_market.application.scrolling_message_service import ScrollingMessageService
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM
from app.modules.policy_market.interface.serializers import serialize_messages


@pytest_asyncio.fixture
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
    publish_time = datetime(2026, 7, 22, 9, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="最高", status=1, is_deleted=0, sort_order=10,
            rating=Decimal("4.50"), publish_time=publish_time, tags="政策, 储能",
        ),
        ScrollingMessageORM(
            title="次高", status=1, is_deleted=0, sort_order=10,
            rating=Decimal("3.00"), publish_time=publish_time,
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
async def test_list_messages_defaults_to_latest_available_day_before_today(session):
    now = datetime(2026, 8, 14, 15, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="今天的数据不滚动", publish_time=datetime(2026, 8, 14, 9, 0, 0),
            status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="十二日第一条", publish_time=datetime(2026, 8, 12, 8, 0, 0),
            status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="十二日第二条", publish_time=datetime(2026, 8, 12, 10, 0, 0),
            status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="十一日旧数据", publish_time=datetime(2026, 8, 11, 9, 0, 0),
            status=1, is_deleted=0,
        ),
    ])
    await session.commit()

    service = ScrollingMessageService()
    messages = await service.list_messages(session, now=now)
    overview = await service.get_overview(session, now=now)

    assert {message.title for message in messages} == {"十二日第一条", "十二日第二条"}
    assert overview.total == 2
    assert overview.trend_percent is None
    assert overview.range_label == "全部省份 · 2026/08/12"


@pytest.mark.asyncio
async def test_list_messages_returns_empty_when_only_today_has_data(session):
    now = datetime(2026, 8, 14, 15, 0, 0)
    session.add(ScrollingMessageORM(
        title="今天的数据不滚动",
        publish_time=datetime(2026, 8, 14, 9, 0, 0),
        status=1,
        is_deleted=0,
    ))
    await session.commit()

    service = ScrollingMessageService()
    messages = await service.list_messages(session, now=now)
    overview = await service.get_overview(session, now=now)

    assert messages == []
    assert overview.total == 0
    assert overview.range_label == "全部省份 · 暂无历史数据"


@pytest.mark.asyncio
async def test_list_messages_keeps_explicit_date_range(session):
    now = datetime(2026, 8, 14, 15, 0, 0)
    session.add_all([
        ScrollingMessageORM(
            title="十二日数据", publish_time=datetime(2026, 8, 12, 9, 0, 0),
            status=1, is_deleted=0,
        ),
        ScrollingMessageORM(
            title="十一日数据", publish_time=datetime(2026, 8, 11, 9, 0, 0),
            status=1, is_deleted=0,
        ),
    ])
    await session.commit()

    messages = await ScrollingMessageService().list_messages(
        session,
        start_date=date(2026, 8, 11),
        end_date=date(2026, 8, 12),
        now=now,
    )

    assert {message.title for message in messages} == {"十一日数据", "十二日数据"}


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
            title="上月储能", province="内蒙古", publish_time=datetime(2026, 6, 10, 9, 0, 0),
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
