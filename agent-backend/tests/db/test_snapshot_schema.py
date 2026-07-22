"""真实 MySQL：测算结果与未来正式报告快照的模式约束。"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportSnapshotORM,
)
from tests.db.conftest import PYTEST_TITLE_PREFIX, PYTEST_USERNAME


async def _new_conversation_and_task(session):
    suffix = uuid.uuid4().hex[:10]
    conversation = ConversationORM(
        user_id=f"schema-{suffix}",
        username=PYTEST_USERNAME,
        title=f"{PYTEST_TITLE_PREFIX}快照模式 {suffix}",
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
async def test_calculation_snapshots_reject_second_row_for_same_task(db_session):
    _, task = await _new_conversation_and_task(db_session)
    snapshot_factories = (
        lambda: InputSnapshotORM(task_id=task.id, payload={"kind": "input"}),
        lambda: DataSnapshotORM(task_id=task.id, payload={"kind": "data"}),
        lambda: FeishuIoSnapshotORM(
            task_id=task.id,
            api_input={},
            api_output={},
            api_meta={},
        ),
        lambda: CalculationResultSnapshotORM(task_id=task.id, payload={"kind": "result"}),
    )

    for factory in snapshot_factories:
        db_session.add(factory())
        await db_session.flush()
        async with db_session.begin_nested():
            db_session.add(factory())
            with pytest.raises(IntegrityError):
                await db_session.flush()


@pytest.mark.asyncio
async def test_formal_report_schema_enforces_future_report_contract(db_session):
    conversation, task = await _new_conversation_and_task(db_session)
    report = ReportSnapshotORM(
        report_id=f"report-{uuid.uuid4().hex}",
        task_id=task.id,
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        payload={"kind": "test"},
    )
    db_session.add(report)
    await db_session.flush()

    assert report.schema_version == 1
    assert report.payload == {"kind": "test"}

    async with db_session.begin_nested():
        db_session.add(ReportSnapshotORM(
            report_id=f"report-{uuid.uuid4().hex}",
            task_id=task.id,
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            payload={"kind": "duplicate-task"},
        ))
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_message_snapshot_defaults_to_text_and_accepts_nullable_payload(db_session):
    conversation, task = await _new_conversation_and_task(db_session)
    text_message = MessageSnapshotORM(
        conversation_id=conversation.id,
        role="assistant",
        content="普通消息",
    )
    event_message = MessageSnapshotORM(
        conversation_id=conversation.id,
        role="assistant",
        content="报告已生成",
        message_type="report_generated",
        payload={"report_id": "r-test", "task_id": task.id},
    )
    db_session.add_all((text_message, event_message))
    await db_session.flush()

    assert text_message.message_type == "text"
    assert text_message.payload is None
    assert event_message.payload == {"report_id": "r-test", "task_id": task.id}


@pytest.mark.asyncio
async def test_formal_report_indexes_exist(db_engine):
    async with db_engine.connect() as connection:
        indexes = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_indexes("ir_report_snapshot")
        )

    indexed_columns = {tuple(index["column_names"]) for index in indexes}
    assert ("user_id",) in indexed_columns
    assert ("conversation_id", "created_at") in indexed_columns
