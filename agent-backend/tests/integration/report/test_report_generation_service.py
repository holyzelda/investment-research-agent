"""报告生成服务的可观察行为。"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    DataSnapshotORM,
    InputSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)
from app.modules.report.application.report_generation_service import ReportGenerationService
from app.modules.report.application.report_rules import AI_FALLBACK_TEXT
from app.modules.report.infrastructure.fake_ai_client import FakeReportAiClient


async def _new_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _completed_task(session):
    conversation = ConversationORM(user_id="report-user", username="报告用户", title="报告测试")
    session.add(conversation)
    await session.flush()
    task = CalculationTaskORM(conversation_id=conversation.id, version="V1", status="completed")
    session.add(task)
    await session.flush()
    session.add_all([
        InputSnapshotORM(task_id=task.id, payload={
            "minInput": {"province": "甘肃", "powerMw": 200, "capacityMwh": 800},
            "apiInput": {"province": "甘肃", "operation_years": 15},
        }),
        DataSnapshotORM(task_id=task.id, payload={"switches": {"spot": 1}, "warnings": [], "reportSources": {}}),
        CalculationResultSnapshotORM(task_id=task.id, payload={
            "basicInfo": {"province": "甘肃", "powerMw": 200, "capacityMwh": 800},
        }),
    ])
    await session.commit()
    return task.id


@pytest.mark.asyncio
async def test_retries_only_failed_ai_section_then_freezes_fallback_without_failing_report():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            service = ReportGenerationService(ai_client=FakeReportAiClient(failures={"sensitivity": 3}))
            started = await service.start(session, task_id=task_id, user_id="report-user")

            await service.run(session, report_task_id=started["reportTaskId"])

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            report = (await session.execute(
                select(ReportSnapshotORM).where(ReportSnapshotORM.report_id == generation.report_id)
            )).scalar_one()
            assert generation.status == "completed"
            assert report.payload["aiSections"]["sensitivity"] == {
                "status": "fallback",
                "attempts": 3,
                "usedFallback": True,
                "text": AI_FALLBACK_TEXT,
            }
            assert report.payload["aiSections"]["debt_service_coverage"]["usedFallback"] is False
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reuses_existing_generation_and_returns_the_final_report_for_repeated_requests():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            service = ReportGenerationService(ai_client=FakeReportAiClient())

            first = await service.start(session, task_id=task_id, user_id="report-user")
            second = await service.start(session, task_id=task_id, user_id="report-user")
            assert second["reportTaskId"] == first["reportTaskId"]
            assert second["status"] == "generating"

            await service.run(session, report_task_id=first["reportTaskId"])
            completed = await service.start(session, task_id=task_id, user_id="report-user")
            assert completed["status"] == "completed"
            assert completed["taskId"] == task_id
            assert completed["reportId"]
    finally:
        await engine.dispose()
