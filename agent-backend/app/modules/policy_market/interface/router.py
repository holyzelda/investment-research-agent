"""政策与市场滚动资讯只读接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.policy_market.application.scrolling_message_service import ScrollingMessageService
from app.modules.policy_market.interface.serializers import serialize_messages

router = APIRouter(prefix="/ir/policy-market", tags=["policy-market"])
_service = ScrollingMessageService()


@router.get("/messages")
async def list_scrolling_messages(session: AsyncSession = Depends(get_db_session)):
    messages = await _service.list_messages(session)
    return ok(serialize_messages(messages))
