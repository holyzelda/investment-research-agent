"""会话自定义电价临时数据的定时清理。"""
from __future__ import annotations

from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.infrastructure.database.session import get_sessionmaker
from app.modules.calculation.application.spot_context_service import SpotContextService

_JOB_ID = "spot_context_cleanup"
_scheduler: Optional[AsyncIOScheduler] = None


async def cleanup_spot_contexts_once() -> None:
    try:
        async with get_sessionmaker()() as session:
            await SpotContextService().cleanup_expired(session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("会话自定义电价清理失败：{}", exc)


def start_spot_context_cleanup_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        cleanup_spot_contexts_once,
        trigger="interval",
        hours=1,
        id=_JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("会话自定义电价清理：已注册，每小时执行")
    return scheduler


def stop_spot_context_cleanup_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("会话自定义电价清理：调度器已关闭")
