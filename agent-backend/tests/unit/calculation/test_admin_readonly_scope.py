"""只读放权边界：管理员可读组织成员的会话/任务，写操作与越权仍是 404。

readable_user_ids 只从 UserScope 传入只读端点；重命名、删除、追加测算等写路径
不传该参数，归属判断保持"仅本人"。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import NotFoundException
from app.infrastructure.database.base import Base
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
)

ADMIN = "119"
MEMBER = "120"
OUTSIDER = "999"
ORG = [ADMIN, MEMBER]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest_asyncio.fixture
async def member_task(session):
    session.add(ConversationORM(
        id="c-member", user_id=MEMBER, username="bjjzB", title="宁夏 独立储能",
    ))
    await session.flush()
    task = CalculationTaskORM(conversation_id="c-member", version="V1", status="completed")
    session.add(task)
    await session.commit()
    return task.id


async def test_admin_can_read_a_member_conversation_and_task(session, member_task):
    service = ConversationHistoryService()

    conversation = await service.require_active_conversation(
        session, conversation_id="c-member", user_id=ADMIN, readable_user_ids=ORG,
    )
    task = await service.require_owned_task(
        session, task_id=member_task, user_id=ADMIN, readable_user_ids=ORG,
    )

    assert conversation.user_id == MEMBER
    assert task.id == member_task


async def test_reads_outside_the_scope_stay_not_found(session, member_task):
    service = ConversationHistoryService()

    with pytest.raises(NotFoundException):
        await service.require_active_conversation(
            session, conversation_id="c-member", user_id=OUTSIDER,
            readable_user_ids=[OUTSIDER],
        )
    with pytest.raises(NotFoundException):
        await service.require_owned_task(
            session, task_id=member_task, user_id=OUTSIDER, readable_user_ids=[OUTSIDER],
        )


async def test_write_paths_without_scope_remain_self_only(session, member_task):
    service = ConversationHistoryService()

    with pytest.raises(NotFoundException):
        await service.rename(
            session, conversation_id="c-member", user_id=ADMIN, title="管理员改名",
        )
    with pytest.raises(NotFoundException):
        await service.soft_delete(session, conversation_id="c-member", user_id=ADMIN)
