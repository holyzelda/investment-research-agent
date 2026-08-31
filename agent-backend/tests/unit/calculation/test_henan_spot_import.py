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


def _write_daily_workbook(path, headers, rows):
    _book(path, headers, rows)


def test_parse_daily_region_workbook_returns_five_curves(tmp_path):
    """逐日分区实时文件：4 区域 + 省级用户侧综合出清价，各展开 96 点。"""
    path = tmp_path / "2026-01-01日（实际）实时出清电价.xlsx"
    headers = ["序号", "时刻点", "豫中东", "豫南", "豫西", "豫北", "用户侧综合出清价"]
    rows = [[f"{h}", f"{h}:00", float(h) * 10, float(h) * 20, float(h) * 30, float(h) * 40, float(h) * 50]
            for h in range(1, 25)]
    _write_daily_workbook(path, headers, rows)

    parsed = parse_henan_file(path)

    assert set(parsed) == {
        ("豫中东", date(2026, 1, 1)),
        ("豫南", date(2026, 1, 1)),
        ("豫西", date(2026, 1, 1)),
        ("豫北", date(2026, 1, 1)),
        ("河南", date(2026, 1, 1)),
    }
    jd = parsed[("豫中东", date(2026, 1, 1))]
    assert len(jd) == 96
    assert jd[:4] == [Decimal("10")] * 4  # 1 点→10
    assert jd[4:8] == [Decimal("20")] * 4  # 2 点→20
    province = parsed[("河南", date(2026, 1, 1))]
    assert province[:4] == [Decimal("50")] * 4


def test_parse_daily_region_workbook_handles_company_suffix(tmp_path):
    """文件名带“（实际）实时出清电价”与多余空格也能解析日期。"""
    path = tmp_path / "2026-03-10日（实际）实时出清电价  (1).xlsx"
    headers = ["序号", "时刻点", "豫中东", "豫南", "豫西", "豫北", "用户侧综合出清价"]
    rows = [[str(h), f"{h}:00", h, h, h, h, h] for h in range(1, 25)]
    _write_daily_workbook(path, headers, rows)
    parsed = parse_henan_file(path)
    assert ("河南", date(2026, 3, 10)) in parsed
    assert len(parsed) == 5


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