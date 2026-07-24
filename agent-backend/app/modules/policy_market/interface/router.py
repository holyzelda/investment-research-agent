"""政策与市场滚动资讯只读接口。"""
from fastapi import APIRouter, Depends, Query
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
from app.modules.policy_market.infrastructure.policy_ask_executor import PolicyAskExecutorAdapter
from app.modules.policy_market.interface.serializers import (
    serialize_consultation_detail,
    serialize_consultation_summary,
    serialize_messages,
    serialize_overview,
)

router = APIRouter(prefix="/ir/policy-market", tags=["policy-market"])
_service = ScrollingMessageService()
_PERIODS = {"all", "month", "quarter"}


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
):
    question = payload.question.strip()
    if not question:
        raise ValidationException("请输入政策或市场问题")

    service = _consultation_service(session)
    try:
        record = await service.create(user_id=user.user_id, question=question)
    except ConsultationExecutionError as exc:
        await session.commit()
        raise ValidationException(str(exc)) from exc

    await session.commit()
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


@router.get("/messages")
async def list_scrolling_messages(
    province: str = Query("all"),
    period: str = Query("all"),
    topic: str = Query("all"),
    session: AsyncSession = Depends(get_db_session),
):
    if period not in _PERIODS:
        raise ValidationException("时间范围仅支持 all、month 或 quarter")
    messages = await _service.list_messages(
        session,
        province=province or "all",
        period=period,
        topic=topic or "all",
    )
    return ok(serialize_messages(messages))


@router.get("/messages/overview")
async def get_market_overview(
    province: str = Query("all"),
    period: str = Query("all"),
    topic: str = Query("all"),
    session: AsyncSession = Depends(get_db_session),
):
    if period not in _PERIODS:
        raise ValidationException("时间范围仅支持 all、month 或 quarter")
    overview = await _service.get_overview(
        session,
        province=province or "all",
        period=period,
        topic=topic or "all",
    )
    return ok(serialize_overview(overview))
