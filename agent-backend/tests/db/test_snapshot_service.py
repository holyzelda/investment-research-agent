"""连测试库 ir_agent · 7 类快照持久化关键链路（真实留痕）。

关键节点：
- 一次成功测算落齐 7 类快照，同会话二次测算不覆盖（V1/V2 并存）。
- 仅凭 report_snapshot 即可重建结果三模块（环形 6 类 + 折线 4 条×15 年 + 财务 5 项）。
"""
import uuid

import pytest
from sqlalchemy import func, select

from app.modules.calculation.application.factory import build_param_assembler
from app.modules.calculation.application.output_mapper import map_output_to_result
from app.modules.calculation.application.snapshot_service import SnapshotService
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.feishu_sample import SAMPLE_API_OUTPUT
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
)
from tests.db.conftest import PYTEST_TITLE_PREFIX, PYTEST_USERNAME


async def _persist(session, svc, conv_id, version, trigger=None):
    basics = ProjectBasics("甘肃", 800, 200, node_name="兰州东")
    assembled = build_param_assembler().assemble(basics)
    result = map_output_to_result(
        basics,
        assembled,
        SAMPLE_API_OUTPUT,
        version=version,
        request_id=f"req-{version}",
    )
    return await svc.persist_success(
        session,
        conversation_id=conv_id,
        version=version,
        request_id=f"req-{version}-{uuid.uuid4().hex[:6]}",
        param_hash="hash-demo",
        doc_token=f"mock-doc-{version}",
        assembled=assembled,
        api_output=SAMPLE_API_OUTPUT,
        api_meta={"status": "done", "request_id": f"req-{version}"},
        result=result,
        min_input={"province": "甘肃", "capacityMwh": 800, "powerMw": 200, "nodeName": "兰州东"},
        trigger=trigger,
        assistant_message=f"{version} 完成",
    )


@pytest.mark.asyncio
async def test_success_persists_seven_snapshots_without_overwrite(db_session, db_engine):
    svc = SnapshotService()
    conv_id = await svc.create_conversation(
        db_session, user_id="1001", username=PYTEST_USERNAME, title=f"{PYTEST_TITLE_PREFIX}7类快照"
    )
    task_v1 = await _persist(db_session, svc, conv_id, "V1")
    task_v2 = await _persist(db_session, svc, conv_id, "V2")

    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as s:
        # 不覆盖：同会话两个任务并存
        n_tasks = await s.scalar(
            select(func.count()).select_from(CalculationTaskORM)
            .where(CalculationTaskORM.conversation_id == conv_id)
        )
        assert n_tasks == 2

        # 每个任务各有 input/data/feishu_io/report 快照
        for tid in (task_v1, task_v2):
            for orm in (InputSnapshotORM, DataSnapshotORM, FeishuIoSnapshotORM, CalculationResultSnapshotORM):
                n = await s.scalar(select(func.count()).select_from(orm).where(orm.task_id == tid))
                assert n == 1, f"{orm.__name__} 缺失 for task {tid}"

        # 仅凭 calculation_result_snapshot 重建三模块
        calculation_result = (await s.execute(
            select(CalculationResultSnapshotORM).where(
                CalculationResultSnapshotORM.task_id == task_v2
            )
        )).scalar_one()
        p = calculation_result.payload
        assert p["basicInfo"]["province"] == "甘肃"
        assert set(p["financial"]) == {
            "projectIrr", "projectStaticPayback", "capitalIrr",
            "capitalStaticPayback", "averageProfit",
            "averageRevenue", "totalInvestmentRoi",
        }
        donut = p["advanced"]["donut"]
        assert donut["totalRevenue"] == SAMPLE_API_OUTPUT["first_year_total_revenue"]
        assert p["advanced"]["debtServiceCoverage"]["cashflowRatio"] == SAMPLE_API_OUTPUT[
            "cashflow_debt_service_coverage_ratio"
        ]


@pytest.mark.asyncio
async def test_success_persists_typed_calculation_completion_messages(db_session, db_engine):
    svc = SnapshotService()
    conv_id = await svc.create_conversation(
        db_session,
        user_id="1001",
        username=PYTEST_USERNAME,
        title=f"{PYTEST_TITLE_PREFIX}测算完成事件",
    )
    task_v1 = await _persist(db_session, svc, conv_id, "V1")
    task_v2 = await _persist(db_session, svc, conv_id, "V2")

    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        messages = (await session.execute(
            select(MessageSnapshotORM)
            .where(MessageSnapshotORM.conversation_id == conv_id)
            .order_by(MessageSnapshotORM.id.asc())
        )).scalars().all()

    # 普通测算不再写伪装用户原文：真实用户输入由聊天入口负责留痕
    user_messages = [message for message in messages if message.role == "user"]
    assistant_messages = [message for message in messages if message.role == "assistant"]
    assert user_messages == []
    assert [message.message_type for message in assistant_messages] == [
        "calculation_completed",
        "calculation_completed",
    ]
    assert [message.payload for message in assistant_messages] == [
        {
            "event_type": "calculation_completed",
            "task_id": task_v1,
            "version": "V1",
        },
        {
            "event_type": "calculation_completed",
            "task_id": task_v2,
            "version": "V2",
        },
    ]


@pytest.mark.asyncio
async def test_recalculate_trigger_writes_explicit_user_event(db_session, db_engine):
    svc = SnapshotService()
    conv_id = await svc.create_conversation(
        db_session,
        user_id="1001",
        username=PYTEST_USERNAME,
        title=f"{PYTEST_TITLE_PREFIX}重算事件",
    )
    task_v1 = await _persist(db_session, svc, conv_id, "V1", trigger="recalculate")

    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        messages = (await session.execute(
            select(MessageSnapshotORM)
            .where(MessageSnapshotORM.conversation_id == conv_id)
            .order_by(MessageSnapshotORM.id.asc())
        )).scalars().all()

    user_messages = [message for message in messages if message.role == "user"]
    assert len(user_messages) == 1
    assert user_messages[0].message_type == "text"
    assert user_messages[0].payload == {"event_type": "recalculate"}
    assert "重新测算" in user_messages[0].content

    completion = [message for message in messages if message.role == "assistant"][0]
    assert completion.message_type == "calculation_completed"
    assert completion.payload == {
        "event_type": "calculation_completed",
        "task_id": task_v1,
        "version": "V1",
    }
