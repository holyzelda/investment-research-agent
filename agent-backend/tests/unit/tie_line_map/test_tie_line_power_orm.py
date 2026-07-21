"""联络线功率宽表 ORM 结构测试。"""
from sqlalchemy import BigInteger, Date, DateTime, Numeric, String

from app.modules.tie_line_map.infrastructure.persistence.orm import TieLinePowerORM


_EXPECTED_TIME_COLUMNS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in (15, 30, 45)
] + [f"{hour:02d}:00" for hour in range(1, 24)] + ["24:00"]
_EXPECTED_TIME_COLUMNS.sort(
    key=lambda value: (24 if value == "24:00" else int(value[:2]), int(value[3:]))
)


def test_tie_line_power_orm_maps_all_excel_columns_and_business_unique_index():
    table = TieLinePowerORM.__table__

    assert table.name == "ir_tie_line_power"
    assert list(table.primary_key.columns.keys()) == ["id"]
    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.line_id.nullable is True
    assert isinstance(table.c.data_date.type, Date)
    assert isinstance(table.c.line_name.type, String)
    assert table.c.line_name.type.length == 128
    assert isinstance(table.c.voltage_text.type, String)
    assert table.c.voltage_text.type.length == 64
    assert isinstance(table.c.created_at.type, DateTime)

    actual_time_columns = [column.name for column in table.c if ":" in column.name]
    assert actual_time_columns == _EXPECTED_TIME_COLUMNS
    for name in _EXPECTED_TIME_COLUMNS:
        column = table.c[name]
        assert isinstance(column.type, Numeric)
        assert (column.type.precision, column.type.scale) == (12, 3)
        assert column.nullable is True

    indexes = {
        index.name: (index.unique, tuple(column.name for column in index.columns))
        for index in table.indexes
    }
    assert indexes["uk_ir_tie_line_power_date_name_voltage"] == (
        True,
        ("data_date", "line_name", "voltage_text"),
    )
    assert table.foreign_keys == set()
