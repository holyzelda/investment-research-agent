"""政策与市场滚动资讯只读接口。"""
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user
from app.modules.policy_market.application.consultation_service import (
    ConsultationExecutionError,
    ConsultationService,
)
from app.modules.policy_market.application.scrolling_message_service import ScrollingMessageService
from app.modules.policy_market.infrastructure.persistence.consultation_repository import (
    SqlAlchemyConsultationRepository,
)
from app.modules.policy_market.infrastructure.policy_ask_executor import (
    PolicyAskExecutorAdapter,
    PolicySourceFileAdapter,
)
from app.modules.policy_market.interface.serializers import (
    serialize_consultation_detail,
    serialize_consultation_summary,
    serialize_messages,
    serialize_overview,
)
from app.modules.trial_quota.application.trial_quota_service import TrialQuotaService
from app.modules.trial_quota.application.trial_role_service import TrialRoleService
from app.modules.trial_quota.interface.deps import (
    get_trial_quota_service,
    get_trial_role_service,
)

router = APIRouter(prefix="/ir/policy-market", tags=["policy-market"])
_service = ScrollingMessageService()
# 浏览器能直接渲染的类型内联展示，其余一律下载——docx/xlsx 内联只会得到一堆乱码。
_INLINE_TYPES = {"application/pdf", "text/plain"}


class ConsultationCreateRequest(BaseModel):
    question: str


def _consultation_service(session: AsyncSession) -> ConsultationService:
    return ConsultationService(
        repository=SqlAlchemyConsultationRepository(session),
        executor=PolicyAskExecutorAdapter(),
    )


@router.post("/consultations")
async def create_consultation(
    payload: ConsultationCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    trial_role: TrialRoleService = Depends(get_trial_role_service),
    trial_quota: TrialQuotaService = Depends(get_trial_quota_service),
):
    question = payload.question.strip()
    if not question:
        raise ValidationException("请输入政策或市场问题")

    reservation = None
    if await trial_role.is_trial(user.user_id):
        reservation = await trial_quota.reserve(session, user.user_id, "consultation")
    service = _consultation_service(session)
    try:
        record = await service.create(user_id=user.user_id, question=question)
    except ConsultationExecutionError as exc:
        await session.commit()
        if reservation is not None:
            await trial_quota.refund(session, reservation)
        raise ValidationException(str(exc)) from exc
    except Exception:
        await session.rollback()
        if reservation is not None:
            await trial_quota.refund(session, reservation)
        raise

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        if reservation is not None:
            await trial_quota.refund(session, reservation)
        raise
    return ok(serialize_consultation_detail(record))


@router.get("/consultations")
async def list_consultations(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    records = await _consultation_service(session).list_for_user(user_id=user.user_id)
    return ok([serialize_consultation_summary(record) for record in records])


@router.get("/consultations/{record_id}")
async def get_consultation(
    record_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    record = await _consultation_service(session).get_for_user(
        record_id=record_id,
        user_id=user.user_id,
    )
    if record is None:
        raise NotFoundException("咨询记录不存在")
    return ok(serialize_consultation_detail(record))


@router.delete("/consultations/{record_id}")
async def delete_consultation(
    record_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    deleted = await _consultation_service(session).delete_for_user(
        record_id=record_id,
        user_id=user.user_id,
    )
    if not deleted:
        raise NotFoundException("咨询记录不存在")
    await session.commit()
    return ok({"id": record_id, "deleted": True})


def _content_disposition(filename: str, inline: bool) -> str:
    """RFC 5987 双写：ASCII 兜底名给老浏览器，filename* 保住中文原名。

    HTTP 响应头必须是 ASCII，中文文件名直接塞进 filename= 会被网关或浏览器截断。
    """
    disposition = "inline" if inline else "attachment"
    safe = quote(filename or "source-file", safe="")
    return f"{disposition}; filename=\"source-file\"; filename*=UTF-8''{safe}"


@router.get("/source-files/{token}")
async def download_source_file(
    token: str,
    user: CurrentUser = Depends(get_current_user),
):
    """代理下载知识库源文件——飞书链接只有公司内部账号能打开，外部用户走这里。

    与其他端点不同，成功时返回的是文件字节流而非 {code,msg,data} 响应壳；
    失败仍走统一异常处理，是标准 JSON 壳。前端按 blob 的 type 区分两者。

    token 白名单在 tools 层校验：不在省页解析出的源文件集合内一律 404，
    否则本端点等于把公司飞书云盘代理给了所有平台用户。
    """
    source = await PolicySourceFileAdapter().fetch(token)
    if source is None:
        raise NotFoundException("源文件不存在或不可下载")

    return Response(
        content=source.content,
        media_type=source.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(
                source.filename,
                inline=source.content_type in _INLINE_TYPES
                or source.content_type.startswith("image/"),
            ),
        },
    )


@router.get("/messages")
async def list_scrolling_messages(
    province: str = Query("all"),
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    topic: str = Query("all"),
    session: AsyncSession = Depends(get_db_session),
):
    _validate_date_range(start_date, end_date)
    messages = await _service.list_messages(
        session,
        province=province or "all",
        start_date=start_date,
        end_date=end_date,
        topic=topic or "all",
    )
    return ok(serialize_messages(messages))


@router.get("/messages/overview")
async def get_market_overview(
    province: str = Query("all"),
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    topic: str = Query("all"),
    session: AsyncSession = Depends(get_db_session),
):
    _validate_date_range(start_date, end_date)
    overview = await _service.get_overview(
        session,
        province=province or "all",
        start_date=start_date,
        end_date=end_date,
        topic=topic or "all",
    )
    return ok(serialize_overview(overview))


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if (start_date is None) != (end_date is None):
        raise ValidationException("开始日期和结束日期必须同时提供")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValidationException("开始日期不能晚于结束日期")
