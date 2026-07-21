"""FastAPI 应用工厂与生命周期入口。

本模块负责环境初始化、应用工厂、生命周期、中间件和业务路由；业务模块
本身不因入口迁移改变。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.infrastructure.database.session import dispose_engine, init_engine
from app.infrastructure.nacos.client import cleanup_nacos, init_nacos_config
from app.infrastructure.web.health import router as system_router
from app.infrastructure.web.middleware.request_logging import RequestLoggingMiddleware
from app.modules.calculation.infrastructure.spot_daily_scheduler import (
    start_spot_daily_scheduler,
    stop_spot_daily_scheduler,
)
from app.modules.calculation.interface.conversation_router import router as conversation_router
from app.modules.calculation.interface.router import router as calculation_router
from app.modules.platform_access.interface.middleware import PlatformIdentityMiddleware
from app.modules.platform_access.interface.router import router as platform_access_router


def register_routers(app: FastAPI) -> None:
    """集中挂载系统、平台接入、测算和会话路由。"""
    app.include_router(system_router)
    app.include_router(platform_access_router)
    app.include_router(calculation_router)
    app.include_router(conversation_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"{settings.app.name} v{settings.app.version} 启动中...（debug={settings.app.debug}）")
    await init_nacos_config()
    init_engine()
    start_spot_daily_scheduler()
    logger.info(f"{settings.app.name} 启动完成")
    yield
    stop_spot_daily_scheduler()
    await dispose_engine()
    await cleanup_nacos()
    logger.info(f"{settings.app.name} 已关闭")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=settings.app.description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(PlatformIdentityMiddleware)
    register_routers(application)
    return application


app = create_app()
