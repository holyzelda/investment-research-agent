"""政策与市场滚动资讯 ORM 模型。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base

_PK = BigInteger().with_variant(Integer, "sqlite")


class ScrollingMessageORM(Base):
    """政策与市场栏目中展示的滚动资讯。"""

    __tablename__ = "policy_market_scrolling_messages"
    __table_args__ = (
        Index("idx_status_deleted_sort", "is_deleted", "status", "sort_order", "rating"),
        Index("idx_province", "province"),
        Index("idx_expire_time", "expire_time"),
    )

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True, server_default="0.00")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
