"""会话 UUID 持久化。"""

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
)


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
async def test_conversation_generates_standard_uuid(session):
    conversation = ConversationORM(user_id="u-1", username="张三", title="测试会话")
    session.add(conversation)
    await session.commit()

    UUID(conversation.id)
    stored = (await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation.id)
    )).scalar_one()
    assert stored.id == conversation.id


@pytest.mark.asyncio
async def test_conversations_use_distinct_uuids(session):
    first = ConversationORM(user_id="u-1", username="张三")
    second = ConversationORM(user_id="u-1", username="张三")
    session.add_all([first, second])
    await session.commit()

    assert first.id != second.id


@pytest.mark.asyncio
async def test_duplicate_conversation_uuid_is_rejected(session):
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
    )
    session.add(conversation)
    await session.commit()
    session.expunge(conversation)

    session.add(ConversationORM(
        id=conversation.id,
        user_id="u-2",
        username="李四",
    ))
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_calculation_task_references_uuid_conversation(session):
    conversation = ConversationORM(user_id="u-1", username="张三")
    session.add(conversation)
    await session.flush()
    task = CalculationTaskORM(
        conversation_id=conversation.id,
        version="V1",
        status="created",
        retry_count=0,
    )
    session.add(task)
    await session.commit()

    assert task.conversation_id == conversation.id
