"""Atomic daily quota operations for trial accounts."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import HttpStatus
from app.core.exceptions import BusinessException
from app.modules.trial_quota.infrastructure.persistence.orm import (
    TrialDailyUsageORM,
    TrialQuotaReservation,
)

TRIAL_DAILY_LIMIT = 5
Feature = Literal["calculation", "report", "consultation"]
_FEATURE_COLUMNS = {
    "calculation": TrialDailyUsageORM.calculation_used,
    "report": TrialDailyUsageORM.report_used,
    "consultation": TrialDailyUsageORM.consultation_used,
}
_TZ = ZoneInfo("Asia/Shanghai")


class TrialQuotaExceeded(BusinessException):
    def __init__(self, feature: str):
        labels = {"calculation": "测算", "report": "报告", "consultation": "政策咨询"}
        super().__init__(
            f"今日{labels.get(feature, '试用')}额度已用完，明日恢复",
            code=HttpStatus.FORBIDDEN,
        )


def today_shanghai() -> date:
    return datetime.now(_TZ).date()


class TrialQuotaService:
    @staticmethod
    async def _get_locked_row(session: AsyncSession, user_id: str, today: date):
        dialect = session.bind.dialect.name if session.bind is not None else ""
        if dialect == "mysql":
            await session.execute(
                insert(TrialDailyUsageORM)
                .values(user_id=user_id, usage_date=today)
                .prefix_with("IGNORE")
            )
        row = (await session.execute(
            select(TrialDailyUsageORM)
            .where(TrialDailyUsageORM.user_id == user_id)
            .with_for_update()
        )).scalar_one_or_none()
        if row is None:
            row = TrialDailyUsageORM(user_id=user_id, usage_date=today)
            session.add(row)
            await session.flush()
        if row.usage_date != today:
            row.usage_date = today
            row.calculation_used = 0
            row.report_used = 0
            row.consultation_used = 0
        return row

    async def get_today_status(self, session: AsyncSession, user_id: str) -> dict:
        row = await self._get_locked_row(session, user_id, today_shanghai())
        await session.commit()
        return self.serialize(row)

    async def reserve(
        self,
        session: AsyncSession,
        user_id: str,
        feature: Feature,
        *,
        commit: bool = True,
    ) -> TrialQuotaReservation:
        column = _FEATURE_COLUMNS.get(feature)
        if column is None:
            raise ValueError(f"unsupported trial quota feature: {feature}")
        today = today_shanghai()
        row = await self._get_locked_row(session, user_id, today)
        if getattr(row, column.key) >= TRIAL_DAILY_LIMIT:
            await session.rollback()
            raise TrialQuotaExceeded(feature)
        setattr(row, column.key, getattr(row, column.key) + 1)
        if commit:
            await session.commit()
        else:
            await session.flush()
        return TrialQuotaReservation(user_id=user_id, feature=feature, usage_date=today)

    async def refund(
        self,
        session: AsyncSession,
        reservation: TrialQuotaReservation,
        *,
        commit: bool = True,
    ) -> None:
        row = (await session.execute(
            select(TrialDailyUsageORM)
            .where(TrialDailyUsageORM.user_id == reservation.user_id)
            .with_for_update()
        )).scalar_one_or_none()
        if row is not None and row.usage_date == reservation.usage_date:
            column = _FEATURE_COLUMNS[reservation.feature]
            setattr(row, column.key, max(0, getattr(row, column.key) - 1))
        if commit:
            await session.commit()
        else:
            await session.flush()

    @staticmethod
    def serialize(row: TrialDailyUsageORM) -> dict:
        def counter(used: int) -> dict:
            return {
                "used": used,
                "limit": TRIAL_DAILY_LIMIT,
                "remaining": max(0, TRIAL_DAILY_LIMIT - used),
            }

        return {
            "usageDate": row.usage_date.isoformat(),
            "calculation": counter(row.calculation_used),
            "report": counter(row.report_used),
            "consultation": counter(row.consultation_used),
        }
