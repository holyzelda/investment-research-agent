"""平台身份中间件（平台接入上下文 · 入站适配器）。

统一网关认证后将 ecenter 身份以固定的 `userId`、`username` Header
转发给本系统。本地开发由前端请求拦截器传递同一份已解析身份。
不做 Token 校验、不访问任何外部登录态存储。
"""
from urllib.parse import unquote

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class PlatformIdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        user_id = (request.headers.get("userId") or "").strip()
        encoded_username = (request.headers.get("username") or "").strip()
        username = unquote(encoded_username).strip()

        if not user_id or not username:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "未获取到平台用户身份", "data": None},
            )

        request.state.user_id = user_id
        request.state.username = username
        return await call_next(request)
