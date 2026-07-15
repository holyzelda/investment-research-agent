"""FastAPI 应用工厂（基础设施 · web 组合根）。

在此把配置、持久化、Nacos、中间件与各上下文路由组装成 FastAPI 应用。
中间件顺序（外→内）：CORS → 请求日志 → 平台身份读取。
说明：本系统不做登录/鉴权，平台身份中间件仅从请求头读取 user_id/username 注入 request.state。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.infrastructure.database.session import dispose_engine, init_engine
from app.infrastructure.nacos.client import cleanup_nacos, init_nacos_config
from app.modules.calculation.infrastructure.spot_daily_scheduler import (
    start_spot_daily_scheduler,
    stop_spot_daily_scheduler,
)
from app.modules.platform_access.interface.middleware import PlatformIdentityMiddleware
from app.infrastructure.web.middleware.request_logging import RequestLoggingMiddleware
from app.infrastructure.web.router_registry import register_routers


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
    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=settings.app.description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(PlatformIdentityMiddleware)
    register_routers(app)
    return app
