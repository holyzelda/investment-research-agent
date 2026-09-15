"""Persistence model for the current trial-account daily counters."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TrialDailyUsageORM(Base):
    __tablename__ = "ir_trial_daily_usage"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    calculation_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consultation_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TrialQuotaReservation:
    """A successful reservation token used to refund the same usage day."""

    def __init__(self, *, user_id: str, feature: str, usage_date: date):
        self.user_id = user_id
        self.feature = feature
        self.usage_date = usage_date
