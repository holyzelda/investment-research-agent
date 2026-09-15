"""calculation 模块 · interface 路由（调试/联调用）。

阶段职责：暴露参数字典与"试组装"，供前端联调与业务核对数据契约。
真正的测算触发端点在 Batch3（执行引擎）落地。
"""
import asyncio
import json
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.factory import (
    build_param_assembler,
    build_revenue_structure_reader,
    build_task_service,
)
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.calculation.application.error_presenter import (
    public_calc_error_code,
    public_calc_error_message,
)
from app.modules.calculation.application.input_normalizer import (
    complete_scale_anchors,
    normalize_project_basics,
)
from app.modules.calculation.application.platform_stats_service import get_platform_stats as load_platform_stats
from app.modules.calculation.application.param_assembler import _SWITCH_MAP as _SWITCH_ATTR_MAP
from app.modules.calculation.application.spot_context_service import SpotContextService
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository
from app.modules.calculation.infrastructure.henan_spot_import import CITY_TO_REGION, city_to_region
from app.modules.calculation.infrastructure.conversation_spot_price_algo import (
    ConversationSpotPriceAlgo,
)
from app.modules.calculation.infrastructure.uploaded_spot_context import (
    EXPECTED_HEADERS,
    MAX_UPLOAD_BYTES,
    parse_uploaded_spot_file,
)
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    InputSnapshotORM,
    SpotStationORM,
)
from app.modules.platform_access.interface.deps import get_current_user, get_user_scope
from app.modules.platform_access.domain.models import CurrentUser, UserScope

router = APIRouter(prefix="/ir/calc", tags=["calculation"])
_SPOT_UPLOAD_SEMAPHORE = asyncio.Semaphore(2)


def _conversation_uuid(value: Optional[str]) -> Optional[str]:
    try:
        return str(UUID(value)) if value is not None else None
    except ValueError as exc:
        raise ValidationException("conversation_id 格式无效") from exc


def _xlsx_template() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "现货电价"
    sheet.append(list(EXPECTED_HEADERS))
    for index in range(1, 97):
        minutes = index * 15
        label = f"{minutes // 60:02d}:{minutes % 60:02d}"
        sheet.append(["", label, ""])
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet["A1"].comment = Comment("填写自然日日期，例如 2025-01-01。", "朱雀投研")
    sheet["B1"].comment = Comment(
        "每个自然日必须包含 00:15 至 24:00 的 96 个时点，每 15 分钟一个时点。",
        "朱雀投研",
    )
    sheet["C1"].comment = Comment("填写数值，单位固定为元/MWh。", "朱雀投研")
    for row in range(2, 98):
        sheet.cell(row=row, column=1).number_format = "yyyy-mm-dd"
        sheet.cell(row=row, column=3).number_format = "0.00"
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["A"].width = 16
    sheet.column_dimensions["B"].width = 12
    sheet.column_dimensions["C"].width = 20

    instructions = workbook.create_sheet("填写说明")
    instruction_rows = [
        ("现货电价文件填写说明", ""),
        ("核心要求", "表头必须为：日期、时点（00:15 至 24:00）、电价（元/MWh）"),
        ("文件格式", "仅支持 .xlsx 文件，文件大小不超过 20MB。"),
        ("数据范围", "一份文件只填写一条电价序列，日期跨度不能超过 366 天。"),
        ("每日数据", "每个自然日填写 96 条数据，时点每 15 分钟一个，从 00:15 到 24:00。"),
        ("有效日期", "时点完整、不重复且电价均为有效数值的自然日才会参与测算。"),
        ("异常日期", "不完整、时点重复或价格无效的自然日会被跳过；文件至少包含一个有效自然日。"),
        ("填写方式", "在“现货电价”工作表填写；多日数据按日期逐日追加，请勿修改表头或新增数据列。"),
        ("单位", "电价统一填写元/MWh，请勿填写元/kWh。"),
        ("示例", "2025-01-01 | 00:15 | 231.50"),
    ]
    for row in instruction_rows:
        instructions.append(row)
    instructions.merge_cells("A1:B1")
    instructions["A1"].font = Font(size=16, bold=True, color="1F4E78")
    instructions["A1"].alignment = Alignment(vertical="center")
    instructions.row_dimensions[1].height = 28
    for row in range(2, len(instruction_rows) + 1):
        instructions.cell(row=row, column=1).font = Font(bold=True, color="1F4E78")
        instructions.cell(row=row, column=1).alignment = Alignment(vertical="top")
        instructions.cell(row=row, column=2).alignment = Alignment(vertical="top", wrap_text=True)
        instructions.row_dimensions[row].height = 34
    instructions.column_dimensions["A"].width = 14
    instructions.column_dimensions["B"].width = 78
    instructions.freeze_panes = "A2"
    instructions.sheet_view.showGridLines = False
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@router.get("/spot-context/template")
async def download_spot_context_template():
    """下载单日 96 点长表模板，供用户按固定格式填充。"""
    return StreamingResponse(
        BytesIO(_xlsx_template()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=spot-price-template.xlsx",
        },
    )


@router.post("/spot-context/prepare")
async def prepare_spot_context(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(default=None),
    price_mode: str = Form(default="both"),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """上传后流式返回校验和保存阶段；实际联合 DP 延迟到测算时执行。"""
    conv_id = _conversation_uuid(conversation_id)
    # StreamingResponse starts iterating after this route returns. Read the
    # upload while FastAPI still owns its temporary file; otherwise request
    # cleanup can close UploadFile before event_stream reaches file.read().
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    file_name = file.filename or ""

    async def event_stream():
        def encode(event: dict) -> str:
            return json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

        yield encode({"phase": "uploading", "message": "文件已接收，正在准备处理"})
        from app.core.config.settings import get_settings

        spot = get_settings().spot_price
        progress_queue: asyncio.Queue[dict | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def report_progress(event: dict):
            loop.call_soon_threadsafe(progress_queue.put_nowait, event)

        def parse_in_worker():
            try:
                return parse_uploaded_spot_file(
                    content,
                    file_name,
                    min_action_minutes=spot.min_action_minutes,
                    switch_gap_minutes=spot.switch_gap_minutes,
                    workers=spot.daily_update_workers,
                    price_mode=price_mode,
                    progress_callback=report_progress,
                )
            finally:
                # Keep the sentinel behind every progress callback scheduled
                # by this worker so the stream cannot skip the final day.
                loop.call_soon_threadsafe(progress_queue.put_nowait, None)

        async def run_parse():
            return await asyncio.to_thread(parse_in_worker)

        async with _SPOT_UPLOAD_SEMAPHORE:
            parse_task = asyncio.create_task(run_parse())
            while (event := await progress_queue.get()) is not None:
                yield encode(event)
            try:
                parsed = await parse_task
            except ValidationException as exc:
                yield encode({"phase": "error", "message": str(exc)})
                return
            except Exception as exc:
                logger.opt(exception=exc).error("上传电价文件解析失败")
                yield encode({"phase": "error", "message": "电价文件处理失败，请稍后重试"})
                return

        yield encode({"phase": "saving", "message": "正在准备本会话电价"})
        try:
            token, context = await SpotContextService().save_prepared(
                session,
                user_id=user.user_id,
                conversation_id=conv_id,
                parsed=parsed,
            )
        except BusinessException as exc:
            yield encode({"phase": "error", "message": str(exc)})
            return
        except Exception as exc:
            logger.opt(exception=exc).error("保存会话电价上下文失败")
            yield encode({"phase": "error", "message": "电价文件保存失败，请稍后重试"})
            return
        yield encode({
            "phase": "ready",
            "message": "电价文件已准备完成",
            "data": {**SpotContextService.summary(context), "contextToken": token},
        })

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/spot-context")
async def get_spot_context(
    conversation_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    conv_id = _conversation_uuid(conversation_id)
    await ConversationHistoryService().require_active_conversation(
        session, conversation_id=conv_id, user_id=user.user_id
    )
    context = await SpotContextService().get_for_conversation(
        session, conversation_id=conv_id, user_id=user.user_id
    )
    return ok(SpotContextService.summary(context) if context else None)


@router.delete("/spot-context")
async def delete_spot_context(
    conversation_id: Optional[str] = Query(default=None),
    context_token: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    if conversation_id:
        await SpotContextService().remove(
            session,
            conversation_id=_conversation_uuid(conversation_id),
            user_id=user.user_id,
        )
    elif context_token:
        await SpotContextService().remove_staged(
            session, token=context_token, user_id=user.user_id
        )
    else:
        raise ValidationException("请提供会话或上传凭证")
    return ok({"deleted": True})

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
    basics = normalize_project_basics(
        province=req.province,
        capacity_mwh=req.capacity_mwh,
        power_mw=req.power_mw,
        duration_hours=None,
        node_name=req.node_name,
        voltage_kv=req.voltage_kv,
        city=city,
    )
    r = asm.assemble(basics)
    return ok({
        "apiInput": r.api_input,
        "switches": r.switches,
        "warnings": r.warnings,
    })


# ---- Batch3：测算任务（发起 / 状态 / 结果）----

class TaskInputsReq(BaseModel):
    taskIds: list[StrictInt] = Field(min_length=1, max_length=50)


@router.post("/tasks/inputs")
async def get_task_inputs(
    req: TaskInputsReq,
    user: CurrentUser = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
):
    """批量读取成功版本冻结入参；不可用任务不泄露资源信息。"""
    if any(task_id <= 0 for task_id in req.taskIds):
        raise ValidationException("taskIds 必须为正整数")
    return ok({"items": await ConversationHistoryService().get_task_inputs(
        session,
        task_ids=req.taskIds,
        user_id=user.user_id,
        readable_user_ids=scope.user_ids,
    )})


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
    conv_id = _conversation_uuid(conversation_id)
    # 非本人/已删除/未知会话按归属边界直接 404（与 latest-input 等只读端点一致）。
    if conv_id is not None:
        await ConversationHistoryService().require_active_conversation(
            session, conversation_id=conv_id, user_id=user.user_id
        )
    spot = None
    if conv_id is not None:
        context = await SpotContextService().get_for_conversation(
            session, conversation_id=conv_id, user_id=user.user_id
        )
        if context is not None:
            from app.core.config.settings import get_settings

            spot_settings = get_settings().spot_price
            spot = ConversationSpotPriceAlgo(
                context,
                spot_settings.province_price_coefficients,
                min_action_minutes=spot_settings.min_action_minutes,
                switch_gap_minutes=spot_settings.switch_gap_minutes,
                workers=spot_settings.daily_update_workers,
            )
    # 同会话修改参数：以最近一次成功版本的冻结入参为基线，补全缺失的规模锚点。
    # 例如用户只改功率，则容量沿用上一版（改功率=改时长，容量不变），避免 normalize 因
    # 缺少容量/时长组合而 400；首次测算（无会话或无成功版本）previous_input 为 None 不补全。
    previous_input = await _latest_frozen_input(session, conv_id) if conv_id is not None else None
    if spot is not None:
        svc = build_task_service(spot=spot)
    else:
        svc = build_task_service()
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
            "code": public_calc_error_code(task.error_code, task.error_message),
            "message": public_calc_error_message(task.error_message, task.error_code),
            "requestId": task.request_id,
            "retryCount": task.retry_count,
        }
    return ok(data)


@router.get("/tasks/{task_id}/input")
async def get_task_input(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
):
    """读取指定成功版本的冻结入参（纯快照，不访问飞书）。"""
    return ok(await ConversationHistoryService().get_task_input(
        session,
        task_id=task_id,
        user_id=user.user_id,
        readable_user_ids=scope.user_ids,
    ))


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
):
    """结果三模块（数据源 report_snapshot，不依赖飞书副本）。"""
    task = await ConversationHistoryService().require_owned_task(
        session,
        task_id=task_id,
        user_id=user.user_id,
        readable_user_ids=scope.user_ids,
    )
    row = (await session.execute(
        select(CalculationResultSnapshotORM).where(CalculationResultSnapshotORM.task_id == task_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundException(f"该任务无结果快照（可能失败或不存在）：{task_id}")
    # 测算时间取任务落库时间（成功任务在测算完成后落库），供前端结果卡展示
    return ok({**row.payload, "calculatedAt": task.created_at.isoformat()})
