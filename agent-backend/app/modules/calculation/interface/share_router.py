"""测算结果分享路由：创建/列表/撤销/公开访问。"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.core.exceptions import ValidationException
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.calculation_share_service import (
    CalculationShareService,
    DEFAULT_DURATION,
    VALID_DURATIONS,
)
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter(tags=["calculation-share"])
_service = CalculationShareService()


class CreateShareReq(BaseModel):
    task_id: int = Field(..., description="测算任务 ID")
    duration_days: int = Field(
        default=DEFAULT_DURATION,
        description=f"有效期天数：{'/'.join(str(d) for d in sorted(VALID_DURATIONS))}",
    )


# ── 管理端：创建分享 ───────────────────────────────────────────────


@router.post("/ir/calc/shares")
async def create_share(
    req: CreateShareReq,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """为指定测算版本创建公开分享链接。"""
    return ok(await _service.create_share(
        session, task_id=req.task_id, user_id=user.user_id, duration_days=req.duration_days,
    ))


# ── 管理端：列表 ───────────────────────────────────────────────────


@router.get("/ir/calc/shares")
async def list_shares(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    conversation_id: str | None = Query(None, description="按会话筛选"),
    task_id: int | None = Query(None, description="按任务筛选"),
):
    """列出当前用户创建的分享记录。"""
    return ok(await _service.list_shares(
        session, user_id=user.user_id, conversation_id=conversation_id, task_id=task_id,
    ))


# ── 管理端：撤销 ───────────────────────────────────────────────────


@router.post("/ir/calc/shares/revoke")
async def revoke_share(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    share_id: int | None = Query(None, description="分享记录 ID"),
    task_id: int | None = Query(None, description="测算任务 ID"),
):
    """撤销指定分享。share_id 和 task_id 至少提供一个。"""
    if share_id is None and task_id is None:
        raise ValidationException("必须提供 share_id 或 task_id")
    return ok(await _service.revoke_share(
        session, share_id=share_id, task_id=task_id, user_id=user.user_id,
    ))


# ── 公开访问：查询结果（免登录） ─────────────────────────────────────


@router.get("/ir/public/calculation-shares/{share_code}")
async def get_public_share(
    share_code: str,
    session: AsyncSession = Depends(get_db_session),
):
    """通过分享码公开查询测算结果（无需登录）。"""
    return ok(await _service.resolve_share(session, share_code=share_code))