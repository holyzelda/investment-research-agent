"""山西实时节点边际电价 Excel 长表导入。"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from posixpath import normpath
import re
from typing import Iterable, Iterator
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from sqlalchemy import Engine, create_engine, text

from app.core.config.settings import get_settings
from app.modules.calculation.infrastructure.spot_price_repo import GRID_LABELS, _to_decimal

_HEADER = (
    "节点名称",
    "日期",
    "时点",
    "电能量价格（元/MWh）",
    "阻塞价格（元/MWh）",
    "节点电价（元/MWh）",
)
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_BUS_VARIANT = re.compile(
    r"^(?P<base>.+?)(?:[./·_\-\s]*)"
    r"(?P<variant>II|III|IV|I|[A-D]|[1-9]|[一二三四]|[东西南北]|[甲乙丙丁])"
    r"(?P<qualifier>[甲乙丙丁]?)母线$",
    re.IGNORECASE,
)


@dataclass
class ShanxiImportReport:
    files_seen: int = 0
    files_failed: int = 0
    rows_seen: int = 0
    numeric_nodes_skipped: int = 0
    numeric_rows_skipped: int = 0
    valid_node_days: int = 0
    invalid_node_days: int = 0
    written_rows: int = 0
    d_plus_e_mismatches: int = 0
    duplicate_node_days: int = 0
    low_complete_day_stations: int = 0
    low_complete_day_rows: int = 0
    errors: list[str] = field(default_factory=list)
    skipped_node_days: list[str] = field(default_factory=list)
    duplicate_node_day_details: list[str] = field(default_factory=list)
    low_complete_day_details: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_failed": self.files_failed,
            "rows_seen": self.rows_seen,
            "numeric_nodes_skipped": self.numeric_nodes_skipped,
            "numeric_rows_skipped": self.numeric_rows_skipped,
            "valid_node_days": self.valid_node_days,
            "invalid_node_days": self.invalid_node_days,
            "written_rows": self.written_rows,
            "d_plus_e_mismatches": self.d_plus_e_mismatches,
            "duplicate_node_days": self.duplicate_node_days,
            "low_complete_day_stations": self.low_complete_day_stations,
            "low_complete_day_rows": self.low_complete_day_rows,
            "errors": list(self.errors),
            "skipped_node_days": list(self.skipped_node_days),
            "duplicate_node_day_details": list(self.duplicate_node_day_details),
            "low_complete_day_details": list(self.low_complete_day_details),
        }


class ShanxiImportError(ValueError):
    """文件结构或业务日期不能用于导入。"""


def normalize_station_name(value: object) -> str | None:
    """过滤数字节点，并删除第一个点号之前的区域前缀。"""
    raw = str(value or "").strip()
    if not raw or raw.isdigit():
        return None
    _, separator, suffix = raw.partition(".")
    suffix = suffix.strip()
    if not separator or not suffix:
        return None
    return suffix


def bus_base_name(station_name: str) -> str | None:
    """返回明确母线变体的基础名称；普通名称不参与去重。"""
    matched = _BUS_VARIANT.fullmatch(station_name.strip())
    if matched is None:
        return None
    base = matched.group("base").rstrip("./·_- ")
    if not base or base.endswith("虚拟"):
        return None
    return base


def _natural_name_key(value: str) -> tuple:
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    )


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _column_number(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha())
    result = 0
    for char in letters.upper():
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def _shared_strings(zf: ZipFile) -> list[str]:
    try:
        with zf.open("xl/sharedStrings.xml") as source:
            root = ElementTree.parse(source).getroot()
    except KeyError:
        return []
    values = []
    for item in root.findall(f"{_NS}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{_NS}t")))
    return values


def _sheet_path(zf: ZipFile) -> str:
    try:
        with zf.open("xl/workbook.xml") as source:
            workbook = ElementTree.parse(source).getroot()
        sheet = workbook.find(f"{_NS}sheets/{_NS}sheet")
        relation = sheet.get(f"{_REL_NS}id") if sheet is not None else None
        with zf.open("xl/_rels/workbook.xml.rels") as source:
            rels = ElementTree.parse(source).getroot()
        for rel in rels:
            if rel.get("Id") == relation:
                target = rel.get("Target", "")
                return normpath(f"xl/{target.lstrip('/')}")
    except (KeyError, ElementTree.ParseError) as error:
        raise ShanxiImportError("Excel 工作簿结构无效") from error
    return "xl/worksheets/sheet1.xml"


def _xlsx_rows(path: Path) -> Iterator[tuple[object, ...]]:
    """按 XML 实际行流式读取，不依赖错误的 worksheet dimension。"""
    try:
        zf = ZipFile(path)
    except (BadZipFile, OSError) as error:
        raise ShanxiImportError(f"Excel 文件无法打开：{path.name}") from error
    try:
        shared = _shared_strings(zf)
        with zf.open(_sheet_path(zf)) as source:
            for event, row in ElementTree.iterparse(source, events=("end",)):
                if row.tag != f"{_NS}row":
                    continue
                cells: dict[int, object] = {}
                for cell in row.findall(f"{_NS}c"):
                    ref = cell.get("r", "A1")
                    column = _column_number(ref)
                    value_node = cell.find(f"{_NS}v")
                    value = value_node.text if value_node is not None else None
                    if cell.get("t") == "s" and value is not None:
                        index = int(value)
                        value = shared[index] if 0 <= index < len(shared) else None
                    elif cell.get("t") == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter(f"{_NS}t"))
                    cells[column] = value
                width = max(cells, default=-1) + 1
                yield tuple(cells.get(i) for i in range(width))
                row.clear()
    except (KeyError, ElementTree.ParseError, ValueError, IndexError) as error:
        raise ShanxiImportError(f"Excel 工作表读取失败：{path.name}") from error
    finally:
        zf.close()


def _file_date(path: Path, year: int | None = None) -> date:
    try:
        month, day = path.stem.split(".", 1)
        if year is None:
            year = next(
                int(part) for parent in path.parents for part in parent.parts
                if len(part) == 4 and part.isdigit()
            )
        return date(year, int(month), int(day))
    except (StopIteration, ValueError, TypeError) as error:
        raise ShanxiImportError(
            f"无法从年度目录和 M.DD.xlsx 文件名确定日期：{path.name}"
        ) from error


def _empty_days() -> dict[tuple[date, str], dict[str, Decimal | None]]:
    return defaultdict(dict)


def parse_shanxi_file(
    path: str | Path,
    report: ShanxiImportReport | None = None,
    *,
    year: int | None = None,
) -> dict:
    path = Path(path)
    report = report or ShanxiImportReport()
    expected_date = _file_date(path, year)
    rows = _xlsx_rows(path)
    header = next(rows, None)
    if tuple(str(value or "").strip() for value in (header or ())) != _HEADER:
        raise ShanxiImportError(f"表头不匹配：{path.name}")
    days = _empty_days()
    numeric_nodes: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        if not any(value not in (None, "") for value in row):
            continue
        if len(row) < 6:
            raise ShanxiImportError(f"第 {row_number} 行列数不足：{path.name}")
        report.rows_seen += 1
        raw_name = str(row[0] or "").strip()
        if raw_name.isdigit():
            report.numeric_rows_skipped += 1
            numeric_nodes.add(raw_name)
            continue
        station = normalize_station_name(raw_name)
        if station is None:
            report.invalid_node_days += 1
            report.skipped_node_days.append(f"{path.name}:第{row_number}行:{raw_name}")
            continue
        business_date = _parse_date(row[1])
        if business_date != expected_date:
            raise ShanxiImportError(f"第 {row_number} 行日期与文件名不一致：{row[1]}")
        label = str(row[2] or "").strip()
        if label not in GRID_LABELS:
            raise ShanxiImportError(f"第 {row_number} 行时点无效：{label}")
        energy = _decimal(row[3])
        congestion = _decimal(row[4])
        calculated = energy + congestion if energy is not None and congestion is not None else None
        key = (business_date, station)
        if label in days[key]:
            days[key][label] = None
        else:
            days[key][label] = calculated
        if _decimal(row[5]) is not None and calculated is not None and _decimal(row[5]) != calculated:
            report.d_plus_e_mismatches += 1
    valid = {}
    for key, prices in days.items():
        if len(prices) != 96 or any(prices.get(label) is None for label in GRID_LABELS):
            report.invalid_node_days += 1
            report.skipped_node_days.append(f"{path.name}:{key[0]}:{key[1]}")
            continue
        valid[key] = [prices[label] for label in GRID_LABELS]
        report.valid_node_days += 1
    report.numeric_nodes_skipped += len(numeric_nodes)
    return valid


@dataclass
class ShanxiDeduplicationReport:
    rows_seen: int = 0
    candidate_groups: int = 0
    duplicate_stations: int = 0
    duplicate_rows: int = 0
    deleted_rows: int = 0
    examples: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "rows_seen": self.rows_seen,
            "candidate_groups": self.candidate_groups,
            "duplicate_stations": self.duplicate_stations,
            "duplicate_rows": self.duplicate_rows,
            "deleted_rows": self.deleted_rows,
            "examples": list(self.examples),
        }


def deduplicate_shanxi_spot_prices(
    *,
    ir_engine: Engine | None = None,
    price_type: int = 1,
    dry_run: bool = True,
    example_limit: int = 20,
) -> ShanxiDeduplicationReport:
    """删除价格完全被另一母线覆盖的站点，默认仅预览删除计划。"""
    engine = ir_engine
    if engine is None:
        settings = get_settings()
        engine = create_engine(
            settings.database.url.replace("+aiomysql", "+pymysql"),
            pool_pre_ping=True,
        )
    columns = ", ".join(f"`{label}`" for label in GRID_LABELS)
    select_sql = text(
        f"SELECT station_name, date, {columns} FROM ir_spot_price "
        "WHERE area=:area AND price_type=:price_type ORDER BY date, station_name"
    )
    delete_sql = text(
        "DELETE FROM ir_spot_price WHERE area=:area AND station_name=:station_name "
        "AND price_type=:price_type AND date=:date"
    )
    report = ShanxiDeduplicationReport()
    by_base: dict[str, dict[str, dict[date, tuple[Decimal, ...]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    with engine.connect() as conn:
        rows = conn.execution_options(stream_results=True).execute(
            select_sql, {"area": "山西", "price_type": price_type}
        )
        for row in rows:
            report.rows_seen += 1
            business_date = _parse_date(row[1])
            station = str(row[0] or "").strip()
            base = bus_base_name(station)
            prices = tuple(_to_decimal(value) for value in row[2:])
            if (
                business_date is not None
                and base is not None
                and all(value is not None for value in prices)
            ):
                by_base[base][station][business_date] = prices

    deleted_stations: set[str] = set()
    deletions: list[dict] = []
    for base, stations in by_base.items():
        names = sorted(stations, key=_natural_name_key)
        candidates: list[tuple[int, str, str]] = []
        for duplicate in names:
            duplicate_days = stations[duplicate]
            for keeper in names:
                if duplicate == keeper:
                    continue
                keeper_days = stations[keeper]
                if len(keeper_days) < len(duplicate_days):
                    continue
                if (
                    len(keeper_days) == len(duplicate_days)
                    and _natural_name_key(keeper) >= _natural_name_key(duplicate)
                ):
                    continue
                if all(
                    keeper_days.get(day) == prices
                    for day, prices in duplicate_days.items()
                ):
                    candidates.append((len(duplicate_days), duplicate, keeper))
                    break
        if not candidates:
            continue
        report.candidate_groups += 1
        for _, duplicate, keeper in sorted(candidates):
            if duplicate in deleted_stations or keeper in deleted_stations:
                continue
            deleted_stations.add(duplicate)
            report.duplicate_stations += 1
            for business_date in stations[duplicate]:
                deletions.append({
                    "area": "山西",
                    "station_name": duplicate,
                    "price_type": price_type,
                    "date": business_date,
                })
                report.duplicate_rows += 1
            if len(report.examples) < example_limit:
                report.examples.append(
                    f"{base}:{duplicate} ({len(stations[duplicate])}天) -> "
                    f"{keeper} ({len(stations[keeper])}天)"
                )

    if not dry_run and deletions:
        with engine.begin() as conn:
            result = conn.execute(delete_sql, deletions)
            report.deleted_rows = (
                result.rowcount if result.rowcount is not None and result.rowcount >= 0
                else len(deletions)
            )
    return report


@dataclass
class ShanxiLowCompleteDayReport:
    rows_seen: int = 0
    stations_seen: int = 0
    complete_days_seen: int = 0
    candidate_stations: int = 0
    candidate_complete_days: int = 0
    candidate_rows: int = 0
    deleted_rows: int = 0
    examples: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "rows_seen": self.rows_seen,
            "stations_seen": self.stations_seen,
            "complete_days_seen": self.complete_days_seen,
            "candidate_stations": self.candidate_stations,
            "candidate_complete_days": self.candidate_complete_days,
            "candidate_rows": self.candidate_rows,
            "deleted_rows": self.deleted_rows,
            "examples": list(self.examples),
        }


def remove_low_complete_day_shanxi_stations(
    *,
    ir_engine: Engine | None = None,
    price_type: int = 1,
    max_complete_days: int = 30,
    dry_run: bool = True,
    example_limit: int | None = None,
) -> ShanxiLowCompleteDayReport:
    """删除完整 96 点业务日不超过阈值的山西节点，默认仅预览。"""
    engine = ir_engine
    if engine is None:
        settings = get_settings()
        engine = create_engine(
            settings.database.url.replace("+aiomysql", "+pymysql"),
            pool_pre_ping=True,
        )
    columns = ", ".join(f"`{label}`" for label in GRID_LABELS)
    select_sql = text(
        f"SELECT station_name, {columns} FROM ir_spot_price "
        "WHERE area=:area AND price_type=:price_type ORDER BY station_name, date"
    )
    delete_sql = text(
        "DELETE FROM ir_spot_price WHERE area=:area AND station_name=:station_name "
        "AND price_type=:price_type"
    )
    report = ShanxiLowCompleteDayReport()
    station_rows: dict[str, int] = defaultdict(int)
    station_complete_days: dict[str, int] = defaultdict(int)
    with engine.connect() as conn:
        rows = conn.execution_options(stream_results=True).execute(
            select_sql, {"area": "山西", "price_type": price_type}
        )
        for row in rows:
            station = str(row[0] or "").strip()
            if not station:
                continue
            report.rows_seen += 1
            station_rows[station] += 1
            prices = tuple(_to_decimal(value) for value in row[1:])
            if len(prices) == len(GRID_LABELS) and all(
                value is not None for value in prices
            ):
                station_complete_days[station] += 1
                report.complete_days_seen += 1

    report.stations_seen = len(station_rows)
    candidates = [
        (station, station_complete_days[station], row_count)
        for station, row_count in station_rows.items()
        if station_complete_days[station] <= max_complete_days
    ]
    candidates.sort(key=lambda item: (_natural_name_key(item[0]), item[1]))
    report.candidate_stations = len(candidates)
    report.candidate_complete_days = sum(item[1] for item in candidates)
    report.candidate_rows = sum(item[2] for item in candidates)
    details = [
        f"{station}:完整日={complete_days},总行数={row_count}"
        for station, complete_days, row_count in candidates
    ]
    report.examples.extend(details if example_limit is None else details[:example_limit])

    if not dry_run and candidates:
        deletions = [
            {
                "area": "山西",
                "station_name": station,
                "price_type": price_type,
            }
            for station, _, _ in candidates
        ]
        with engine.begin() as conn:
            result = conn.execute(delete_sql, deletions)
            report.deleted_rows = (
                result.rowcount
                if result.rowcount is not None and result.rowcount >= 0
                else report.candidate_rows
            )
    return report


def _upsert_sql(dialect: str) -> str:
    columns = ["area", "station_name", "price_type", "date", *GRID_LABELS]
    names = ", ".join(f"`{column}`" for column in columns)
    values = ", ".join(f":v{i}" for i in range(len(columns)))
    if dialect == "sqlite":
        update = ", ".join(f"`{column}`=excluded.`{column}`" for column in GRID_LABELS)
        return f"INSERT INTO ir_spot_price ({names}) VALUES ({values}) ON CONFLICT (area, station_name, price_type, date) DO UPDATE SET {update}"
    update = ", ".join(f"`{column}`=VALUES(`{column}`)" for column in GRID_LABELS)
    return f"INSERT INTO ir_spot_price ({names}) VALUES ({values}) ON DUPLICATE KEY UPDATE {update}"


def import_shanxi_directory(
    directory: str | Path,
    *,
    ir_engine: Engine | None = None,
    price_type: int = 1,
    dry_run: bool = True,
    files: Iterable[str | Path] | None = None,
    year: int | None = None,
) -> ShanxiImportReport:
    directory = Path(directory)
    paths = [Path(item) for item in files] if files is not None else sorted(directory.rglob("*.xlsx"))
    report = ShanxiImportReport()
    engine = ir_engine
    if engine is None and not dry_run:
        settings = get_settings()
        engine = create_engine(settings.database.url.replace("+aiomysql", "+pymysql"), pool_pre_ping=True)
    statement = None
    for path in paths:
        report.files_seen += 1
        try:
            valid = parse_shanxi_file(path, report, year=year)
            if not dry_run and valid:
                with engine.begin() as conn:
                    if statement is None:
                        statement = text(_upsert_sql(conn.dialect.name))
                    for (business_date, station), prices in valid.items():
                        values = {"v0": "山西", "v1": station, "v2": price_type, "v3": business_date}
                        values.update({f"v{i + 4}": str(price) for i, price in enumerate(prices)})
                        conn.execute(statement, values)
                report.written_rows += len(valid)
        except ShanxiImportError as error:
            report.files_failed += 1
            report.errors.append(str(error))
    if not dry_run and report.written_rows:
        deduplication = deduplicate_shanxi_spot_prices(
            ir_engine=engine,
            price_type=price_type,
            dry_run=False,
            example_limit=20,
        )
        report.duplicate_node_days = deduplication.deleted_rows
        report.duplicate_node_day_details.extend(deduplication.examples)
        low_days = remove_low_complete_day_shanxi_stations(
            ir_engine=engine,
            price_type=price_type,
            max_complete_days=30,
            dry_run=False,
            example_limit=20,
        )
        report.low_complete_day_stations = low_days.candidate_stations
        report.low_complete_day_rows = low_days.deleted_rows
        report.low_complete_day_details.extend(low_days.examples)
    return report
