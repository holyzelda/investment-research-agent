"""平台接入模块 · interface 依赖：从 request.state 取当前用户。"""
from fastapi import Request

from app.modules.platform_access.domain.models import CurrentUser


def get_current_user(request: Request) -> CurrentUser:
    """从 request.state 读取平台注入的身份（中间件已解析）。"""
    return CurrentUser(
        user_id=getattr(request.state, "user_id", None),
        username=getattr(request.state, "username", None),
    )
