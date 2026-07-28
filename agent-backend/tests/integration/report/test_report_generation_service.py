"""报告生成服务的可观察行为。"""
from __future__ import annotations

import asyncio

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
from app.modules.report.application.report_rules import AI_FALLBACK_TEXT, AI_SECTION_RULES
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


class BlockingAiClient:
    def __init__(self, expected_active):
        self.expected_active = expected_active
        self.active = 0
        self.max_active = 0
        self.started = 0
        self.batch_started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_section(self, rule, context, *, user_id="", username=""):
        self.active += 1
        self.started += 1
        self.max_active = max(self.max_active, self.active)
        if self.active == self.expected_active:
            self.batch_started.set()
        try:
            await self.release.wait()
            return f"{rule['key']} 正文"
        finally:
            self.active -= 1


class YieldingAiClient:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def generate_section(self, rule, context, *, user_id="", username=""):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            return f"{rule['key']} 正文"
        finally:
            self.active -= 1


class OutOfOrderAiClient:
    async def generate_section(self, rule, context, *, user_id="", username=""):
        key = rule["key"]
        if key == "debt_service_coverage":
            await asyncio.sleep(0.02)
        if key == "sensitivity":
            raise RuntimeError("单节失败")
        return f"{key} 正文"


@pytest.mark.asyncio
async def test_generates_all_five_ai_sections_concurrently():
    client = BlockingAiClient(expected_active=5)
    service = ReportGenerationService(ai_client=client, ai_concurrency=5)

    pending = asyncio.create_task(service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    ))
    await asyncio.wait_for(client.batch_started.wait(), timeout=1)
    assert client.started == 5
    assert client.max_active == 5
    client.release.set()

    sections = await pending
    assert list(sections) == [rule["key"] for rule in AI_SECTION_RULES]
    assert all(section["status"] == "generated" for section in sections.values())


@pytest.mark.asyncio
async def test_report_ai_concurrency_respects_configured_limit():
    client = YieldingAiClient()
    service = ReportGenerationService(ai_client=client, ai_concurrency=2)

    sections = await service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    )

    assert client.max_active == 2
    assert len(sections) == 5


@pytest.mark.asyncio
async def test_parallel_results_keep_rule_order_and_isolate_failure():
    service = ReportGenerationService(
        ai_client=OutOfOrderAiClient(), ai_concurrency=5
    )

    sections = await service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    )

    assert list(sections) == [rule["key"] for rule in AI_SECTION_RULES]
    assert sections["sensitivity"]["status"] == "fallback"
    assert sections["sensitivity"]["failureCode"] == "ai_output_validation_failed"
    assert all(
        section["status"] == "generated"
        for key, section in sections.items()
        if key != "sensitivity"
    )


@pytest.mark.asyncio
async def test_calls_ai_even_when_some_frozen_report_data_is_missing():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            client = FakeReportAiClient(failures={"sensitivity": 3})
            service = ReportGenerationService(ai_client=client)
            started = await service.start(session, task_id=task_id, user_id="report-user")

            await service.run(session, report_task_id=started["reportTaskId"])

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            report = (await session.execute(
                select(ReportSnapshotORM).where(ReportSnapshotORM.report_id == generation.report_id)
            )).scalar_one()
            assert generation.status == "completed"
            assert client.calls == {
                "debt_service_coverage": 1, "operating_cashflow": 1,
                "accounting_profit": 1, "sensitivity": 1, "investment_conclusion": 1,
            }
            assert report.payload["aiSections"]["sensitivity"]["failureCode"] == "ai_output_validation_failed"
            assert report.payload["aiSections"]["sensitivity"]["text"] == AI_FALLBACK_TEXT
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_generates_and_freezes_ai_sections_from_snapshot_report_sources():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            task_id = await _completed_task(session)
            data = (await session.execute(
                select(DataSnapshotORM).where(DataSnapshotORM.task_id == task_id)
            )).scalar_one()
            data.payload = {
                "switches": {"switch_spot": 1},
                "warnings": ["冻结提示"],
                "reportSources": {
                    "charts": {
                        "available": True,
                        "series": {
                            "debtServiceCoverage": [1.2, 1.3],
                            "principal": [100, 90], "interest": [20, 10],
                            "operatingCashflow": [150, 140], "freeCashflow": [30, 40],
                            "netProfit": [20, 30], "depreciationAmortization": [60, 55],
                        },
                        "sensitivity": {"baseline": 1.2, "optimistic": 1.4, "pessimistic": 1.1},
                    },
                },
            }
            await session.commit()
            client = FakeReportAiClient()
            service = ReportGenerationService(ai_client=client)
            started = await service.start(
                session, task_id=task_id, user_id="report-user", username="报告用户"
            )

            await service.run(session, report_task_id=started["reportTaskId"])

            generation = await session.get(ReportGenerationTaskORM, started["reportTaskId"])
            report = (await session.execute(
                select(ReportSnapshotORM).where(ReportSnapshotORM.report_id == generation.report_id)
            )).scalar_one()
            assert client.calls == {
                "debt_service_coverage": 1, "operating_cashflow": 1,
                "accounting_profit": 1, "sensitivity": 1, "investment_conclusion": 1,
            }
            assert all(section["status"] == "generated" for section in report.payload["aiSections"].values())
            assert all(section["usedFallback"] is False for section in report.payload["aiSections"].values())
            assert report.payload["aiSections"]["sensitivity"]["text"].startswith("甘肃")
    finally:
        await engine.dispose()

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
