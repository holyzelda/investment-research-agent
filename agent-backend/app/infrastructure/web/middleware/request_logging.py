"""请求日志中间件（通用基础设施）。"""
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        logger.info(f"请求开始：{request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"请求结束：{request.method} {request.url.path} status={response.status_code}")
        return response
