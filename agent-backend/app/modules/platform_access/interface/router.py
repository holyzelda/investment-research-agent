"""平台接入模块 · interface 路由：当前用户信息。"""
from fastapi import APIRouter, Depends

from app.core.response import ok
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter()


@router.get("/ir/me", tags=["session"])
async def me(user: CurrentUser = Depends(get_current_user)):
    """返回当前用户（来自平台注入的请求头）。本系统不做登录。"""
    return ok({"userId": user.user_id, "username": user.username})
