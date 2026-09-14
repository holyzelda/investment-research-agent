"""上传现货电价的解析、校验与 19 个业务 K 聚合。"""
from __future__ import annotations

import hashlib
import io
import multiprocessing
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from zipfile import BadZipFile

from openpyxl import load_workbook

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.spot_pricing import (
    PRECOMPUTE_K_VALUES,
    day_optimal_by_k,
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ROWS = 1_000_000
MAX_DATE_SPAN_DAYS = 366
PRICE_UNIT = "CNY/MWh"
ALGORITHM_VERSION = "spot-dp-v1"
EXPECTED_HEADERS = ("日期", "时点", "电价（元/MWh）")
DATA_SHEET_NAME = "现货电价"
INSTRUCTION_SHEET_NAME = "填写说明"
_GRID_LABELS = {
    f"{(index * 15) // 60:02d}:{(index * 15) % 60:02d}"
    for index in range(1, 97)
}


@dataclass(frozen=True)
class ParsedSpotContext:
    file_name: str
    file_sha256: str
    start_date: date
    end_date: date
    valid_day_count: int
    skipped_day_count: int
    warnings: list[str]
    k_results: dict[str, dict[str, Any]]


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: object) -> str | None:
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        if value.second or value.microsecond:
            return None
        if value.hour == 0 and value.minute == 0:
            return "24:00"
        label = f"{value.hour:02d}:{value.minute:02d}"
        return label if label in _GRID_LABELS else None
    if isinstance(value, (int, float)) and 0 <= value <= 1:
        minutes = round(float(value) * 24 * 60)
        if minutes % 15 == 0 and 0 < minutes <= 24 * 60:
            return f"{minutes // 60:02d}:{minutes % 60:02d}"
        return None
    text = str(value or "").strip()
    if text in {"24:00", "24:00:00"}:
        return "24:00"
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt).time()
        except ValueError:
            continue
        if parsed.second:
            return None
        label = f"{parsed.hour:02d}:{parsed.minute:02d}"
        return label if label in _GRID_LABELS else None
    return None


def _parse_price(value: object) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _error(message: str) -> ValidationException:
    return ValidationException(f"电价文件校验失败：{message}")


def _compute_day(prices: list[str], min_action_minutes: int, switch_gap_minutes: int):
    result = day_optimal_by_k(
        [Decimal(value) for value in prices],
        k_values=PRECOMPUTE_K_VALUES,
        min_action_minutes=min_action_minutes,
        switch_gap_minutes=switch_gap_minutes,
    )
    return {
        k: (str(charge_sum), str(discharge_sum), slot_count)
        for k, (charge_sum, discharge_sum, slot_count) in result.items()
    }


def _compute_day_from_tuple(args):
    return _compute_day(*args)


def _aggregate_days(
    valid_days: dict[date, list[Decimal]],
    *,
    min_action_minutes: int,
    switch_gap_minutes: int,
    workers: int | None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, dict[str, Any]]:
    aggregate = {
        str(k): {"chargeSum": Decimal(0), "dischargeSum": Decimal(0), "slotCount": 0}
        for k in PRECOMPUTE_K_VALUES
    }
    inputs = [
        ([str(price) for price in prices], min_action_minutes, switch_gap_minutes)
        for prices in valid_days.values()
    ]
    worker_count = workers if workers is not None else min(8, os.cpu_count() or 1)
    worker_count = max(1, min(worker_count, len(inputs)))
    executor = None
    if worker_count == 1:
        results = (_compute_day(*item) for item in inputs)
    else:
        executor = ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        )
        results = executor.map(_compute_day_from_tuple, inputs)
    try:
        completed_days = 0
        total_days = len(inputs)
        for by_k in results:
            for k, (charge_sum, discharge_sum, slot_count) in by_k.items():
                item = aggregate[str(k)]
                item["chargeSum"] += Decimal(charge_sum)
                item["dischargeSum"] += Decimal(discharge_sum)
                item["slotCount"] += slot_count
            completed_days += 1
            if progress_callback is not None:
                progress_callback(completed_days, total_days)
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    return {
        key: {
            "chargeSum": str(value["chargeSum"]),
            "dischargeSum": str(value["dischargeSum"]),
            "slotCount": value["slotCount"],
        }
        for key, value in aggregate.items()
    }


def parse_uploaded_spot_file(
    content: bytes,
    filename: str,
    *,
    min_action_minutes: int = 30,
    switch_gap_minutes: int = 15,
    workers: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ParsedSpotContext:
    """解析标准长表，并在返回前完成全部 19 个 K 的 DP 聚合。"""
    if not filename or not filename.lower().endswith(".xlsx"):
        raise _error("仅支持 .xlsx 文件")
    if not content:
        raise _error("文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise _error(f"文件不能超过 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (BadZipFile, OSError, ValueError) as exc:
        raise _error("Excel 文件无法打开") from exc

    try:
        if progress_callback is not None:
            progress_callback({"phase": "validating", "message": "正在读取并校验 Excel 数据"})
        sheet_names = workbook.sheetnames
        if DATA_SHEET_NAME in sheet_names:
            unexpected_sheets = [
                name for name in sheet_names
                if name not in {DATA_SHEET_NAME, INSTRUCTION_SHEET_NAME}
            ]
            if unexpected_sheets:
                raise _error("除现货电价和填写说明外，不能包含其他工作表")
            sheet = workbook[DATA_SHEET_NAME]
        elif len(sheet_names) == 1:
            # 兼容本功能上线前生成的单工作表模板和用户已有文件。
            sheet = workbook.active
        else:
            raise _error("包含多个工作表时，数据工作表必须命名为“现货电价”")
        rows = sheet.iter_rows(values_only=True)
        headers = tuple(str(value or "").strip() for value in (next(rows, None) or ()))
        if headers != EXPECTED_HEADERS:
            expected = "、".join(EXPECTED_HEADERS)
            raise _error(f"表头不匹配，必须为：{expected}")

        by_day: dict[date, dict[str, Decimal]] = defaultdict(dict)
        invalid_days: set[date] = set()
        malformed_rows: list[str] = []
        row_count = 1
        for row_number, row in enumerate(rows, start=2):
            row_count += 1
            if row_count > MAX_ROWS:
                raise _error(f"数据行不能超过 {MAX_ROWS:,} 行")
            if not any(value not in (None, "") for value in row):
                continue
            if len(row) < 3:
                raise _error(f"第 {row_number} 行列数不足")
            business_date = _parse_date(row[0])
            if business_date is None:
                malformed_rows.append(f"第{row_number}行日期无效")
                continue
            label = _parse_time(row[1])
            price = _parse_price(row[2])
            if label is None or price is None:
                invalid_days.add(business_date)
                continue
            if label in by_day[business_date]:
                invalid_days.add(business_date)
            else:
                by_day[business_date][label] = price

        if malformed_rows:
            detail = "、".join(malformed_rows[:3])
            suffix = "等" if len(malformed_rows) > 3 else ""
            raise _error(f"{detail}{suffix}，无法识别日期")

        valid_days: dict[date, list[Decimal]] = {}
        for business_date, cells in by_day.items():
            if business_date in invalid_days or len(cells) != 96:
                invalid_days.add(business_date)
                continue
            ordered = [cells.get(
                f"{(index * 15) // 60:02d}:{(index * 15) % 60:02d}"
            ) for index in range(1, 97)]
            if any(price is None for price in ordered):
                invalid_days.add(business_date)
                continue
            valid_days[business_date] = ordered  # type: ignore[assignment]

        if not valid_days:
            raise _error("没有包含完整的 96 点有效自然日")
        first_day = min(by_day)
        last_day = max(by_day)
        if (last_day - first_day).days + 1 > MAX_DATE_SPAN_DAYS:
            raise _error(f"数据日期范围不能超过 {MAX_DATE_SPAN_DAYS} 天")

        if progress_callback is not None:
            progress_callback({
                "phase": "computing",
                "message": "正在计算不同充放电策略",
                "completedDays": 0,
                "totalDays": len(valid_days),
            })
        k_results = _aggregate_days(
            valid_days,
            min_action_minutes=min_action_minutes,
            switch_gap_minutes=switch_gap_minutes,
            workers=workers,
            progress_callback=(
                lambda completed, total: progress_callback({
                    "phase": "computing",
                    "message": "正在计算不同充放电策略",
                    "completedDays": completed,
                    "totalDays": total,
                })
                if progress_callback is not None else None
            ),
        )
        skipped_count = (last_day - first_day).days + 1 - len(valid_days)
        warnings = []
        if skipped_count:
            warnings.append(f"有{skipped_count}个自然日因时点不完整、重复或价格无效未参与计算")
        return ParsedSpotContext(
            file_name=filename[:255],
            file_sha256=hashlib.sha256(content).hexdigest(),
            start_date=first_day,
            end_date=last_day,
            valid_day_count=len(valid_days),
            skipped_day_count=skipped_count,
            warnings=warnings,
            k_results=k_results,
        )
    finally:
        workbook.close()
