"""共享内核：统一响应壳 {code, msg, data}。"""
from typing import Any, Optional

from fastapi.responses import JSONResponse

from app.core.constants import HttpStatus


class APIResponse:
    """构造统一响应体。"""

    @staticmethod
    def body(data: Any = None, code: int = HttpStatus.OK, msg: str = "success") -> dict:
        return {"code": code, "msg": msg, "data": data}

    @staticmethod
    def success(data: Any = None, msg: str = "success") -> dict:
        return APIResponse.body(data=data, code=HttpStatus.OK, msg=msg)

    @staticmethod
    def error(msg: str = "error", code: int = HttpStatus.INTERNAL_SERVER_ERROR, data: Any = None) -> JSONResponse:
        return JSONResponse(status_code=code, content=APIResponse.body(data=data, code=code, msg=msg))


def ok(data: Optional[Any] = None, msg: str = "success") -> dict:
    """路由里直接 return ok(...) 即可（FastAPI 序列化为 {code,msg,data}）。"""
    return APIResponse.success(data=data, msg=msg)
