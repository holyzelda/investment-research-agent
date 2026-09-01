"""平台接入模块 · interface 依赖：从 request.state 取当前用户。"""
from fastapi import Depends, Request

from app.modules.platform_access.application.user_scope_service import UserScopeService
from app.modules.platform_access.domain.models import CurrentUser, UserScope


def get_current_user(request: Request) -> CurrentUser:
    """从 request.state 读取平台注入的身份（中间件已解析）。"""
    return CurrentUser(
        user_id=getattr(request.state, "user_id", None),
        username=getattr(request.state, "username", None),
    )


async def get_user_scope(
    user: CurrentUser = Depends(get_current_user),
) -> UserScope:
    """每请求实时向用户管理中心确认角色与可见成员，不信任前端上报的身份。"""
    return await UserScopeService().resolve(user)
