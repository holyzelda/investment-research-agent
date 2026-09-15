"""报告生成与试用额度的集成：预占、成功保留、失败回退。"""
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
)
from app.modules.report.application.report_generation_service import ReportGenerationService
from app.modules.trial_quota.application.trial_quota_service import (
    TRIAL_DAILY_LIMIT,
    TrialQuotaExceeded,
    TrialQuotaService,
)
from app.modules.trial_quota.infrastructure.persistence.orm import TrialDailyUsageORM


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


async def _report_used(session, user_id: str) -> int:
    row = await session.get(TrialDailyUsageORM, user_id)
    return 0 if row is None else row.report_used


class OkAiClient:
    async def generate_section(self, rule, context, *, user_id="", username=""):
        return f"{rule['key']} 正文"


@pytest.mark.asyncio
async def test_trial_start_reserves_quota_and_success_keeps_it():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            service = ReportGenerationService(ai_client=OkAiClient())
            quota = TrialQuotaService()

            started = await service.start(
                session, task_id=task_id, user_id="report-user",
                username="报告用户", is_trial=True, trial_quota=quota,
            )

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.trial_quota_reserved is True
            assert await _report_used(session, "report-user") == 1

            await service.run(session, report_task_id=started["reportTaskId"])

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.status == "completed"
            assert generation.trial_quota_reserved is False
            assert generation.trial_quota_usage_date is None
            assert await _report_used(session, "report-user") == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_trial_run_failure_refunds_reserved_quota():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            service = ReportGenerationService(ai_client=OkAiClient())
            quota = TrialQuotaService()

            started = await service.start(
                session, task_id=task_id, user_id="report-user",
                username="报告用户", is_trial=True, trial_quota=quota,
            )
            assert await _report_used(session, "report-user") == 1

            # 后台故障：冻结入参快照缺失（模拟运行期真实故障），run 走失败回退。
            input_row = (await session.execute(
                select(InputSnapshotORM).where(InputSnapshotORM.task_id == task_id)
            )).scalar_one()
            await session.delete(input_row)
            await session.commit()

            await service.run(session, report_task_id=started["reportTaskId"])

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.status == "failed"
            assert generation.trial_quota_reserved is False
            assert await _report_used(session, "report-user") == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_non_trial_start_never_reserves_quota():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            service = ReportGenerationService(ai_client=OkAiClient())

            started = await service.start(
                session, task_id=task_id, user_id="report-user",
                username="报告用户", is_trial=False,
            )

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.trial_quota_reserved is False
            assert await _report_used(session, "report-user") == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_exhausted_report_quota_blocks_new_generation():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            quota = TrialQuotaService()
            for _ in range(TRIAL_DAILY_LIMIT):
                await quota.reserve(session, "report-user", "report")

            service = ReportGenerationService(ai_client=OkAiClient())
            with pytest.raises(TrialQuotaExceeded):
                await service.start(
                    session, task_id=task_id, user_id="report-user",
                    username="报告用户", is_trial=True, trial_quota=quota,
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_generation_can_retry_after_refund():
    """失败回退后，同一任务重试可再次预占（次数不重复累计）。"""
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            quota = TrialQuotaService()

            service = ReportGenerationService(ai_client=OkAiClient())
            started = await service.start(
                session, task_id=task_id, user_id="report-user",
                username="报告用户", is_trial=True, trial_quota=quota,
            )
            input_row = (await session.execute(
                select(InputSnapshotORM).where(InputSnapshotORM.task_id == task_id)
            )).scalar_one()
            await session.delete(input_row)
            await session.commit()
            await service.run(session, report_task_id=started["reportTaskId"])
            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.status == "failed"
            assert await _report_used(session, "report-user") == 0

            # 补回快照后重试：再次预占，成功后保留（只计一次）。
            session.add(InputSnapshotORM(task_id=task_id, payload={
                "minInput": {"province": "甘肃", "powerMw": 200, "capacityMwh": 800},
                "apiInput": {"province": "甘肃", "operation_years": 15},
            }))
            await session.commit()
            retried = await service.start(
                session, task_id=task_id, user_id="report-user",
                username="报告用户", is_trial=True, trial_quota=quota,
            )
            assert retried["reportTaskId"] == started["reportTaskId"]
            assert await _report_used(session, "report-user") == 1

            await service.run(session, report_task_id=started["reportTaskId"])
            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            assert generation.status == "completed"
            assert await _report_used(session, "report-user") == 1
    finally:
        await engine.dispose()
