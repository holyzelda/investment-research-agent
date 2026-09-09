from datetime import date
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.spot_pricing import PRECOMPUTE_K_VALUES
from app.modules.calculation.infrastructure.uploaded_spot_context import (
    parse_uploaded_spot_file,
)


def _workbook_bytes(*, complete_days=1, bad_header=False, incomplete_day=False, gap_day=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["错误"] if bad_header else ["日期", "时点", "电价（元/MWh）"])
    for day_offset in range(complete_days):
        business_date = date(2026, 1, day_offset + 1)
        if gap_day and day_offset == 1:
            continue
        slots = 95 if incomplete_day and day_offset == complete_days - 1 else 96
        for index in range(1, slots + 1):
            minutes = index * 15
            label = f"{minutes // 60:02d}:{minutes % 60:02d}"
            price = 100 if index <= 48 else 500
            sheet.append([business_date, label, price])
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_parses_complete_days_and_aggregates_exact_business_k_set():
    parsed = parse_uploaded_spot_file(
        _workbook_bytes(complete_days=1), "spot.xlsx", workers=1
    )

    assert parsed.valid_day_count == 1
    assert parsed.skipped_day_count == 0
    assert parsed.start_date == parsed.end_date == date(2026, 1, 1)
    assert set(map(int, parsed.k_results)) == set(PRECOMPUTE_K_VALUES)
    assert len(parsed.k_results) == 19
    assert parsed.k_results["8"]["slotCount"] == 8
    assert parsed.k_results["8"]["chargeSum"] == "800"
    assert parsed.k_results["8"]["dischargeSum"] == "4000"


def test_skips_incomplete_day_but_reports_warning():
    parsed = parse_uploaded_spot_file(
        _workbook_bytes(complete_days=2, incomplete_day=True),
        "spot.xlsx",
        workers=1,
    )

    assert parsed.valid_day_count == 1
    assert parsed.skipped_day_count == 1
    assert "1个自然日" in parsed.warnings[0]


def test_uses_process_pool_for_multiple_complete_days():
    parsed = parse_uploaded_spot_file(
        _workbook_bytes(complete_days=2), "spot.xlsx", workers=2
    )

    assert parsed.valid_day_count == 2
    assert len(parsed.k_results) == 19
    assert parsed.k_results["8"]["slotCount"] == 16


def test_counts_missing_calendar_days_in_skipped_days():
    parsed = parse_uploaded_spot_file(
        _workbook_bytes(complete_days=3, gap_day=True), "spot.xlsx", workers=1
    )

    assert parsed.valid_day_count == 2
    assert parsed.skipped_day_count == 1


def test_rejects_bad_header_and_file_type():
    with pytest.raises(ValidationException, match="表头不匹配"):
        parse_uploaded_spot_file(
            _workbook_bytes(bad_header=True), "spot.xlsx", workers=1
        )
    with pytest.raises(ValidationException, match="仅支持 .xlsx"):
        parse_uploaded_spot_file(b"x", "spot.csv", workers=1)
