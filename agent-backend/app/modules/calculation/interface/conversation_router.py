"""Conversation history HTTP endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter(prefix="/ir/conversations", tags=["conversation-history"])
_service = ConversationHistoryService()


@router.get("")
async def list_conversations(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return ok({"items": await _service.list_active(session, user_id=user.user_id)})


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return ok(await _service.get_detail(
        session,
        conversation_id=conversation_id,
        user_id=user.user_id,
    ))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return ok(await _service.soft_delete(
        session,
        conversation_id=conversation_id,
        user_id=user.user_id,
    ))
