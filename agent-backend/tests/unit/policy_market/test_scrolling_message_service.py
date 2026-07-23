from datetime import datetime, timedelta
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
