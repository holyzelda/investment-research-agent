from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.modules.calculation.infrastructure.shanxi_spot_import import (
    ShanxiImportReport,
    bus_base_name,
    deduplicate_shanxi_spot_prices,
    import_shanxi_directory,
    normalize_station_name,
    parse_shanxi_file,
    remove_low_complete_day_shanxi_stations,
)
from app.modules.calculation.infrastructure.spot_price_repo import GRID_LABELS


HEADER = (
    "节点名称", "日期", "时点", "电能量价格（元/MWh）",
    "阻塞价格（元/MWh）", "节点电价（元/MWh）",
)
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _xlsx(path: Path, rows):
    strings = list(HEADER) + sorted({str(row[0]) for row in rows})
    indexes = {value: index for index, value in enumerate(strings)}
    xml_rows = []
    header_cells = "".join(
        f'<c r="{chr(65 + index)}1" t="s"><v>{indexes[value]}</v></c>'
        for index, value in enumerate(HEADER)
    )
    xml_rows.append(f'<row r="1">{header_cells}</row>')
    for number, row in enumerate(rows, start=2):
        cells = [f'<c r="A{number}" t="s"><v>{indexes[str(row[0])]}</v></c>']
        for index, value in enumerate(row[1:], start=1):
            cells.append(f'<c r="{chr(65 + index)}{number}" t="inlineStr"><is><t>{value}</t></is></c>')
        xml_rows.append(f'<row r="{number}">{"".join(cells)}</row>')
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", f'''<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        zf.writestr("xl/_rels/workbook.xml.rels", '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>''')
        zf.writestr("xl/sharedStrings.xml", f'''<sst xmlns="{NS}">{''.join(f'<si><t>{value}</t></si>' for value in strings)}</sst>''')
        zf.writestr("xl/worksheets/sheet1.xml", f'''<worksheet xmlns="{NS}"><dimension ref="A1"/><sheetData>{''.join(xml_rows)}</sheetData></worksheet>''')


def _rows(station="山西.恒北热电厂/500kV母线", day="2025-01-02", f="999"):
    return [(station, day, label, "1.25", "-0.25", f) for label in GRID_LABELS]


def _engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    columns = ", ".join(f'"{label}" NUMERIC' for label in GRID_LABELS)
    with engine.begin() as conn:
        conn.execute(text(f'''CREATE TABLE ir_spot_price (
            area TEXT, station_name TEXT, price_type INTEGER, date TEXT, {columns},
            PRIMARY KEY (area, station_name, price_type, date)
        )'''))
    return engine


def test_normalize_station_name_keeps_suffix():
    assert normalize_station_name(" 山西.东凌井站/220kV.A母线 ") == "东凌井站/220kV.A母线"
    assert normalize_station_name("110008136") is None


def test_bus_base_name_only_accepts_explicit_variants():
    assert bus_base_name("东凌井站/220kV.A母线") == "东凌井站/220kV"
    assert bus_base_name("北岳/500kV.II甲母线") == "北岳/500kV"
    assert bus_base_name("某站/220kV.2母线") == "某站/220kV"
    assert bus_base_name("某站/220kV.东母线") == "某站/220kV"
    assert bus_base_name("恒北热电厂/500kV母线") is None
    assert bus_base_name("某站/220kV虚拟A母线") is None


def test_parse_keeps_bus_variants_until_cross_file_comparison(tmp_path):
    path = tmp_path / "2025" / "1.02.xlsx"
    path.parent.mkdir()
    rows = _rows("山西.东凌井站/220kV.A母线", f="1")
    rows += _rows("山西.东凌井站/220kV.B母线", f="1")
    rows += _rows("山西.东凌井站/220kV.C母线", f="1")
    rows[-1] = (*rows[-1][:3], "2", "0", "2")
    _xlsx(path, rows)
    report = ShanxiImportReport()
    parsed = parse_shanxi_file(path, report)
    assert set(parsed) == {
        (date(2025, 1, 2), "东凌井站/220kV.A母线"),
        (date(2025, 1, 2), "东凌井站/220kV.B母线"),
        (date(2025, 1, 2), "东凌井站/220kV.C母线"),
    }
    assert report.duplicate_node_days == 0


def test_parse_uses_d_plus_e_and_ignores_wrong_dimension(tmp_path):
    path = tmp_path / "2025" / "1" / "1.02.xlsx"
    path.parent.mkdir(parents=True)
    _xlsx(path, _rows())
    report = ShanxiImportReport()
    parsed = parse_shanxi_file(path, report)
    assert parsed[(date(2025, 1, 2), "恒北热电厂/500kV母线")] == [Decimal("1.00")] * 96
    assert report.d_plus_e_mismatches == 96


def test_invalid_node_day_does_not_block_valid_node(tmp_path):
    path = tmp_path / "2025" / "1.02.xlsx"
    path.parent.mkdir()
    _xlsx(path, _rows("山西.完整节点") + _rows("山西.缺点节点")[:-1] + _rows("12345"))
    report = ShanxiImportReport()
    parsed = parse_shanxi_file(path, report)
    assert list(parsed) == [(date(2025, 1, 2), "完整节点")]
    assert report.invalid_node_days == 1
    assert report.numeric_nodes_skipped == 1
    assert report.numeric_rows_skipped == 96


def test_dry_run_and_upsert(tmp_path):
    paths = []
    start = date(2025, 1, 1)
    for offset in range(31):
        day = start + timedelta(days=offset)
        path = tmp_path / "2025" / f"{day.month}.{day.day:02d}.xlsx"
        path.parent.mkdir(exist_ok=True)
        _xlsx(path, _rows(day=day.isoformat(), f="1"))
        paths.append(path)
    engine = _engine()
    dry = import_shanxi_directory(tmp_path, ir_engine=engine, dry_run=True)
    assert dry.written_rows == 0
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_price")).scalar() == 0
    first = import_shanxi_directory(tmp_path, ir_engine=engine, dry_run=False)
    second = import_shanxi_directory(tmp_path, ir_engine=engine, dry_run=False)
    assert first.written_rows == second.written_rows == 31
    assert first.low_complete_day_stations == second.low_complete_day_stations == 0
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_price")).scalar() == 31
        assert conn.execute(text('SELECT "00:15" FROM ir_spot_price LIMIT 1')).scalar() == 1


def _insert_price(conn, area, station, day, price_type=1, changed_last=None):
    columns = ["area", "station_name", "price_type", "date", *GRID_LABELS]
    names = ", ".join(f'"{column}"' for column in columns)
    values = ", ".join(f":v{index}" for index in range(len(columns)))
    prices = ["1"] * 96
    if changed_last is not None:
        prices[-1] = str(changed_last)
    params = {
        "v0": area,
        "v1": station,
        "v2": price_type,
        "v3": day,
        **{f"v{index + 4}": price for index, price in enumerate(prices)},
    }
    conn.execute(text(f"INSERT INTO ir_spot_price ({names}) VALUES ({values})"), params)


def test_database_deduplication_preview_and_delete():
    engine = _engine()
    with engine.begin() as conn:
        _insert_price(conn, "山西", "东凌井站/220kV.A母线", "2025-01-01")
        _insert_price(conn, "山西", "东凌井站/220kV.A母线", "2025-01-02")
        _insert_price(conn, "山西", "东凌井站/220kV.B母线", "2025-01-02")
        _insert_price(conn, "山西", "东凌井站/220kV.C母线", "2025-01-01", changed_last=2)
        _insert_price(conn, "山西", "东凌井站/220kV.C母线", "2025-01-02")
        _insert_price(conn, "山西", "恒北热电厂/500kV母线", "2025-01-02")
        _insert_price(conn, "甘肃", "东凌井站/220kV.B母线", "2025-01-02")
        _insert_price(conn, "山西", "东凌井站/220kV.B母线", "2025-01-03", price_type=2)

    preview = deduplicate_shanxi_spot_prices(ir_engine=engine, dry_run=True)
    assert preview.candidate_groups == 1
    assert preview.duplicate_stations == 1
    assert preview.duplicate_rows == 1
    assert preview.deleted_rows == 0
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_price")).scalar() == 8

    result = deduplicate_shanxi_spot_prices(ir_engine=engine, dry_run=False)
    assert result.duplicate_stations == 1
    assert result.duplicate_rows == result.deleted_rows == 1
    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT area, station_name, price_type, date FROM ir_spot_price "
            "ORDER BY area, station_name, price_type, date"
        )).all()
    assert len(remaining) == 7
    assert ("山西", "东凌井站/220kV.B母线", 1, "2025-01-02") not in remaining
    assert ("山西", "东凌井站/220kV.C母线", 1, "2025-01-01") in remaining
    assert ("山西", "东凌井站/220kV.C母线", 1, "2025-01-02") in remaining
    assert ("甘肃", "东凌井站/220kV.B母线", 1, "2025-01-02") in remaining
    assert ("山西", "东凌井站/220kV.B母线", 2, "2025-01-03") in remaining


def test_low_complete_day_preview_and_delete():
    engine = _engine()
    start = date(2025, 1, 1)
    with engine.begin() as conn:
        for offset in range(30):
            day = (start + timedelta(days=offset)).isoformat()
            _insert_price(conn, "山西", "三十天节点", day)
        for offset in range(31):
            day = (start + timedelta(days=offset)).isoformat()
            _insert_price(conn, "山西", "三十一天节点", day)
        _insert_price(conn, "山西", "不完整节点", "2025-02-01")
        conn.execute(text(
            'UPDATE ir_spot_price SET "24:00"=NULL '
            "WHERE area='山西' AND station_name='不完整节点'"
        ))
        _insert_price(conn, "甘肃", "三十天节点", "2025-01-01")
        _insert_price(conn, "山西", "三十天节点", "2025-02-01", price_type=2)

    preview = remove_low_complete_day_shanxi_stations(
        ir_engine=engine,
        dry_run=True,
    )
    assert preview.stations_seen == 3
    assert preview.candidate_stations == 2
    assert preview.candidate_complete_days == 30
    assert preview.candidate_rows == 31
    assert preview.deleted_rows == 0
    assert set(preview.examples) == {
        "不完整节点:完整日=0,总行数=1",
        "三十天节点:完整日=30,总行数=30",
    }
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_price")).scalar() == 64

    result = remove_low_complete_day_shanxi_stations(
        ir_engine=engine,
        dry_run=False,
    )
    assert result.candidate_stations == 2
    assert result.candidate_rows == result.deleted_rows == 31
    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT area, station_name, price_type, COUNT(*) FROM ir_spot_price "
            "GROUP BY area, station_name, price_type "
            "ORDER BY area, station_name, price_type"
        )).all()
    assert set(remaining) == {
        ("山西", "三十天节点", 2, 1),
        ("山西", "三十一天节点", 1, 31),
        ("甘肃", "三十天节点", 1, 1),
    }


def test_import_filters_only_after_entire_batch(tmp_path):
    paths = []
    start = date(2025, 1, 1)
    for offset in range(31):
        day = start + timedelta(days=offset)
        path = tmp_path / "2025" / f"{day.month}.{day.day:02d}.xlsx"
        path.parent.mkdir(exist_ok=True)
        _xlsx(path, _rows("山西.批次节点", day.isoformat(), f="1"))
        paths.append(path)

    engine = _engine()
    report = import_shanxi_directory(
        tmp_path,
        ir_engine=engine,
        dry_run=False,
        files=paths,
    )
    assert report.written_rows == 31
    assert report.low_complete_day_stations == 0
    assert report.low_complete_day_rows == 0
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM ir_spot_price WHERE station_name='批次节点'"
        )).scalar() == 31


def test_import_removes_station_when_batch_has_only_thirty_days(tmp_path):
    paths = []
    start = date(2025, 1, 1)
    for offset in range(30):
        day = start + timedelta(days=offset)
        path = tmp_path / "2025" / f"{day.month}.{day.day:02d}.xlsx"
        path.parent.mkdir(exist_ok=True)
        _xlsx(path, _rows("山西.短批次节点", day.isoformat(), f="1"))
        paths.append(path)

    engine = _engine()
    report = import_shanxi_directory(
        tmp_path,
        ir_engine=engine,
        dry_run=False,
        files=paths,
    )
    assert report.written_rows == 30
    assert report.low_complete_day_stations == 1
    assert report.low_complete_day_rows == 30
    assert report.low_complete_day_details == [
        "短批次节点:完整日=30,总行数=30"
    ]
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_price")).scalar() == 0
