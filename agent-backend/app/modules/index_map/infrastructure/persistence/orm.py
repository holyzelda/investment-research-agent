"""全国指数地图 ORM 模型（ir_agent 库）。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class IndexMapPeriodORM(Base):
    """全国指数的一个可查询期次。"""

    __tablename__ = "ir_index_map_period"

    period: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class IndexMapProvinceORM(Base):
    """指定期次的一条省级指数记录及完整展示载荷。"""

    __tablename__ = "ir_index_map_province"
    __table_args__ = (
        Index("uk_ir_index_map_province_period_code", "period", "province_code", unique=True),
        Index("ix_ir_index_map_province_period_rank", "period", "rank"),
        Index("ix_ir_index_map_province_period_score", "period", "index_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(
        String(32), ForeignKey("ir_index_map_period.period"), nullable=False
    )
    province_code: Mapped[str] = mapped_column(String(32), nullable=False)
    province_name: Mapped[str] = mapped_column(String(64), nullable=False)
    map_name: Mapped[str] = mapped_column(String(64), nullable=False)
    index_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    opened: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    detail_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
