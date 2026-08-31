"""测算台账查询：只读已完成测算，按会话名称/省份/时间筛选并分页。"""
from __future__ import annotations

from datetime import date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.modules.calculation.application.calculation_ledger_service import CalculationLedgerService
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


async def _conversation(session, *, conversation_id, title, user_id="1001", deleted_at=None):
    session.add(ConversationORM(
        id=conversation_id, user_id=user_id, username="tester",
        title=title, deleted_at=deleted_at,
    ))
    await session.commit()
    return conversation_id


async def _completed_task(
    session, *, conversation_id, version, created_at, province,
    status="completed", power_mw=200.0, capacity_mwh=800.0, node_name="兰州东",
    project_irr=8.5, payback=9.2, with_result=True,
):
    task = CalculationTaskORM(
        conversation_id=conversation_id, version=version, status=status,
        created_at=created_at,
    )
    session.add(task)
    await session.flush()
    session.add(InputSnapshotORM(task_id=task.id, payload={
        "apiInput": {"province": province, "power_mw": power_mw, "capacity_mwh": capacity_mwh},
        "minInput": {"province": province, "nodeName": node_name},
    }))
    if with_result:
        session.add(CalculationResultSnapshotORM(task_id=task.id, payload={
            "basicInfo": {
                "province": province, "nodeName": node_name,
                "powerMw": power_mw, "capacityMwh": capacity_mwh,
            },
            "financial": {"projectIrr": project_irr, "projectStaticPayback": payback},
        }))
    await session.commit()
    return task.id


@pytest.mark.asyncio
async def test_serializes_canonical_city_from_frozen_snapshots(session):
    conversation = await _conversation(session, conversation_id="henan", title="河南 储能测算")
    task_id = await _completed_task(
        session, conversation_id=conversation, version="V1",
        created_at=datetime(2026, 8, 10, 10, 0), province="河南", node_name=None,
    )
    snapshot = await session.get(InputSnapshotORM, task_id)
    snapshot.payload["apiInput"]["city"] = "郑州"
    snapshot.payload["minInput"]["city"] = "郑州"
    result = await session.get(CalculationResultSnapshotORM, task_id)
    result.payload["basicInfo"]["city"] = "郑州"
    await session.commit()

    item = (await CalculationLedgerService().list_records(session, user_id="1001"))["items"][0]

    assert item["city"] == "郑州"
    assert "cityName" not in item


@pytest.mark.asyncio
async def test_lists_only_completed_tasks_of_the_current_user(session):
    mine = await _conversation(session, conversation_id="c-1", title="甘肃 储能测算")
    others = await _conversation(session, conversation_id="c-2", title="别人的项目", user_id="2002")
    deleted = await _conversation(
        session, conversation_id="c-3", title="已删除会话", deleted_at=datetime(2026, 8, 1, 9, 0),
    )
    ok_task = await _completed_task(
        session, conversation_id=mine, version="V1",
        created_at=datetime(2026, 8, 10, 10, 0), province="甘肃",
    )
    await _completed_task(
        session, conversation_id=mine, version="V2", status="failed",
        created_at=datetime(2026, 8, 11, 10, 0), province="甘肃",
    )
    await _completed_task(
        session, conversation_id=others, version="V1",
        created_at=datetime(2026, 8, 10, 11, 0), province="宁夏",
    )
    await _completed_task(
        session, conversation_id=deleted, version="V1",
        created_at=datetime(2026, 8, 10, 12, 0), province="山西",
    )

    data = await CalculationLedgerService().list_records(session, user_id="1001")

    assert data["total"] == 1
    assert [item["taskId"] for item in data["items"]] == [ok_task]
    item = data["items"][0]
    assert item["title"] == "甘肃 储能测算"
    assert item["version"] == "V1"
    assert item["province"] == "甘肃"
    assert item["powerMw"] == 200.0
    assert item["capacityMwh"] == 800.0
    assert item["projectIrr"] == 8.5
    assert item["report"] == {"status": "not_generated", "reportId": None}


@pytest.mark.asyncio
async def test_orders_versions_by_calculated_at_desc_and_paginates_by_ten(session):
    conversation = await _conversation(session, conversation_id="c-1", title="甘肃 储能测算")
    for index in range(1, 13):
        await _completed_task(
            session, conversation_id=conversation, version=f"V{index}",
            created_at=datetime(2026, 8, 1, 10, index), province="甘肃",
        )

    first = await CalculationLedgerService().list_records(session, user_id="1001")
    second = await CalculationLedgerService().list_records(session, user_id="1001", page=2)

    assert first["total"] == 12
    assert first["pageSize"] == 10
    assert len(first["items"]) == 10
    assert first["items"][0]["version"] == "V12"
    assert [item["version"] for item in second["items"]] == ["V2", "V1"]


@pytest.mark.asyncio
async def test_filters_by_title_keyword_provinces_and_inclusive_date_range(session):
    gansu = await _conversation(session, conversation_id="c-1", title="甘肃 储能测算")
    ningxia = await _conversation(session, conversation_id="c-2", title="宁夏 独立储能")
    in_range = await _completed_task(
        session, conversation_id=gansu, version="V1",
        created_at=datetime(2026, 8, 12, 23, 59, 59), province="甘肃",
    )
    await _completed_task(
        session, conversation_id=gansu, version="V2",
        created_at=datetime(2026, 8, 13, 0, 30), province="甘肃",
    )
    await _completed_task(
        session, conversation_id=ningxia, version="V1",
        created_at=datetime(2026, 8, 12, 10, 0), province="宁夏",
    )
    service = CalculationLedgerService()

    by_date = await service.list_records(
        session, user_id="1001",
        start_date=date(2026, 8, 12), end_date=date(2026, 8, 12),
    )
    by_province = await service.list_records(session, user_id="1001", provinces=["宁夏"])
    by_keyword = await service.list_records(session, user_id="1001", keyword="独立")

    assert {item["taskId"] for item in by_date["items"]} == {
        in_range, by_province["items"][0]["taskId"],
    }
    assert [item["province"] for item in by_province["items"]] == ["宁夏"]
    assert [item["title"] for item in by_keyword["items"]] == ["宁夏 独立储能"]


@pytest.mark.asyncio
async def test_report_status_prefers_generated_snapshot_over_generation_task(session):
    conversation = await _conversation(session, conversation_id="c-1", title="甘肃 储能测算")
    generated = await _completed_task(
        session, conversation_id=conversation, version="V1",
        created_at=datetime(2026, 8, 10, 9, 0), province="甘肃",
    )
    failed = await _completed_task(
        session, conversation_id=conversation, version="V2",
        created_at=datetime(2026, 8, 10, 10, 0), province="甘肃",
    )
    generating = await _completed_task(
        session, conversation_id=conversation, version="V3",
        created_at=datetime(2026, 8, 10, 11, 0), province="甘肃",
    )
    session.add_all([
        ReportGenerationTaskORM(
            task_id=generated, conversation_id=conversation, user_id="1001",
            status="completed", steps=[], report_id="rpt-1",
        ),
        ReportGenerationTaskORM(
            task_id=failed, conversation_id=conversation, user_id="1001",
            status="failed", steps=[],
        ),
        ReportGenerationTaskORM(
            task_id=generating, conversation_id=conversation, user_id="1001",
            status="generating", steps=[],
        ),
        ReportSnapshotORM(
            report_id="rpt-1", task_id=generated, conversation_id=conversation,
            user_id="1001", payload={"title": "甘肃报告"},
        ),
    ])
    await session.commit()

    data = await CalculationLedgerService().list_records(session, user_id="1001")
    by_task = {item["taskId"]: item["report"] for item in data["items"]}

    assert by_task[generated] == {"status": "completed", "reportId": "rpt-1"}
    assert by_task[failed]["status"] == "failed"
    assert by_task[generating]["status"] == "generating"


@pytest.mark.asyncio
async def test_province_options_only_include_provinces_the_user_calculated(session):
    mine = await _conversation(session, conversation_id="c-1", title="甘肃 储能测算")
    others = await _conversation(session, conversation_id="c-2", title="别人的项目", user_id="2002")
    await _completed_task(
        session, conversation_id=mine, version="V1",
        created_at=datetime(2026, 8, 10, 9, 0), province="甘肃",
    )
    await _completed_task(
        session, conversation_id=mine, version="V2",
        created_at=datetime(2026, 8, 10, 10, 0), province="宁夏",
    )
    await _completed_task(
        session, conversation_id=others, version="V1",
        created_at=datetime(2026, 8, 10, 11, 0), province="山西",
    )

    assert await CalculationLedgerService().list_provinces(session, user_id="1001") == ["宁夏", "甘肃"]
