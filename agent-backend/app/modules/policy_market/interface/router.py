"""政策与市场滚动资讯只读接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.policy_market.application.scrolling_message_service import ScrollingMessageService
from app.modules.policy_market.interface.serializers import serialize_messages, serialize_overview

router = APIRouter(prefix="/ir/policy-market", tags=["policy-market"])
_service = ScrollingMessageService()
_PERIODS = {"all", "month", "quarter"}


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
