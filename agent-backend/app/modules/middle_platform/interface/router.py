"""本应用的中台对话 SSE 代理接口。"""
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.infrastructure.database.session import get_db_session
from app.modules.middle_platform.application.chat_proxy_service import ChatProxyService
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter(prefix="/ir/chat", tags=["middle-platform-chat"])


class ChatDiagRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = Field(default=None, gt=0)


@router.post("/diag")
async def chat_diag(
    req: ChatDiagRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    stream = await ChatProxyService(get_settings().middle_platform).start_chat(
        session=session,
        user=user,
        message=req.message,
        conversation_id=req.conversation_id,
    )
    return StreamingResponse(
        stream.chunks,
        media_type="text/event-stream",
        headers={"X-IR-Conversation-Id": str(stream.conversation_id)},
    )
