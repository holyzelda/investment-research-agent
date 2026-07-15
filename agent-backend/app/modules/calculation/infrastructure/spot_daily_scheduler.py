"""现货电价日更调度（应用内固定时刻触发，替代系统计划任务/cron）。

BackgroundScheduler 在独立线程工作；多实例以 MySQL GET_LOCK 互斥，任务异常只记录日志，
不会影响 FastAPI 服务本身。
"""
from datetime import date
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from sqlalchemy import create_engine, text

from app.modules.calculation.infrastructure.spot_precompute import run_precompute

_LOCK_NAME = "ir_spot_daily_update"
_JOB_ID = "spot_daily_update"
_scheduler: Optional[BackgroundScheduler] = None


def run_daily_update_once(
    ir_dsn: str,
    node_province: str = "蒙西",
    workers: int = 4,
    run_date_provider=date.today,
    precompute_fn=run_precompute,
    engine_factory=create_engine,
) -> bool:
    """抢锁后执行当天日更；抢不到锁返回 False，任务异常被记录并释放锁。"""
    engine = engine_factory(ir_dsn, pool_pre_ping=True)
    with engine.connect() as conn:
        acquired = conn.execute(
            text("SELECT GET_LOCK(:name, 0)"), {"name": _LOCK_NAME}).scalar()
        if not acquired:
            logger.info(f"现货日更新：未取得锁 {_LOCK_NAME}，跳过本次（其他实例正在执行）")
            return False
        try:
            run_date = run_date_provider()
            logger.info(f"现货日更新：开始 run_date={run_date}")
            stats = precompute_fn(
                run_date=run_date,
                node_stations=["*"],
                node_province=node_province,
                workers=workers,
                cleanup_old=True,
            )
            logger.info(f"现货日更新：完成 {stats}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"现货日更新：失败 {type(exc).__name__}: {exc}")
        finally:
            conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": _LOCK_NAME})
    return True


def start_spot_daily_scheduler() -> Optional[BackgroundScheduler]:
    """按 spot_price.daily_update_* 配置注册日更任务；关闭时不注册。"""
    global _scheduler
    from app.core.config.settings import get_settings

    settings = get_settings()
    spot = settings.spot_price
    if not spot.daily_update_enabled:
        logger.info("现货日更新：daily_update_enabled=false，不注册后台任务")
        return None

    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_update_once,
        trigger="cron",
        hour=spot.daily_update_hour,
        minute=spot.daily_update_minute,
        kwargs={
            "ir_dsn": settings.database.url.replace("+aiomysql", "+pymysql"),
            "workers": spot.daily_update_workers,
        },
        id=_JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        f"现货日更新：已注册，每天 {spot.daily_update_hour:02d}:{spot.daily_update_minute:02d} 触发")
    return scheduler


def stop_spot_daily_scheduler() -> None:
    """停止当前进程登记的日更调度器；未启动时为空操作。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("现货日更新：调度器已关闭")
