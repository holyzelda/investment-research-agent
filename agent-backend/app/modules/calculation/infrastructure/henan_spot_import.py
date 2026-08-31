"""河南现货电价 Excel 导入与小时数据标准化。

河南源文件常见为一日 24 个小时值（而非系统使用的 96 个 15 分钟值）。
本模块将每个小时值原样复制到对应的四个 15 分钟槽位，绝不做除四等缩放。

现行河南区域数据为按日切分的实时出清文件（如 ``2026-01-01日（实际）实时出清电价.xlsx``），
每个文件一个自然日、24 行：区域列（豫中东/豫南/豫西/豫北）+ 用户侧综合出清价列。
区域电价取各自价格列；省级统一结算价由“用户侧综合出清价”列承担（``area=河南, station=统一结算点``）。

另保留对旧式宽表（日/时点/列价格）与 ``城市/日期/时点/价格`` 长表的兼容解析，供历史数据与测试使用。
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
_REGIONS = ("豫北", "豫西", "豫中东", "豫南")
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
        raise ValueError(f"不在可测算的河南城市：{city}")
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
    """Read a daily regional workbook, a legacy wide workbook, or a long workbook.

    ``path`` 为逐日实时出清文件时自动识别。显式 ``region``/``province`` 仅用于
    tools 里历史旧式文件的外部类型提示（逐日分区文件按表头自动路由）。
    """
    report = report or HenanImportReport()
    if region is not None and province:
        raise HenanImportError("文件不能同时配置省级文件和区域文件")
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(Path(path), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise HenanImportError(f"Excel 文件无法打开：{Path(path).name}") from exc
    try:
        headers = list(next(workbook.active.iter_rows(values_only=True), ()))
        if _find_column(headers, "market") is not None and _find_column(headers, "city") is None:
            if region is not None:
                raise HenanImportError(
                    "旧式省级长表文件与区域配置冲突，请改用逐日分区实时出清文件"
                )
            return _parse_henan_province_file(path, report)
        if _is_daily_region_workbook(headers):
            if province:
                raise HenanImportError("省级来源不应使用逐日分区实时出清文件")
            return parse_henan_daily_region_file(path, report)
        # Keep the historical wide/long workbook parsers for legacy data and tests.
        if province:
            if region is not None:
                raise HenanImportError("文件不能同时配置省级文件和区域文件")
            return _parse_henan_province_file(path, report)
        if region is not None:
            if region not in _CITY_REGIONS:
                raise HenanImportError(f"不支持的河南区域：{region}")
            return _parse_henan_region_file(path, report, region)
        return _parse_henan_city_file(path, report)
    finally:
        workbook.close()


_PROVINCE_ALIASES = _HEADER_ALIASES["market"] | _HEADER_ALIASES["date"] | _HEADER_ALIASES["hour"] | _HEADER_ALIASES["price"]


def _is_daily_region_workbook(headers: list[object]) -> bool:
    """逐日分区实时出清文件的特征：含,, 非日期的序号/时刻点 + 区域价列 + 用户侧综合出清价。"""
    keys = [_header_key(header) for header in headers]
    if "用户侧综合出清价" in keys and any(key.startswith("豫") for key in keys):
        return True
    return False


def parse_henan_daily_region_file(
    path: str | Path,
    report: HenanImportReport | None = None,
) -> dict[tuple[str, date], list[Decimal]]:
    """Parse a single-day regional realtime clearing workbook.

    结构：表头 ``序号, 时刻点, 豫中东, 豫南, 豫西, 豫北, 用户侧综合出清价``，共 24 个时刻点行。
    返回 5 条曲线（4 区域 + 省级“用户侧综合出清价”），每个小时值展开为 4 个 15 分钟槽。
    区域列取值稳定在列 2..5；省级列支持“用户侧综合出清价”别名。
    """
    from openpyxl import load_workbook

    report = report or HenanImportReport()
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = list(next(rows, ()))
        region_cols = [(i, str(value).strip()) for i, value in enumerate(headers)
                       if str(value or "").strip() in _REGIONS]
        province_col = next(
            (i for i, value in enumerate(headers)
             if _header_key(value) == "用户侧综合出清价"), None)
        if len(region_cols) != 4 or province_col is None:
            raise HenanImportError(
                f"逐日分区文件需含 {', '.join(_REGIONS)} 与用户侧综合出清价列：{Path(path).name}"
            )
        day_match = re.search(r"(20\d{2}[-\/年月]\d{1,2}[-\/月]\d{1,2})", Path(path).name)
        day_text = (
            day_match.group(1).replace("月", "-").replace("日", "")
            if day_match is not None else ""
        )
        can_parse = _parse_date(day_text) if day_text else None
        # 文件名里的日期以“2026-01-01”形态出现（不替换成分隔），_parse_date 已支持；
        # 若用月/日替换后仍是纯数字形态，则作兜底。
        if can_parse is None and day_text:
            can_parse = _parse_date("".join(day_text.split("-")))
        can_day = None
        materialized = list(rows)
        hour_by_row: dict[int, int] = {}
        for row_index, row in enumerate(materialized):
            if not any(value not in (None, "") for value in row):
                continue
            report.rows_seen += 1
            if can_parse is None:
                for cell in row:
                    parsed = _parse_date(cell)
                    if parsed is not None and (can_day is None or parsed > can_day):
                        can_day = parsed
            # 时刻标签“1:00..24:00”表示第 1..24 个小时（非钟表时刻），
            # 1:00 对应槽 0，24:00 对应槽 23。
            slot = _daily_hour_slot(row[1])
            if slot is not None:
                hour_by_row[row_index] = slot

        if can_day is None:
            can_day = can_parse
        if can_day is None:
            raise HenanImportError(
                f"逐日分区文件无法从文件名或工作表日期确定业务日期：{Path(path).name}"
            )

        result = {}
        hour_values = sorted(hour_by_row.values())
        if set(hour_values) != set(range(24)):
            raise HenanImportError(
                f"逐日分区文件未覆盖完整 24 个时刻点：文件={Path(path).name}，"
                f"行数={len(hour_by_row)}，时刻={hour_values}"
            )
        for column_index, region_name in region_cols:
            # 按小时索引组装 24 个小时值；逐行定位到时刻列，取区域列
            ordered = [None] * 24
            for row_index, hour in hour_by_row.items():
                row_vals = materialized[row_index]
                if column_index < len(row_vals):
                    ordered[hour] = row_vals[column_index]
            expanded = expand_hourly_prices(ordered)
            if expanded is None:
                report.invalid_city_days += 1
                continue
            result[(region_name, can_day)] = expanded
            report.valid_city_days += 1
        # 省级用户侧综合出清价列单独解析
        if province_col is not None:
            ordered = [None] * 24
            for row_index, hour in hour_by_row.items():
                row_vals = materialized[row_index]
                if province_col < len(row_vals):
                    ordered[hour] = row_vals[province_col]
            expanded = expand_hourly_prices(ordered)
            if expanded is not None:
                result[("河南", can_day)] = expanded
                report.valid_city_days += 1
            else:
                report.invalid_city_days += 1
        return result
    finally:
        workbook.close()


def _daily_hour_slot(value: object) -> int | None:
    """逐日文件的时刻标签：1:00..24:00 为第 1..24 个小时 → 返回槽下标 0..23。

    24:00 映射到槽 23。与旧区域文件（1 小时=4 个 15 分钟槽）语义一致。
    """
    if value is None:
        return None
    raw = str(value).strip()
    if raw in ("24:00", "24：00"):
        return 23
    match = re.fullmatch(r"(?:[1-9]|1[0-9]|2[0-3]):00", raw)
    if match:
        return int(raw.split(":", 1)[0]) - 1
    return None


def _parse_henan_city_file(path: str | Path, report: HenanImportReport) -> dict[tuple[str, date], list[Decimal]]:
    """Read a legacy city/date workbook in wide 24-hour or long hourly form."""
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
    """导入河南现货电价。

    新会话入口：``files`` 指向逐日分区实时出清目录（默认 ``directory.rglob("*.xlsx")``），
    每个逐日文件自动路由到 ``parse_henan_daily_region_file``，产出
    4 个区域（豫中东/豫南/豫西/豫北）+ 省级用户侧综合出清价，共 5 条曲线。
    文件名为 ``2026-01-01日（实际）实时出清电价.xlsx`` 形态。

    旧式入口（``province_file``/``region_files``）仅保留给历史宽表：省级长表、
    按月的区域文件；区域名仍是业务配置。
    """
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
                region=region if not (
                    province_file is not None and path == Path(province_file)
                ) else None,
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
