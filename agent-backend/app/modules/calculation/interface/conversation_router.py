"""Conversation history HTTP endpoints."""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.conversation_history_service import (
    ConversationHistoryService,
)
from app.modules.calculation.application.factory import build_feishu_gateway
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter(prefix="/ir/conversations", tags=["conversation-history"])
_service = ConversationHistoryService()


async def _delete_feishu_copies(conversation_id: str, doc_tokens: list[str]) -> None:
    """响应发送后尽力清理飞书副本，不影响会话软删除结果。"""
    gateway = None
    try:
        logger.info(
            "开始后台清理会话飞书副本 conversation_id={} count={}",
            conversation_id, len(doc_tokens),
        )
        gateway = build_feishu_gateway()
        logger.info(
            "飞书清理网关已创建 conversation_id={} gateway={}",
            conversation_id, type(gateway).__name__,
        )
        for doc_token in doc_tokens:
            try:
                logger.info(
                    "发起删除飞书副本 conversation_id={} doc_token={}",
                    conversation_id, doc_token,
                )
                await gateway.delete_file(doc_token)
                logger.info(
                    "删除飞书副本成功 conversation_id={} doc_token={}",
                    conversation_id, doc_token,
                )
            except Exception as exc:
                logger.warning(
                    "删除会话关联飞书副本失败 conversation_id={} doc_token={} error={}",
                    conversation_id, doc_token, exc,
                )
    except Exception as exc:
        logger.warning(
            "初始化飞书清理任务失败 conversation_id={} error={}", conversation_id, exc
        )
    finally:
        if gateway is not None:
            try:
                await gateway.close()
            except Exception as exc:
                logger.warning(
                    "关闭飞书网关失败 conversation_id={} error={}", conversation_id, exc
                )
        logger.info(
            "后台清理会话飞书副本结束 conversation_id={} count={}",
            conversation_id, len(doc_tokens),
        )


class RenameConversationReq(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


@router.get("")
async def list_conversations(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    cursor: str | None = Query(None, description="游标分页标记，首页不传，后续传上次返回的 nextCursor"),
    limit: int = Query(15, ge=1, le=50, description="每页条数"),
):
    items, next_cursor = await _service.list_active(
        session, user_id=user.user_id, cursor=cursor, limit=limit,
    )
    return ok({"items": items, "nextCursor": next_cursor})


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return ok(await _service.get_detail(
        session,
        conversation_id=str(conversation_id),
        user_id=user.user_id,
    ))


@router.patch("/{conversation_id}")
async def rename_conversation(
    conversation_id: UUID,
    req: RenameConversationReq,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return ok(await _service.rename(
        session,
        conversation_id=str(conversation_id),
        user_id=user.user_id,
        title=req.title,
    ))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    data, doc_tokens = await _service.soft_delete(
        session,
        conversation_id=str(conversation_id),
        user_id=user.user_id,
    )
    if doc_tokens:
        logger.info(
            "会话软删除成功，已登记飞书后台清理 conversation_id={} count={}",
            conversation_id, len(doc_tokens),
        )
        background_tasks.add_task(_delete_feishu_copies, str(conversation_id), doc_tokens)
    else:
        logger.info(
            "会话软删除成功，无关联飞书副本需要清理 conversation_id={}", conversation_id
        )
    return ok(data)
