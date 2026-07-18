"""连测试库 ir_agent · 7 类快照持久化关键链路（真实留痕）。

关键节点：
- 一次成功测算落齐 7 类快照，同会话二次测算不覆盖（V1/V2 并存）。
- 仅凭 report_snapshot 即可重建结果三模块（环形 6 类 + 折线 4 条×15 年 + 财务 5 项）。
"""
import uuid

import pytest
from sqlalchemy import func, select

from app.modules.calculation.application.factory import (
    build_calculation_service,
    build_param_assembler,
)
from app.modules.calculation.application.snapshot_service import SnapshotService
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.feishu_sample import SAMPLE_API_OUTPUT
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportSnapshotORM,
)
from tests.db.conftest import PYTEST_TITLE_PREFIX, PYTEST_USERNAME


async def _persist(session, svc, conv_id, version):
    basics = ProjectBasics("甘肃", 800, 200, node_name="兰州东")
    assembled = build_param_assembler().assemble(basics)
    result = await build_calculation_service().run(basics, version=version, request_id=f"req-{version}")
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
        user_message=f"测算甘肃 200MW/800MWh（{version}）",
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
            for orm in (InputSnapshotORM, DataSnapshotORM, FeishuIoSnapshotORM, ReportSnapshotORM):
                n = await s.scalar(select(func.count()).select_from(orm).where(orm.task_id == tid))
                assert n == 1, f"{orm.__name__} 缺失 for task {tid}"

        # message_snapshot：会话下至少 user+assistant × 2 次测算 = 4
        n_msg = await s.scalar(
            select(func.count()).select_from(MessageSnapshotORM)
            .where(MessageSnapshotORM.conversation_id == conv_id)
        )
        assert n_msg == 4

        # 仅凭 report_snapshot 重建三模块
        report = (await s.execute(
            select(ReportSnapshotORM).where(ReportSnapshotORM.task_id == task_v2)
        )).scalar_one()
        p = report.payload
        assert p["basicInfo"]["province"] == "甘肃"
        assert set(p["financial"]) == {
            "projectIrr", "projectStaticPayback", "capitalIrr",
            "capitalStaticPayback", "averageProfit",
        }
        donut = p["advanced"]["donut"]
        assert donut["totalRevenue"] == SAMPLE_API_OUTPUT["first_year_total_revenue"]
        assert p["advanced"]["debtServiceCoverage"]["cashflowRatio"] == SAMPLE_API_OUTPUT[
            "cashflow_debt_service_coverage_ratio"
        ]
