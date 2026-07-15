"""平台身份中间件（平台接入上下文 · 入站适配器）。

用户在统一平台完成登录，平台/网关将用户标识注入到转发给本系统的请求头。
本中间件直接信任并读取 header 中的 user_id/username，注入 request.state，供快照归属。
不做 token 校验、不访问任何外部登录态存储。

header 字段名由配置指定（platform.header_user_id / header_username），
默认 X-User-Id / X-User-Name，待与统一平台约定后经 Nacos/env 覆盖（PRD 挂账 #8）。
"""
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config.settings import get_settings


class PlatformIdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        platform = get_settings().platform

        user_id = request.headers.get(platform.header_user_id)
        username = request.headers.get(platform.header_username)

        if not user_id and platform.allow_anonymous:
            # 开发/联调态：平台 header 未接入时降级为匿名占位，不阻塞对话首页
            user_id = platform.anonymous_user_id
            username = username or platform.anonymous_username

        request.state.user_id = user_id
        request.state.username = username

        if user_id is None:
            logger.debug(f"未获取到平台注入身份（{platform.header_user_id}），且未允许匿名")

        return await call_next(request)
