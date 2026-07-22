"""真实 MySQL：正式报告生成任务的模式约束。"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    ReportGenerationTaskORM,
)
from tests.db.conftest import PYTEST_TITLE_PREFIX, PYTEST_USERNAME


async def _new_conversation_and_task(session):
    suffix = uuid.uuid4().hex[:10]
    conversation = ConversationORM(
        user_id=f"report-schema-{suffix}",
        username=PYTEST_USERNAME,
        title=f"{PYTEST_TITLE_PREFIX}报告任务模式 {suffix}",
    )
    session.add(conversation)
    await session.flush()
    task = CalculationTaskORM(
        conversation_id=conversation.id,
        version="V1",
        status="completed",
        retry_count=0,
    )
    session.add(task)
    await session.flush()
    return conversation, task


@pytest.mark.asyncio
async def test_report_generation_task_is_unique_per_calculation_task(db_session):
    conversation, task = await _new_conversation_and_task(db_session)
    generation = ReportGenerationTaskORM(
        task_id=task.id,
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        steps=[{"seq": 1, "key": "prepare", "state": "active"}],
    )
    db_session.add(generation)
    await db_session.flush()

    assert generation.status == "generating"
    assert generation.steps == [{"seq": 1, "key": "prepare", "state": "active"}]
    assert generation.report_id is None

    async with db_session.begin_nested():
        db_session.add(ReportGenerationTaskORM(
            task_id=task.id,
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            steps=[],
        ))
        with pytest.raises(IntegrityError):
            await db_session.flush()
