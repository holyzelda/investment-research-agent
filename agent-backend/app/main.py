"""FastAPI 应用工厂与生命周期入口。

本模块负责环境初始化、应用工厂、生命周期、中间件和业务路由；业务模块
本身不因入口迁移改变。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config.settings import configure_logging, get_settings
from app.core.exceptions import register_exception_handlers
from app.infrastructure.database.session import dispose_engine, get_sessionmaker, init_engine
from app.infrastructure.nacos.client import cleanup_nacos, init_nacos_config
from app.infrastructure.web.health import router as system_router
from app.infrastructure.web.middleware.request_logging import RequestLoggingMiddleware
from app.modules.calculation.infrastructure.spot_daily_scheduler import (
    start_spot_daily_scheduler,
    stop_spot_daily_scheduler,
)
from app.modules.calculation.interface.conversation_router import router as conversation_router
from app.modules.calculation.interface.ledger_router import router as calculation_ledger_router
from app.modules.calculation.interface.share_router import router as calculation_share_router
from app.modules.calculation.interface.router import router as calculation_router
from app.modules.middle_platform.interface.router import router as middle_platform_router
from app.modules.index_map.interface.router import router as index_map_router
from app.modules.platform_access.interface.middleware import PlatformIdentityMiddleware
from app.modules.platform_access.interface.router import router as platform_access_router
from app.modules.policy_market.infrastructure.policy_ask_executor import stop_source_prefetch
from app.modules.policy_market.infrastructure.policy_ask_loader import (
    start_policy_ask_warmup,
    stop_policy_ask_warmup,
)
from app.modules.policy_market.interface.router import router as policy_market_router
from app.modules.report.application.startup_recovery import mark_interrupted_generations_failed
from app.modules.report.interface.router import router as report_router
from app.modules.tie_line_map.interface.router import router as tie_line_router


def register_routers(app: FastAPI) -> None:
    """集中挂载系统、平台接入、测算、会话和联络线路由。"""
    app.include_router(system_router)
    app.include_router(platform_access_router)
    app.include_router(calculation_ledger_router)
    app.include_router(calculation_router)
    app.include_router(conversation_router)
    app.include_router(calculation_share_router)
    app.include_router(middle_platform_router)
    app.include_router(report_router)
    app.include_router(tie_line_router)
    app.include_router(index_map_router)
    app.include_router(policy_market_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"{settings.app.name} v{settings.app.version} 启动中...（debug={settings.app.debug}）")
    await init_nacos_config()
    # Nacos 配置加载后重新应用日志设置，使远端 log 配置优先于本地 YAML。
    configure_logging(get_settings().log)
    init_engine()
    async with get_sessionmaker()() as session:
        interrupted = await mark_interrupted_generations_failed(session)
    if interrupted:
        logger.info("已将 {} 个中断的报告生成任务标记为失败", interrupted)
    start_spot_daily_scheduler()
    start_policy_ask_warmup()
    logger.info(f"{settings.app.name} 启动完成")
    yield
    stop_spot_daily_scheduler()
    await stop_source_prefetch()
    await stop_policy_ask_warmup()
    await dispose_engine()
    await cleanup_nacos()
    logger.info(f"{settings.app.name} 已关闭")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log)
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
        expose_headers=settings.cors.expose_headers,
    )
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(PlatformIdentityMiddleware)
    register_routers(application)
    return application


app = create_app()
