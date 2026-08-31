"""calculation 模块 · interface 路由（调试/联调用）。

阶段职责：暴露参数字典与"试组装"，供前端联调与业务核对数据契约。
真正的测算触发端点在 Batch3（执行引擎）落地。
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.core.exceptions import NotFoundException, ValidationException
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.factory import (
    build_param_assembler,
    build_revenue_structure_reader,
    build_task_service,
)
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.calculation.application.input_normalizer import (
    complete_scale_anchors,
    normalize_project_basics,
)
from app.modules.calculation.application.platform_stats_service import get_platform_stats as load_platform_stats
from app.modules.calculation.application.param_assembler import _SWITCH_MAP as _SWITCH_ATTR_MAP
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository
from app.modules.calculation.infrastructure.henan_spot_import import CITY_TO_REGION, city_to_region
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    InputSnapshotORM,
    SpotStationORM,
)
from app.modules.platform_access.interface.deps import get_current_user
from app.modules.platform_access.domain.models import CurrentUser

router = APIRouter(prefix="/ir/calc", tags=["calculation"])

@router.get("/stats")
async def get_platform_stats(
    session: AsyncSession = Depends(get_db_session),
):
    """返回首页平台累计指标（固定基线 + 数据库真实使用量）。"""
    return ok(await load_platform_stats(session))


@router.get("/param-dict")
async def get_param_dict(
    display_only: bool = Query(False, description="仅返回 F=1 展示项"),
    province: Optional[str] = Query(None, description="按省返回表2市场开关，供收益类统一显隐"),
):
    """参数字典（数据契约）。display_only=true 仅返回页面展示项；province= 附带该省表2开关。"""
    d = JsonParamDictRepository().load()
    specs = d.displayable() if display_only else d.all()
    parameters = [dict(s.__dict__) for s in specs]
    data = {
        "total": len(specs),
        "parameters": parameters,
    }
    if province:
        profile = build_revenue_structure_reader().get_profile(province)
        if profile is not None:
            data["switches"] = {
                pid: getattr(profile, attr) for pid, attr in _SWITCH_ATTR_MAP.items()
            }
        # 河南按地级市定位项目，城市候选取自现货区域映射这一权威来源。
        if _is_henan(province):
            for spec in parameters:
                if spec["id"] == "city":
                    spec["control"] = "select"
                    spec["options"] = [
                        {"value": city, "label": city} for city in CITY_TO_REGION
                    ]
    return ok(data)


@router.get("/stations")
async def list_stations(
    province: str = Query(..., min_length=1, description="项目省份，精确匹配 ir_spot_station.province"),
    keyword: Optional[str] = Query(default=None, max_length=128, description="节点名称关键字"),
    cursor: Optional[str] = Query(default=None, max_length=128, description="上一批最后一个节点名称"),
    limit: int = Query(default=30, ge=1, le=100, description="每批返回数量"),
    session: AsyncSession = Depends(get_db_session),
):
    """按项目省份搜索节点；滚动到底时用 nextCursor 继续加载后一批。"""
    statement = select(SpotStationORM.station_name).where(
        SpotStationORM.province == province
    )
    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        escaped_keyword = (
            normalized_keyword
            .replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_")
        )
        statement = statement.where(
            SpotStationORM.station_name.like(f"%{escaped_keyword}%", escape="!")
        )
    if cursor:
        statement = statement.where(SpotStationORM.station_name > cursor)

    rows = (await session.execute(
        statement.order_by(SpotStationORM.station_name.asc()).limit(limit + 1)
    )).scalars().all()
    items = list(rows[:limit])
    has_more = len(rows) > limit
    return ok({
        "items": items,
        "hasMore": has_more,
        "nextCursor": items[-1] if has_more else None,
    })


def _is_henan(province: object) -> bool:
    """河南省份判定：容忍前后空白与“省”后缀，统一走城市区域路由。"""
    return str(province or "").strip().removesuffix("省") == "河南"


def _validate_henan_input(*, province: str, city: Optional[str], node_name: Optional[str]) -> None:
    """河南现货按地级市区域计算，禁止节点路由并要求可识别城市。"""
    if not _is_henan(province):
        return
    if node_name:
        raise ValidationException("河南项目不支持节点名称，请填写城市")
    if not city:
        raise ValidationException("河南项目必须填写城市")
    if city_to_region(city) is None:
        raise ValidationException("河南城市无法识别，请填写河南地级市")


class AssembleReq(BaseModel):
    province: str
    capacity_mwh: float = Field(gt=0)
    power_mw: float = Field(gt=0)
    node_name: Optional[str] = None
    voltage_kv: int = 220
    city: Optional[str] = None


@router.post("/assemble-preview")
async def assemble_preview(req: AssembleReq):
    """试组装：给最小项目信息，预览四来源组装出的 API_INPUT / 开关。"""
    city = req.city.strip() if req.city and req.city.strip() else None
    _validate_henan_input(province=req.province, city=city, node_name=req.node_name)
    asm = build_param_assembler()
    r = asm.assemble(ProjectBasics(
        province=req.province, capacity_mwh=req.capacity_mwh, power_mw=req.power_mw,
        node_name=req.node_name, voltage_kv=req.voltage_kv, city=city,
    ))
    return ok({
        "apiInput": r.api_input,
        "switches": r.switches,
        "warnings": r.warnings,
    })


# ---- Batch3：测算任务（发起 / 状态 / 结果）----

class TaskCreateReq(BaseModel):
    province: str
    capacity_mwh: Optional[float] = Field(default=None, gt=0)
    power_mw: Optional[float] = Field(default=None, gt=0)
    duration_hours: Optional[float] = Field(default=None, gt=0)
    node_name: Optional[str] = None
    voltage_kv: int = 220
    city: Optional[str] = None
    param_overrides: Optional[dict] = None  # Batch5：调整面板提交的受控参数覆盖（仅 g=1 可写输入生效）
    trigger: Optional[str] = None  # 直接重算传 "recalculate"，历史据此写明确重算事件而非伪装用户原文

@router.post("/tasks")
async def create_task(
    req: TaskCreateReq,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    conversation_id: Optional[str] = Header(default=None, alias="X-IR-Conversation-Id"),
):
    """发起一次测算：组装→引擎(重试)→7类快照，返回 {taskId, version, conversationId, status}。"""
    try:
        conv_id = str(UUID(conversation_id)) if conversation_id is not None else None
    except ValueError as exc:
        raise ValidationException("conversation_id 格式无效") from exc
    svc = build_task_service()
    # 非本人/已删除/未知会话按归属边界直接 404（与 latest-input 等只读端点一致）。
    if conv_id is not None:
        await ConversationHistoryService().require_active_conversation(
            session, conversation_id=conv_id, user_id=user.user_id
        )
    # 同会话修改参数：以最近一次成功版本的冻结入参为基线，补全缺失的规模锚点。
    # 例如用户只改功率，则容量沿用上一版（改功率=改时长，容量不变），避免 normalize 因
    # 缺少容量/时长组合而 400；首次测算（无会话或无成功版本）previous_input 为 None 不补全。
    previous_input = await _latest_frozen_input(session, conv_id) if conv_id is not None else None
    cap, pwr, dur = complete_scale_anchors(
        previous_input=previous_input,
        capacity_mwh=req.capacity_mwh,
        power_mw=req.power_mw,
        duration_hours=req.duration_hours,
    )
    city = req.city.strip() if req.city and req.city.strip() else None
    if city is None and previous_input is not None:
        # 同会话调整参数未重复提交城市时，沿用冻结快照中的应用侧城市元数据。
        city = previous_input.get("city")
    _validate_henan_input(province=req.province, city=city, node_name=req.node_name)
    inherited_node = (
        previous_input is not None
        and previous_input.get("node_name") == req.node_name
    )
    if req.node_name and not inherited_node:
        station = (await session.execute(
            select(SpotStationORM.station_name).where(
                SpotStationORM.province == req.province,
                SpotStationORM.station_name == req.node_name,
            )
        )).scalar_one_or_none()
        if station is None:
            raise ValidationException(f"节点“{req.node_name}”不属于省份“{req.province}”")
    out = await svc.create_and_run(
        session,
        user_id=user.user_id,
        username=user.username,
        basics=normalize_project_basics(
            province=req.province,
            capacity_mwh=cap,
            power_mw=pwr,
            duration_hours=dur,
            node_name=req.node_name,
            voltage_kv=req.voltage_kv,
            city=city,
        ),
        conversation_id=conv_id,
        param_overrides=req.param_overrides,
        trigger=req.trigger,
    )
    return ok(out)


async def _latest_frozen_input(
    session: AsyncSession, conv_id: str
) -> Optional[dict]:
    """最近一次成功测算版本的冻结 api_input（无成功版本或无快照时返回 None）。"""
    latest_task = (await session.execute(
        select(CalculationTaskORM)
        .where(
            CalculationTaskORM.conversation_id == conv_id,
            CalculationTaskORM.status == "completed",
        )
        .order_by(CalculationTaskORM.created_at.desc(), CalculationTaskORM.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if latest_task is None:
        return None
    snapshot = (await session.execute(
        select(InputSnapshotORM).where(InputSnapshotORM.task_id == latest_task.id)
    )).scalar_one_or_none()
    if snapshot is None or not snapshot.payload:
        return None
    return snapshot.payload.get("apiInput")


@router.get("/tasks/latest-input")
async def get_latest_task_input(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    conversation_id: Optional[str] = Header(default=None, alias="X-IR-Conversation-Id"),
):
    """最近一次成功测算的冻结入参（含省份/规模/节点/电压及全部 g=1 参数）。

    供智能体中台"对话修改参数并重新测算"场景取基线：中台按同一会话再次调用
    create_calculation_task 前，先经本接口读取最近一次成功版本的冻结 api_input，
    作为未改动参数的种子；无会话或无成功版本时返回 404，中台据此如实告知。
    只读快照（InputSnapshotORM），不触发飞书、不生成新任务。
    """
    try:
        conv_id = str(UUID(conversation_id)) if conversation_id is not None else None
    except ValueError as exc:
        raise ValidationException("conversation_id 格式无效") from exc
    if conv_id is None:
        raise NotFoundException("会话不存在")
    await ConversationHistoryService().require_active_conversation(
        session, conversation_id=conv_id, user_id=user.user_id
    )
    frozen = await _latest_frozen_input(session, conv_id)
    if frozen is None:
        raise NotFoundException("该会话暂无成功测算版本")
    latest_task = (await session.execute(
        select(CalculationTaskORM)
        .where(
            CalculationTaskORM.conversation_id == conv_id,
            CalculationTaskORM.status == "completed",
        )
        .order_by(CalculationTaskORM.created_at.desc(), CalculationTaskORM.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    return ok({
        "taskId": latest_task.id,
        "version": latest_task.version,
        "input": frozen,
    })


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
        data["error"] = {
            "code": task.error_code,
            "message": task.error_message,
            "requestId": task.request_id,
            "retryCount": task.retry_count,
        }
    return ok(data)


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """结果三模块（数据源 report_snapshot，不依赖飞书副本）。"""
    task = await ConversationHistoryService().require_owned_task(
        session, task_id=task_id, user_id=user.user_id
    )
    row = (await session.execute(
        select(CalculationResultSnapshotORM).where(CalculationResultSnapshotORM.task_id == task_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundException(f"该任务无结果快照（可能失败或不存在）：{task_id}")
    # 测算时间取任务落库时间（成功任务在测算完成后落库），供前端结果卡展示
    return ok({**row.payload, "calculatedAt": task.created_at.isoformat()})
