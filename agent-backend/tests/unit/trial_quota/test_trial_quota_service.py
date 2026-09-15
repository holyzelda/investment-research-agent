"""试用每日额度：建行、边界、跨日重置、回退与跨会话持久化。"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.core.constants import HttpStatus
from app.modules.trial_quota.application.trial_quota_service import (
    TRIAL_DAILY_LIMIT,
    TrialQuotaExceeded,
    TrialQuotaService,
    today_shanghai,
)
from app.modules.trial_quota.infrastructure.persistence.orm import TrialDailyUsageORM


async def _new_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_status_creates_fresh_zeroed_row_for_new_user():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            status = await TrialQuotaService().get_today_status(session, "u-1")

            assert status["usageDate"] == today_shanghai().isoformat()
            for feature in ("calculation", "report", "consultation"):
                assert status[feature] == {
                    "used": 0,
                    "limit": TRIAL_DAILY_LIMIT,
                    "remaining": TRIAL_DAILY_LIMIT,
                }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_increments_each_feature_independently():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            for _ in range(3):
                await service.reserve(session, "u-1", "calculation")
            await service.reserve(session, "u-1", "report")
            await service.reserve(session, "u-1", "report")

            status = await service.get_today_status(session, "u-1")

            assert status["calculation"] == {"used": 3, "limit": 5, "remaining": 2}
            assert status["report"] == {"used": 2, "limit": 5, "remaining": 3}
            assert status["consultation"] == {"used": 0, "limit": 5, "remaining": 5}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sixth_reserve_same_day_raises_forbidden_with_feature_label():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            for _ in range(TRIAL_DAILY_LIMIT):
                await service.reserve(session, "u-1", "calculation")

            with pytest.raises(TrialQuotaExceeded) as excinfo:
                await service.reserve(session, "u-1", "calculation")

            assert excinfo.value.code == HttpStatus.FORBIDDEN
            assert "测算" in excinfo.value.msg
            assert "明日恢复" in excinfo.value.msg

            # 测算耗尽不影响其它额度
            status = await service.get_today_status(session, "u-1")
            assert status["report"]["remaining"] == TRIAL_DAILY_LIMIT
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rollover_to_new_date_resets_counters_before_first_use():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            await service.reserve(session, "u-1", "calculation")
            row = await session.get(TrialDailyUsageORM, "u-1")
            row.usage_date = today_shanghai() - timedelta(days=1)
            row.calculation_used = TRIAL_DAILY_LIMIT
            await session.commit()

            await service.reserve(session, "u-1", "calculation")

            status = await service.get_today_status(session, "u-1")
            assert status["usageDate"] == today_shanghai().isoformat()
            assert status["calculation"] == {"used": 1, "limit": 5, "remaining": 4}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refund_decrements_and_never_goes_below_zero():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            first = await service.reserve(session, "u-1", "consultation")
            second = await service.reserve(session, "u-1", "consultation")
            await service.refund(session, first)
            await service.refund(session, second)
            await service.refund(session, first)  # 已回到 0，不再减

            status = await service.get_today_status(session, "u-1")
            assert status["consultation"]["used"] == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refund_is_noop_when_usage_date_has_rolled_over():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            reservation = await service.reserve(session, "u-1", "report")
            row = await session.get(TrialDailyUsageORM, "u-1")
            row.usage_date = today_shanghai() - timedelta(days=1)
            row.report_used = 0
            await session.commit()

            await service.refund(session, reservation)

            status = await service.get_today_status(session, "u-1")
            assert status["report"]["used"] == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_counters_persist_across_sessions():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            await TrialQuotaService().reserve(session, "u-1", "calculation")

        async with maker() as session:
            status = await TrialQuotaService().get_today_status(session, "u-1")
            assert status["calculation"]["used"] == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_without_commit_rolls_back_with_outer_transaction():
    """报告场景：预占与任务创建同事务，外层回滚即释放。"""
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            reservation = await service.reserve(session, "u-1", "report", commit=False)
            assert reservation.usage_date == today_shanghai()

            await session.rollback()

            status = await service.get_today_status(session, "u-1")
            assert status["report"]["used"] == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_without_commit_persists_on_outer_commit():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            await service.reserve(session, "u-1", "report", commit=False)
            await session.commit()

        async with maker() as session:
            status = await TrialQuotaService().get_today_status(session, "u-1")
            assert status["report"]["used"] == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_guard_blocks_reserve_when_another_session_is_at_limit():
    """MySQL 下由 SELECT ... FOR UPDATE 行锁串行化并发，最终结果与顺序预占等价。"""
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            service = TrialQuotaService()
            for _ in range(TRIAL_DAILY_LIMIT):
                await service.reserve(session, "u-1", "consultation")

        async with maker() as session:
            with pytest.raises(TrialQuotaExceeded):
                await TrialQuotaService().reserve(session, "u-1", "consultation")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unsupported_feature_raises_value_error():
    engine, maker = await _new_session()
    try:
        async with maker() as session:
            with pytest.raises(ValueError):
                await TrialQuotaService().reserve(session, "u-1", "unknown")  # type: ignore[arg-type]
    finally:
        await engine.dispose()
