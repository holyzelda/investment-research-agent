"""calculation 模块 · interface 路由（调试/联调用）。

阶段职责：暴露参数字典与"试组装"，供前端联调与业务核对数据契约。
真正的测算触发端点在 Batch3（执行引擎）落地。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.core.exceptions import NotFoundException
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.factory import (
    build_calculation_service,
    build_param_assembler,
    build_task_service,
)
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository
from app.modules.calculation.infrastructure.persistence.orm import ReportSnapshotORM
from app.modules.calculation.interface.serializers import serialize_result
from app.modules.platform_access.interface.deps import get_current_user
from app.modules.platform_access.domain.models import CurrentUser

router = APIRouter(prefix="/ir/calc", tags=["calculation"])


@router.get("/param-dict")
async def get_param_dict(display_only: bool = Query(False, description="仅返回 F=1 展示项")):
    """参数字典（数据契约）。display_only=true 仅返回页面展示项。"""
    d = JsonParamDictRepository().load()
    specs = d.displayable() if display_only else d.all()
    return ok({
        "total": len(specs),
        "parameters": [s.__dict__ for s in specs],
    })


class AssembleReq(BaseModel):
    province: str
    capacity_mwh: float
    power_mw: float
    node_name: Optional[str] = None
    voltage_kv: int = 220


@router.post("/assemble-preview")
async def assemble_preview(req: AssembleReq):
    """试组装：给最小项目信息，预览四来源组装出的 API_INPUT / 开关。"""
    asm = build_param_assembler()
    r = asm.assemble(ProjectBasics(
        province=req.province, capacity_mwh=req.capacity_mwh, power_mw=req.power_mw,
        node_name=req.node_name, voltage_kv=req.voltage_kv,
    ))
    return ok({
        "apiInput": r.api_input,
        "switches": r.switches,
        "warnings": r.warnings,
    })


@router.post("/run")
async def run_calculation(req: AssembleReq):
    """Mock 主链路测算：最小三项 → 组装 → 飞书写入/读取(Mock) → 结果三模块。

    薄片阶段飞书网关回放样例 output，不依赖真飞书；Batch3 换真网关+状态机+快照。
    """
    svc = build_calculation_service()
    result = await svc.run(ProjectBasics(
        province=req.province, capacity_mwh=req.capacity_mwh, power_mw=req.power_mw,
        node_name=req.node_name, voltage_kv=req.voltage_kv,
    ))
    return ok(serialize_result(result))


# ---- Batch3：测算任务（发起 / 状态 / 结果）----

class TaskCreateReq(BaseModel):
    province: str
    capacity_mwh: float
    power_mw: float
    node_name: Optional[str] = None
    voltage_kv: int = 220
    conversation_id: Optional[int] = None  # 空=新会话(V1)；给定=同会话追加(版本递增)


@router.post("/tasks")
async def create_task(
    req: TaskCreateReq,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """发起一次测算：组装→引擎(重试)→7类快照，返回 {taskId, version, conversationId, status}。"""
    svc = build_task_service()
    out = await svc.create_and_run(
        session,
        user_id=user.user_id,
        username=user.username,
        basics=ProjectBasics(
            province=req.province, capacity_mwh=req.capacity_mwh, power_mw=req.power_mw,
            node_name=req.node_name, voltage_kv=req.voltage_kv,
        ),
        conversation_id=req.conversation_id,
    )
    return ok(out)


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """任务状态流转（脱离飞书，纯读任务表）。"""
    task = await ConversationHistoryService().require_owned_task(
        session, task_id=task_id, user_id=user.user_id
    )
    data = {
        "taskId": task.id,
        "conversationId": task.conversation_id,
        "version": task.version,
        "status": task.status,
        "requestId": task.request_id,
    }
    if task.status == "failed":
        data["error"] = {"code": task.error_code, "message": task.error_message}
    return ok(data)


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """结果三模块（数据源 report_snapshot，不依赖飞书副本）。"""
    await ConversationHistoryService().require_owned_task(
        session, task_id=task_id, user_id=user.user_id
    )
    row = (await session.execute(
        select(ReportSnapshotORM).where(ReportSnapshotORM.task_id == task_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundException(f"该任务无结果快照（可能失败或不存在）：{task_id}")
    return ok(row.payload)
