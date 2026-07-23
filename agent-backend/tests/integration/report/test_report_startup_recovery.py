"""报告任务启动恢复。"""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    ReportGenerationTaskORM,
)
from app.modules.report.application.startup_recovery import mark_interrupted_generations_failed


@pytest.mark.asyncio
async def test_marks_only_interrupted_generating_report_tasks_as_failed():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            conversation = ConversationORM(user_id="u1", username="用户")
            session.add(conversation)
            await session.flush()
            generating_task = CalculationTaskORM(conversation_id=conversation.id, version="V1", status="completed")
            completed_task = CalculationTaskORM(conversation_id=conversation.id, version="V2", status="completed")
            session.add_all([generating_task, completed_task])
            await session.flush()
            session.add_all([
                ReportGenerationTaskORM(task_id=generating_task.id, conversation_id=conversation.id, user_id="u1", steps=[], status="generating"),
                ReportGenerationTaskORM(task_id=completed_task.id, conversation_id=conversation.id, user_id="u1", steps=[], status="completed"),
            ])
            await session.commit()

            assert await mark_interrupted_generations_failed(session) == 1
            assert (await session.get(ReportGenerationTaskORM, 1)).error_code == "report_generation_interrupted"
            assert (await session.get(ReportGenerationTaskORM, 2)).status == "completed"
    finally:
        await engine.dispose()
