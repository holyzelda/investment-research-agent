"""联络线地图 ORM 模型（ir_agent 库）。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base

_PK = BigInteger().with_variant(Integer, "sqlite")


class _PkTimestamp:
    """自增主键 + 创建时间。"""

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class TieLineMapORM(_PkTimestamp, Base):
    """联络线地图底表：跨省线路、端点坐标、容量与投运年份。"""

    __tablename__ = "ir_tie_line_map"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    start_point: Mapped[str] = mapped_column(String(128), nullable=False)
    end_point: Mapped[str] = mapped_column(String(128), nullable=False)
    length_text: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    voltage_text: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    end_region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    start_latitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    end_longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    end_latitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    rated_capacity_mw: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    operation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    coordinate_basis: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_basis_note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
