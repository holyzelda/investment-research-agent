"""联络线地图 ORM 模型（ir_agent 库）。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, Numeric, String, Text, func
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


class TieLinePowerORM(_PkTimestamp, Base):
    """联络线功率宽表：96 个时段列与 Excel 保持一致。"""

    __tablename__ = "ir_tie_line_power"
    __table_args__ = (
        Index(
            "uk_ir_tie_line_power_date_name_voltage",
            "data_date",
            "line_name",
            "voltage_text",
            unique=True,
        ),
    )

    line_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    line_name: Mapped[str] = mapped_column(String(128), nullable=False)
    voltage_text: Mapped[str] = mapped_column(String(64), nullable=False)
    power_0015_mw: Mapped[Optional[Decimal]] = mapped_column("00:15", Numeric(12, 3), nullable=True)
    power_0030_mw: Mapped[Optional[Decimal]] = mapped_column("00:30", Numeric(12, 3), nullable=True)
    power_0045_mw: Mapped[Optional[Decimal]] = mapped_column("00:45", Numeric(12, 3), nullable=True)
    power_0100_mw: Mapped[Optional[Decimal]] = mapped_column("01:00", Numeric(12, 3), nullable=True)
    power_0115_mw: Mapped[Optional[Decimal]] = mapped_column("01:15", Numeric(12, 3), nullable=True)
    power_0130_mw: Mapped[Optional[Decimal]] = mapped_column("01:30", Numeric(12, 3), nullable=True)
    power_0145_mw: Mapped[Optional[Decimal]] = mapped_column("01:45", Numeric(12, 3), nullable=True)
    power_0200_mw: Mapped[Optional[Decimal]] = mapped_column("02:00", Numeric(12, 3), nullable=True)
    power_0215_mw: Mapped[Optional[Decimal]] = mapped_column("02:15", Numeric(12, 3), nullable=True)
    power_0230_mw: Mapped[Optional[Decimal]] = mapped_column("02:30", Numeric(12, 3), nullable=True)
    power_0245_mw: Mapped[Optional[Decimal]] = mapped_column("02:45", Numeric(12, 3), nullable=True)
    power_0300_mw: Mapped[Optional[Decimal]] = mapped_column("03:00", Numeric(12, 3), nullable=True)
    power_0315_mw: Mapped[Optional[Decimal]] = mapped_column("03:15", Numeric(12, 3), nullable=True)
    power_0330_mw: Mapped[Optional[Decimal]] = mapped_column("03:30", Numeric(12, 3), nullable=True)
    power_0345_mw: Mapped[Optional[Decimal]] = mapped_column("03:45", Numeric(12, 3), nullable=True)
    power_0400_mw: Mapped[Optional[Decimal]] = mapped_column("04:00", Numeric(12, 3), nullable=True)
    power_0415_mw: Mapped[Optional[Decimal]] = mapped_column("04:15", Numeric(12, 3), nullable=True)
    power_0430_mw: Mapped[Optional[Decimal]] = mapped_column("04:30", Numeric(12, 3), nullable=True)
    power_0445_mw: Mapped[Optional[Decimal]] = mapped_column("04:45", Numeric(12, 3), nullable=True)
    power_0500_mw: Mapped[Optional[Decimal]] = mapped_column("05:00", Numeric(12, 3), nullable=True)
    power_0515_mw: Mapped[Optional[Decimal]] = mapped_column("05:15", Numeric(12, 3), nullable=True)
    power_0530_mw: Mapped[Optional[Decimal]] = mapped_column("05:30", Numeric(12, 3), nullable=True)
    power_0545_mw: Mapped[Optional[Decimal]] = mapped_column("05:45", Numeric(12, 3), nullable=True)
    power_0600_mw: Mapped[Optional[Decimal]] = mapped_column("06:00", Numeric(12, 3), nullable=True)
    power_0615_mw: Mapped[Optional[Decimal]] = mapped_column("06:15", Numeric(12, 3), nullable=True)
    power_0630_mw: Mapped[Optional[Decimal]] = mapped_column("06:30", Numeric(12, 3), nullable=True)
    power_0645_mw: Mapped[Optional[Decimal]] = mapped_column("06:45", Numeric(12, 3), nullable=True)
    power_0700_mw: Mapped[Optional[Decimal]] = mapped_column("07:00", Numeric(12, 3), nullable=True)
    power_0715_mw: Mapped[Optional[Decimal]] = mapped_column("07:15", Numeric(12, 3), nullable=True)
    power_0730_mw: Mapped[Optional[Decimal]] = mapped_column("07:30", Numeric(12, 3), nullable=True)
    power_0745_mw: Mapped[Optional[Decimal]] = mapped_column("07:45", Numeric(12, 3), nullable=True)
    power_0800_mw: Mapped[Optional[Decimal]] = mapped_column("08:00", Numeric(12, 3), nullable=True)
    power_0815_mw: Mapped[Optional[Decimal]] = mapped_column("08:15", Numeric(12, 3), nullable=True)
    power_0830_mw: Mapped[Optional[Decimal]] = mapped_column("08:30", Numeric(12, 3), nullable=True)
    power_0845_mw: Mapped[Optional[Decimal]] = mapped_column("08:45", Numeric(12, 3), nullable=True)
    power_0900_mw: Mapped[Optional[Decimal]] = mapped_column("09:00", Numeric(12, 3), nullable=True)
    power_0915_mw: Mapped[Optional[Decimal]] = mapped_column("09:15", Numeric(12, 3), nullable=True)
    power_0930_mw: Mapped[Optional[Decimal]] = mapped_column("09:30", Numeric(12, 3), nullable=True)
    power_0945_mw: Mapped[Optional[Decimal]] = mapped_column("09:45", Numeric(12, 3), nullable=True)
    power_1000_mw: Mapped[Optional[Decimal]] = mapped_column("10:00", Numeric(12, 3), nullable=True)
    power_1015_mw: Mapped[Optional[Decimal]] = mapped_column("10:15", Numeric(12, 3), nullable=True)
    power_1030_mw: Mapped[Optional[Decimal]] = mapped_column("10:30", Numeric(12, 3), nullable=True)
    power_1045_mw: Mapped[Optional[Decimal]] = mapped_column("10:45", Numeric(12, 3), nullable=True)
    power_1100_mw: Mapped[Optional[Decimal]] = mapped_column("11:00", Numeric(12, 3), nullable=True)
    power_1115_mw: Mapped[Optional[Decimal]] = mapped_column("11:15", Numeric(12, 3), nullable=True)
    power_1130_mw: Mapped[Optional[Decimal]] = mapped_column("11:30", Numeric(12, 3), nullable=True)
    power_1145_mw: Mapped[Optional[Decimal]] = mapped_column("11:45", Numeric(12, 3), nullable=True)
    power_1200_mw: Mapped[Optional[Decimal]] = mapped_column("12:00", Numeric(12, 3), nullable=True)
    power_1215_mw: Mapped[Optional[Decimal]] = mapped_column("12:15", Numeric(12, 3), nullable=True)
    power_1230_mw: Mapped[Optional[Decimal]] = mapped_column("12:30", Numeric(12, 3), nullable=True)
    power_1245_mw: Mapped[Optional[Decimal]] = mapped_column("12:45", Numeric(12, 3), nullable=True)
    power_1300_mw: Mapped[Optional[Decimal]] = mapped_column("13:00", Numeric(12, 3), nullable=True)
    power_1315_mw: Mapped[Optional[Decimal]] = mapped_column("13:15", Numeric(12, 3), nullable=True)
    power_1330_mw: Mapped[Optional[Decimal]] = mapped_column("13:30", Numeric(12, 3), nullable=True)
    power_1345_mw: Mapped[Optional[Decimal]] = mapped_column("13:45", Numeric(12, 3), nullable=True)
    power_1400_mw: Mapped[Optional[Decimal]] = mapped_column("14:00", Numeric(12, 3), nullable=True)
    power_1415_mw: Mapped[Optional[Decimal]] = mapped_column("14:15", Numeric(12, 3), nullable=True)
    power_1430_mw: Mapped[Optional[Decimal]] = mapped_column("14:30", Numeric(12, 3), nullable=True)
    power_1445_mw: Mapped[Optional[Decimal]] = mapped_column("14:45", Numeric(12, 3), nullable=True)
    power_1500_mw: Mapped[Optional[Decimal]] = mapped_column("15:00", Numeric(12, 3), nullable=True)
    power_1515_mw: Mapped[Optional[Decimal]] = mapped_column("15:15", Numeric(12, 3), nullable=True)
    power_1530_mw: Mapped[Optional[Decimal]] = mapped_column("15:30", Numeric(12, 3), nullable=True)
    power_1545_mw: Mapped[Optional[Decimal]] = mapped_column("15:45", Numeric(12, 3), nullable=True)
    power_1600_mw: Mapped[Optional[Decimal]] = mapped_column("16:00", Numeric(12, 3), nullable=True)
    power_1615_mw: Mapped[Optional[Decimal]] = mapped_column("16:15", Numeric(12, 3), nullable=True)
    power_1630_mw: Mapped[Optional[Decimal]] = mapped_column("16:30", Numeric(12, 3), nullable=True)
    power_1645_mw: Mapped[Optional[Decimal]] = mapped_column("16:45", Numeric(12, 3), nullable=True)
    power_1700_mw: Mapped[Optional[Decimal]] = mapped_column("17:00", Numeric(12, 3), nullable=True)
    power_1715_mw: Mapped[Optional[Decimal]] = mapped_column("17:15", Numeric(12, 3), nullable=True)
    power_1730_mw: Mapped[Optional[Decimal]] = mapped_column("17:30", Numeric(12, 3), nullable=True)
    power_1745_mw: Mapped[Optional[Decimal]] = mapped_column("17:45", Numeric(12, 3), nullable=True)
    power_1800_mw: Mapped[Optional[Decimal]] = mapped_column("18:00", Numeric(12, 3), nullable=True)
    power_1815_mw: Mapped[Optional[Decimal]] = mapped_column("18:15", Numeric(12, 3), nullable=True)
    power_1830_mw: Mapped[Optional[Decimal]] = mapped_column("18:30", Numeric(12, 3), nullable=True)
    power_1845_mw: Mapped[Optional[Decimal]] = mapped_column("18:45", Numeric(12, 3), nullable=True)
    power_1900_mw: Mapped[Optional[Decimal]] = mapped_column("19:00", Numeric(12, 3), nullable=True)
    power_1915_mw: Mapped[Optional[Decimal]] = mapped_column("19:15", Numeric(12, 3), nullable=True)
    power_1930_mw: Mapped[Optional[Decimal]] = mapped_column("19:30", Numeric(12, 3), nullable=True)
    power_1945_mw: Mapped[Optional[Decimal]] = mapped_column("19:45", Numeric(12, 3), nullable=True)
    power_2000_mw: Mapped[Optional[Decimal]] = mapped_column("20:00", Numeric(12, 3), nullable=True)
    power_2015_mw: Mapped[Optional[Decimal]] = mapped_column("20:15", Numeric(12, 3), nullable=True)
    power_2030_mw: Mapped[Optional[Decimal]] = mapped_column("20:30", Numeric(12, 3), nullable=True)
    power_2045_mw: Mapped[Optional[Decimal]] = mapped_column("20:45", Numeric(12, 3), nullable=True)
    power_2100_mw: Mapped[Optional[Decimal]] = mapped_column("21:00", Numeric(12, 3), nullable=True)
    power_2115_mw: Mapped[Optional[Decimal]] = mapped_column("21:15", Numeric(12, 3), nullable=True)
    power_2130_mw: Mapped[Optional[Decimal]] = mapped_column("21:30", Numeric(12, 3), nullable=True)
    power_2145_mw: Mapped[Optional[Decimal]] = mapped_column("21:45", Numeric(12, 3), nullable=True)
    power_2200_mw: Mapped[Optional[Decimal]] = mapped_column("22:00", Numeric(12, 3), nullable=True)
    power_2215_mw: Mapped[Optional[Decimal]] = mapped_column("22:15", Numeric(12, 3), nullable=True)
    power_2230_mw: Mapped[Optional[Decimal]] = mapped_column("22:30", Numeric(12, 3), nullable=True)
    power_2245_mw: Mapped[Optional[Decimal]] = mapped_column("22:45", Numeric(12, 3), nullable=True)
    power_2300_mw: Mapped[Optional[Decimal]] = mapped_column("23:00", Numeric(12, 3), nullable=True)
    power_2315_mw: Mapped[Optional[Decimal]] = mapped_column("23:15", Numeric(12, 3), nullable=True)
    power_2330_mw: Mapped[Optional[Decimal]] = mapped_column("23:30", Numeric(12, 3), nullable=True)
    power_2345_mw: Mapped[Optional[Decimal]] = mapped_column("23:45", Numeric(12, 3), nullable=True)
    power_2400_mw: Mapped[Optional[Decimal]] = mapped_column("24:00", Numeric(12, 3), nullable=True)
