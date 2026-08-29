"""calculation 基础设施 · 现货电价库取数（省级 long 格式 / 节点级 wide 格式）。

两个独立 MySQL，同步 pymysql（端口 SpotPriceAlgo.compute 是同步契约）：
- 省级 lamda_data.market_curve_points_current：long 格式，每天 96 行(time=00:15..24:00)，
  price 为 varchar；仅取 market=省内市场、mode=实时、area=省份。
- 节点级 dlsc_mengxi.real_time_spot_price：wide 格式，96 列(00:15..24:00) decimal；
  仅取 price_type=1、station_name=节点（当前仅蒙西）。

统一产出 {business_date: [96 个 Decimal, 按 00:15..24:00 升序]}，只含"恰好 96 点且全可解析"的完整日；
不完整/坏日直接跳过（业务确认的宽松口径）。整段查询零行 → 抛 SpotDataError（一点数据都没有才失败）。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# 96 个 15 分钟网格标签：00:15, 00:30, ..., 23:45, 24:00
GRID_LABELS = [f"{(i * 15) // 60:02d}:{(i * 15) % 60:02d}" for i in range(1, 97)]
_GRID_INDEX = {label: i for i, label in enumerate(GRID_LABELS)}


class SpotDataError(Exception):
    """现货电价库无数据（整段查询零行）。"""


def _to_decimal(v) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        value = Decimal(str(v))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _parse_date(v) -> Optional[date]:
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class ProvinceSpotRepository:
    """省级电价库（long 格式）。identifier = area（省份）。"""

    def __init__(self, dsn: str, table: str, market: str):
        self._dsn, self._table = dsn, table
        self._market = market
        self._engine: Optional[Engine] = None

    def _eng(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self._dsn, pool_pre_ping=True)
        return self._engine

    def fetch_daily_prices(self, area: str, mode: str, start_date: date, end_date: date) -> dict:
        sql = text(
            f"SELECT business_date, `time`, price FROM {self._table} "
            "WHERE market=:market AND mode=:mode AND area=:area "
            "AND business_date >= :start AND business_date < :end"
        )
        return self._fetch_daily_query(sql, {
            "market": self._market, "mode": mode, "area": area,
            "start": start_date, "end": end_date,
        }, area=area, mode=mode, start_date=start_date, end_date=end_date)

    def fetch_daily_dual_prices(
        self, area: str, charge_mode: str, discharge_mode: str,
        start_date: date, end_date: date, *, discharge_area: str | None = None,
    ) -> dict:
        """读取充、放电价格对；可为河南指定独立的区域放电源。"""
        charge = self.fetch_daily_prices(area, charge_mode, start_date, end_date)
        discharge = self.fetch_daily_prices(
            discharge_area if discharge_area is not None else area,
            discharge_mode, start_date, end_date,
        )
        return {
            day: (charge[day], discharge[day])
            for day in charge.keys() & discharge.keys()
            if len(charge[day]) == len(discharge[day]) == len(GRID_LABELS)
        }

    def _fetch_daily_query(self, sql, params, *, area, mode, start_date, end_date):
        rows = 0
        by_day: dict = {}  # date -> {label: Decimal}
        with self._eng().connect() as conn:
            result = conn.execute(sql, params)
            for business_date, tlabel, price in result:
                rows += 1
                d = _parse_date(business_date)
                if d is None or tlabel not in _GRID_INDEX:
                    continue
                by_day.setdefault(d, {})[str(tlabel)] = _to_decimal(price)
        if rows == 0:
            raise SpotDataError(
                f"省级电价库无数据：area={area} mode={mode} [{start_date},{end_date})")
        return _complete_days(by_day)


class NodeSpotRepository:
    """节点级电价库（wide 格式）。identifier = station_name（节点）。"""

    def __init__(self, dsn: str, table: str, price_type: int):
        self._dsn, self._table, self._price_type = dsn, table, price_type
        self._engine: Optional[Engine] = None

    def _eng(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self._dsn, pool_pre_ping=True)
        return self._engine

    def fetch_daily_prices(self, station_name: str, start_date: date, end_date: date) -> dict:
        cols = ", ".join(f"`{label}`" for label in GRID_LABELS)
        sql = text(
            f"SELECT `date`, {cols} FROM {self._table} "
            "WHERE price_type=:pt AND station_name=:station "
            "ORDER BY `date`, station_name"
        )
        rows = 0
        daily: dict = {}
        with self._eng().connect() as conn:
            result = conn.execute(sql, {"pt": self._price_type, "station": station_name})
            for row in result:
                rows += 1
                d = _parse_date(row[0])
                if d is None or d in daily or not (start_date <= d < end_date):
                    continue  # 同一 station 每天有多条母线(node_name)、价格一致，取首条即可
                prices = [_to_decimal(v) for v in row[1:]]           # 96 列，已按网格顺序
                if len(prices) == 96 and all(p is not None for p in prices):
                    daily[d] = prices
        if rows == 0:
            raise SpotDataError(
                f"节点电价库无数据：station={station_name} price_type={self._price_type}")
        return daily


class UploadedNodeSpotRepository:
    """主库文件导入节点电价（wide 格式），按省份、节点和价格类型隔离。"""

    def __init__(self, dsn: str, table: str = "ir_spot_price", price_type: int = 1):
        self._dsn, self._table, self._price_type = dsn, table, price_type
        self._engine: Optional[Engine] = None

    def _eng(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self._dsn, pool_pre_ping=True)
        return self._engine

    def list_stations(self, area: str) -> list[str]:
        sql = text(
            f"SELECT DISTINCT station_name FROM {self._table} "
            "WHERE area=:area AND price_type=:pt ORDER BY station_name"
        )
        with self._eng().connect() as conn:
            return [
                row[0]
                for row in conn.execute(sql, {"area": area, "pt": self._price_type})
                if row[0]
            ]

    def fetch_daily_prices(
        self,
        area: str,
        station_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        cols = ", ".join(f"`{label}`" for label in GRID_LABELS)
        sql = text(
            f"SELECT `date`, {cols} FROM {self._table} "
            "WHERE area=:area AND price_type=:pt AND station_name=:station "
            "ORDER BY `date`"
        )
        rows = 0
        daily: dict = {}
        with self._eng().connect() as conn:
            result = conn.execute(sql, {
                "area": area,
                "pt": self._price_type,
                "station": station_name,
            })
            for row in result:
                rows += 1
                business_date = _parse_date(row[0])
                if business_date is None or business_date in daily:
                    continue
                if start_date is not None and business_date < start_date:
                    continue
                if end_date is not None and business_date >= end_date:
                    continue
                prices = [_to_decimal(value) for value in row[1:]]
                if len(prices) == 96 and all(price is not None for price in prices):
                    daily[business_date] = prices
        if rows == 0:
            raise SpotDataError(
                f"上传节点电价库无数据：area={area} station={station_name} "
                f"price_type={self._price_type}"
            )
        return daily

    def last_complete_date(self, area: str, station_name: str) -> Optional[date]:
        daily = self.fetch_daily_prices(area, station_name)
        return max(daily, default=None)


def _complete_days(by_day: dict) -> dict:
    """{date: {label: Decimal}} → 只保留恰好 96 点且全可解析的日，按网格升序成 list。"""
    out: dict = {}
    for d, cells in by_day.items():
        if len(cells) != 96:
            continue
        ordered = [cells.get(label) for label in GRID_LABELS]
        if all(p is not None for p in ordered):
            out[d] = ordered
    return out
