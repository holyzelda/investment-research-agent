"""路由集中注册：挂载各限界上下文的 interface 路由。"""
from fastapi import FastAPI

from app.infrastructure.web.health import router as system_router
from app.modules.calculation.interface.router import router as calculation_router
from app.modules.calculation.interface.conversation_router import router as conversation_router
from app.modules.platform_access.interface.router import router as platform_access_router
from app.modules.tie_line_map.interface.router import router as tie_line_router


def register_routers(app: FastAPI) -> None:
    app.include_router(system_router)
    app.include_router(platform_access_router)
    app.include_router(calculation_router)
    app.include_router(conversation_router)
    app.include_router(tie_line_router)
