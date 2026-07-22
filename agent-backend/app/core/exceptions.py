"""异常处理：统一为 {code, msg, data} 响应壳。"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import HttpStatus
from app.core.config.settings import get_settings


class BusinessException(Exception):
    """业务异常基类。"""

    def __init__(self, msg: str, code: int = HttpStatus.INTERNAL_SERVER_ERROR):
        self.msg = msg
        self.code = code
        super().__init__(msg)


class ValidationException(BusinessException):
    def __init__(self, msg: str = "参数验证失败"):
        super().__init__(msg=msg, code=HttpStatus.BAD_REQUEST)


class NotFoundException(BusinessException):
    def __init__(self, msg: str = "请求的资源不存在"):
        super().__init__(msg=msg, code=HttpStatus.NOT_FOUND)


def _json(code: int, msg: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"code": code, "msg": msg, "data": None})


async def _business_handler(request: Request, exc: BusinessException):
    logger.warning(f"业务异常：{exc.msg} path={request.url.path}")
    return _json(exc.code, exc.msg)


async def _http_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP 异常：{exc.detail} path={request.url.path}")
    return _json(exc.status_code, str(exc.detail))


async def _validation_handler(request: Request, exc: RequestValidationError):
    errors = "; ".join(
        f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg', '')}" for e in exc.errors()
    )
    logger.warning(f"参数校验异常：{errors} path={request.url.path}")
    return _json(HttpStatus.BAD_REQUEST, errors or "参数验证失败")


async def _global_handler(request: Request, exc: Exception):
    logger.exception(
        f"未处理异常 type={type(exc).__name__} request={request.method} "
        f"{request.url.path}: {exc}"
    )
    message = str(exc) if get_settings().app.debug else "服务器内部错误"
    return _json(HttpStatus.INTERNAL_SERVER_ERROR, message or "服务器内部错误")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessException, _business_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _global_handler)
