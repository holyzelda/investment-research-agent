"""河南现货电价 Excel 导入与小时数据标准化。

河南源文件常见为一日 24 个小时值（而非系统使用的 96 个 15 分钟值）。
本模块将每个小时值原样复制到对应的四个 15 分钟槽位，绝不做除四等缩放。
同时兼容宽表和 ``城市/日期/时点/价格`` 长表，供批量导入主库使用。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Iterable

from sqlalchemy import Engine, create_engine, text

from app.core.config.settings import get_settings
from app.modules.calculation.infrastructure.spot_price_repo import GRID_LABELS


# 河南常用电网区域。接受带“市”“地区”的输入，返回稳定的区域名。
_CITY_REGIONS = {
    "豫北": ("安阳", "濮阳", "鹤壁", "新乡", "焦作"),
    "豫西": ("洛阳", "三门峡"),
    "豫中东": ("郑州", "开封", "许昌", "周口", "商丘"),
    "豫南": ("南阳", "驻马店", "信阳", "平顶山"),
}
CITY_TO_REGION = {city: region for region, cities in _CITY_REGIONS.items() for city in cities}


def city_to_region(city: object, *, strict: bool = False) -> str | None:
    """将河南城市名映射为四个后端区域；未知值默认返回 None。"""
    value = str(city or "").strip().replace("河南省", "")
    value = re.sub(r"(市|地区)$", "", value)
    result = CITY_TO_REGION.get(value)
    if result is None and strict:
        raise ValueError(f"未知河南城市：{city}")
    return result


def _decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return result if result.is_finite() else None


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y%m%d"):
        try:
            return datetime.strptime(text_value, fmt).date()
        except ValueError:
            continue
    return None


def parse_hour(value: object) -> int | None:
    """Parse an hour label to 0..23, accepting 1..24 spreadsheet conventions.

    ``24:00`` is the 24th hourly value and therefore maps to index 23. Decimal
    Excel time values and labels such as ``第1小时``/``1时`` are accepted.
    """
    if isinstance(value, datetime):
        return value.hour
    if isinstance(value, timedelta):
        minutes = int(value.total_seconds() // 60)
        if minutes % 60 == 0 and 0 <= minutes <= 1440:
            return 23 if minutes == 1440 else minutes // 60
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer() and 0 <= int(value) <= 24:
            number = int(value)
            return 23 if number == 24 else (number - 1 if 1 <= number <= 24 else 0)
    raw = str(value or "").strip().lower().replace("：", ":")
    match = re.search(r"(\d{1,2})\s*(?::\s*\d{1,2})?", raw)
    if not match:
        return None
    number = int(match.group(1))
    # Labels with an explicit colon are clock labels (00:00 -> hour 0).
    if ":" in raw:
        return 23 if number == 24 else number if 0 <= number <= 23 else None
    return 23 if number == 24 else number - 1 if 1 <= number <= 24 else 0 if number == 0 else None


def expand_hourly_prices(prices: Iterable[object]) -> list[Decimal] | None:
    """Expand exactly 24 hourly prices into 96 quarter-hour prices."""
    values = [_decimal(value) for value in prices]
    if len(values) != 24 or any(value is None for value in values):
        return None
    return [value for value in values for _ in range(4)]


_HEADER_ALIASES = {
    "market": {"市场", "market"},
    "city": {"城市", "地区", "地市", "市名", "city"},
    "date": {"日期", "交易日期", "业务日期", "date"},
    "hour": {"时点", "时间", "小时", "时刻", "hour", "time"},
    "price": {"价格", "电价", "节点电价", "出清价格", "price"},
}


def _header_key(value: object) -> str:
    return re.sub(r"[\s（）()\[\]【】]", "", str(value or "").strip()).lower()


def _find_column(headers: list[object], kind: str) -> int | None:
    aliases = {_header_key(item) for item in _HEADER_ALIASES[kind]}
    normalized = [_header_key(header) for header in headers]
    for index, key in enumerate(normalized):
        if key in aliases:
            return index
    candidates = []
    for index, key in enumerate(normalized):
        if kind == "price" and ("价格类型" in key or "类型" in key):
            continue
        if any(alias in key for alias in aliases if len(alias) > 1):
            candidates.append((len(key), index))
    return min(candidates)[1] if candidates else None


@dataclass
class HenanImportReport:
    files_seen: int = 0
    files_failed: int = 0
    rows_seen: int = 0
    valid_city_days: int = 0
    invalid_city_days: int = 0
    written_rows: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class HenanImportError(ValueError):
    pass


def parse_henan_file(
    path: str | Path,
    report: HenanImportReport | None = None,
    *,
    region: str | None = None,
    province: bool = False,
) -> dict[tuple[object, object], list[Decimal]]:
    """Read a province workbook, an explicitly named region workbook, or a legacy city workbook."""
    report = report or HenanImportReport()
    if region is not None and province:
        raise HenanImportError("文件不能同时配置省级文件和区域文件")
    if province:
        return _parse_henan_province_file(path, report)
    if region is not None:
        if region not in _CITY_REGIONS:
            raise HenanImportError(f"不支持的河南区域：{region}")
        return _parse_henan_region_file(path, report, region)
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(Path(path), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise HenanImportError(f"Excel 文件无法打开：{Path(path).name}") from exc
    try:
        headers = list(next(workbook.active.iter_rows(values_only=True), ()))
    finally:
        workbook.close()
    if _find_column(headers, "market") is not None and _find_column(headers, "city") is None:
        return _parse_henan_province_file(path, report)
    # Keep the historical city-based parser for generic test/long workbooks.
    return _parse_henan_city_file(path, report)


def _parse_henan_city_file(path: str | Path, report: HenanImportReport) -> dict[tuple[str, date], list[Decimal]]:
    """Read a city/date workbook in wide 24-hour or long hourly form."""
    from openpyxl import load_workbook
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = list(next(rows, ()))
        city_col, date_col = _find_column(headers, "city"), _find_column(headers, "date")
        hour_col, price_col = _find_column(headers, "hour"), _find_column(headers, "price")
        if city_col is None or date_col is None:
            raise HenanImportError(f"缺少城市或日期列：{Path(path).name}")
        hourly: dict[tuple[date, str], dict[int, Decimal | None]] = defaultdict(dict)
        wide_hour_cols: dict[int, int] = {}
        if hour_col is None or price_col is None:
            for index, header in enumerate(headers):
                hour = parse_hour(header)
                if hour is not None and index not in (city_col, date_col):
                    wide_hour_cols[hour] = index
            if len(wide_hour_cols) != 24:
                raise HenanImportError(f"未找到 24 个小时价格列：{Path(path).name}")
        for row in rows:
            if not any(value not in (None, "") for value in row):
                continue
            report.rows_seen += 1
            city, day = str(row[city_col] or "").strip(), _parse_date(row[date_col])
            if not city or day is None:
                report.invalid_city_days += 1
                continue
            key = (city, day)
            if hour_col is not None and price_col is not None:
                hour = parse_hour(row[hour_col])
                if hour is not None:
                    hourly[key][hour] = _decimal(row[price_col])
            else:
                for hour, index in wide_hour_cols.items():
                    hourly[key][hour] = _decimal(row[index] if index < len(row) else None)
        result = {}
        for (city, day), values in hourly.items():
            expanded = expand_hourly_prices(values.get(hour) for hour in range(24))
            if expanded is None:
                report.invalid_city_days += 1
            else:
                result[(day, city)] = expanded
                report.valid_city_days += 1
        return result
    finally:
        workbook.close()


def _parse_henan_province_file(path: str | Path, report: HenanImportReport) -> dict[tuple[str, date], list[Decimal]]:
    """Parse the province settlement-point long workbook."""
    from openpyxl import load_workbook

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = list(next(rows, ()))
        market_col = _find_column(headers, "market")
        date_col = _find_column(headers, "date")
        hour_col = _find_column(headers, "hour")
        price_col = _find_column(headers, "price")
        if date_col is None or hour_col is None or price_col is None:
            raise HenanImportError(f"省级文件缺少日期、时间点或电价列：{Path(path).name}")
        hourly: dict[date, dict[int, Decimal | None]] = defaultdict(dict)
        for row in rows:
            if not any(value not in (None, "") for value in row):
                continue
            report.rows_seen += 1
            day = _parse_date(row[date_col])
            raw_hour = row[hour_col]
            # 此文件的 1:00...24:00 表示第 1...24 个小时，
            # 与普通钟表标签不同：1:00 对应第一个小时槽（索引 0）。
            hour_text = str(raw_hour or "").strip().replace("：", ":")
            if re.fullmatch(r"(?:[1-9]|1[0-9]|2[0-4]):00", hour_text):
                hour = int(hour_text.split(":", 1)[0]) - 1
            else:
                hour = parse_hour(raw_hour)
            price = _decimal(row[price_col])
            market = str(row[market_col] or "").strip() if market_col is not None else ""
            if day is None or hour is None or price is None or market not in ("", "日前"):
                continue
            hourly[day][hour] = price
        result = {}
        for day, values in hourly.items():
            expanded = expand_hourly_prices(values.get(hour) for hour in range(24))
            if expanded is None:
                report.invalid_city_days += 1
            else:
                result[("河南", day)] = expanded
                report.valid_city_days += 1
        return result
    finally:
        workbook.close()


def _parse_henan_region_file(
    path: str | Path,
    report: HenanImportReport,
    region: str,
) -> dict[tuple[str, date], list[Decimal]]:
    """Parse a named regional workbook with 年/月/时间 and 24 price columns."""
    from openpyxl import load_workbook

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = list(next(rows, ()))
        date_col = _find_column(headers, "date")
        if date_col is None:
            date_col = _find_column(headers, "hour")  # replaced below for 年/月/时间 files
        time_col = next((i for i, value in enumerate(headers) if str(value or "").strip() == "时间"), None)
        if time_col is None:
            raise HenanImportError(f"区域文件缺少时间列：{Path(path).name}")
        region_cols = [(i, str(value).strip().split("实时", 1)[0])
                       for i, value in enumerate(headers)
                       if "实时" in str(value or "") and "时刻" in str(value or "")]
        if len(region_cols) != 24:
            raise HenanImportError(f"区域文件未找到 24 个价格列：{Path(path).name}")
        if any(item[1] != region for item in region_cols):
            raise HenanImportError(
                f"区域文件列名与配置区域不一致：配置={region}，文件={region_cols[0][1]}"
            )
        result = {}
        for row in rows:
            if not any(value not in (None, "") for value in row):
                continue
            report.rows_seen += 1
            raw_day = row[time_col]
            day = _parse_date(raw_day)
            values = [row[index] if index < len(row) else None for index, _ in region_cols]
            expanded = expand_hourly_prices(values)
            if day is None or expanded is None:
                report.invalid_city_days += 1
                continue
            result[(region, day)] = expanded
            report.valid_city_days += 1
        return result
    finally:
        workbook.close()


def _upsert_sql(dialect: str) -> str:
    columns = ["area", "station_name", "price_type", "date", *GRID_LABELS]
    names = ", ".join(f"`{column}`" for column in columns)
    values = ", ".join(f":v{i}" for i in range(len(columns)))
    updates = ", ".join(f"`{column}`=excluded.`{column}`" for column in GRID_LABELS)
    if dialect != "sqlite":
        updates = ", ".join(f"`{column}`=VALUES(`{column}`)" for column in GRID_LABELS)
    conflict = "ON CONFLICT (area, station_name, price_type, date) DO UPDATE SET" if dialect == "sqlite" else "ON DUPLICATE KEY UPDATE"
    return f"INSERT INTO ir_spot_price ({names}) VALUES ({values}) {conflict} {updates}"


def import_henan_directory(
    directory: str | Path,
    *,
    ir_engine: Engine | None = None,
    price_type: int = 1,
    dry_run: bool = True,
    files: Iterable[str | Path] | None = None,
    province_file: str | Path | None = None,
    region_files: Iterable[tuple[str | Path, str]] | None = None,
) -> HenanImportReport:
    """Import the province workbook and explicitly configured regional workbooks."""
    report = HenanImportReport()
    base = Path(directory)
    if province_file is not None or region_files is not None:
        paths_and_regions = []
        if province_file is not None:
            paths_and_regions.append((Path(province_file), None))
        paths_and_regions.extend((Path(path), region) for path, region in (region_files or ()))
    else:
        paths_and_regions = [(Path(item), None) for item in (
            files if files is not None else sorted(base.rglob("*.xlsx"))
        )]

    engine = ir_engine
    if not dry_run and engine is None:
        settings = get_settings()
        engine = create_engine(settings.database.url.replace("+aiomysql", "+pymysql"), pool_pre_ping=True)
    statement = None
    for path, region in paths_and_regions:
        report.files_seen += 1
        try:
            parsed = parse_henan_file(
                path,
                report,
                region=region,
                province=province_file is not None and path == Path(province_file),
            )
            if not dry_run and parsed:
                with engine.begin() as conn:
                    if statement is None:
                        statement = text(_upsert_sql(conn.dialect.name))
                    for (area, business_date), prices in parsed.items():
                        station_name = "统一结算点" if area == "河南" else area
                        values = {"v0": area, "v1": station_name, "v2": price_type, "v3": business_date}
                        values.update({f"v{i + 4}": str(price) for i, price in enumerate(prices)})
                        conn.execute(statement, values)
                report.written_rows += len(parsed)
        except HenanImportError as exc:
            report.files_failed += 1
            report.errors.append(str(exc))
    return report
