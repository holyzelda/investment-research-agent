from datetime import date
from decimal import Decimal

from openpyxl import Workbook

from app.modules.calculation.infrastructure.henan_spot_import import (
    city_to_region,
    expand_hourly_prices,
    parse_hour,
    parse_henan_file,
)


def _book(path, headers, rows):
    book = Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    book.save(path)


def test_city_to_region_normalizes_henan_names():
    assert city_to_region("河南省郑州市") == "豫中东"
    assert city_to_region("洛阳") == "豫西"
    assert city_to_region("不存在") is None
    try:
        city_to_region("不存在", strict=True)
    except ValueError:
        pass
    else:
        raise AssertionError("strict unknown city should fail")


def test_parse_hour_accepts_clock_and_one_based_labels():
    assert parse_hour("00:00") == 0
    assert parse_hour("1时") == 0
    assert parse_hour("第24小时") == 23
    assert parse_hour("24:00") == 23
    assert parse_hour("25时") is None


def test_expand_hourly_prices_copies_each_value_four_times():
    result = expand_hourly_prices(range(24))
    assert result is not None
    assert len(result) == 96
    assert result[:8] == [Decimal("0")] * 4 + [Decimal("1")] * 4
    assert result[-4:] == [Decimal("23")] * 4
    assert expand_hourly_prices([1] * 23) is None
    assert expand_hourly_prices([1] * 23 + ["bad"]) is None


def test_parse_henan_wide_24_hour_workbook_expands_without_scaling(tmp_path):
    path = tmp_path / "henan.xlsx"
    headers = ["城市", "日期", *[f"{hour}时" for hour in range(1, 25)]]
    _book(path, headers, [["郑州市", date(2026, 7, 1), *range(1, 25)]])
    parsed = parse_henan_file(path)
    prices = parsed[(date(2026, 7, 1), "郑州市")]
    assert len(prices) == 96
    assert prices[:4] == [Decimal("1")] * 4
    assert prices[4:8] == [Decimal("2")] * 4
    assert prices[-4:] == [Decimal("24")] * 4


def test_parse_henan_long_hourly_workbook_rejects_incomplete_day(tmp_path):
    path = tmp_path / "henan-long.xlsx"
    rows = [["洛阳市", date(2026, 7, 2), hour, str(hour)] for hour in range(1, 24)]
    _book(path, ["地市", "业务日期", "小时", "出清价格"], rows)
    report = None
    parsed = parse_henan_file(path, report)
    assert parsed == {}
