"""中台会话映射持久化。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import ConversationORM


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_persists_middle_platform_session_id(session):
    conversation = ConversationORM(
        user_id="u-1",
        username="张三",
        title="测试会话",
        middle_platform_session_id="platform-session-1",
    )
    session.add(conversation)
    await session.commit()

    stored = (await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation.id)
    )).scalar_one()
    assert stored.middle_platform_session_id == "platform-session-1"


@pytest.mark.asyncio
async def test_same_user_cannot_bind_same_middle_platform_session(session):
    session.add_all([
        ConversationORM(user_id="u-1", username="张三", middle_platform_session_id="s-1"),
        ConversationORM(user_id="u-1", username="张三", middle_platform_session_id="s-1"),
    ])

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_same_user_can_create_multiple_unbound_conversations(session):
    session.add_all([
        ConversationORM(user_id="u-1", username="张三"),
        ConversationORM(user_id="u-1", username="张三"),
    ])
    await session.commit()
