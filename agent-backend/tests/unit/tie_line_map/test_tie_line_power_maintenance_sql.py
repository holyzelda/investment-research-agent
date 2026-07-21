"""联络线功率去重维护脚本测试。"""
from pathlib import Path


def test_maintenance_sql_deduplicates_by_largest_id_and_creates_index_idempotently():
    sql_path = Path(__file__).resolve().parents[3] / "sql" / "maintain_tie_line_power_unique.sql"
    sql = sql_path.read_text(encoding="utf-8")

    assert "DELETE older" in sql
    assert "older.id < newer.id" in sql
    assert "older.data_date = newer.data_date" in sql
    assert "older.line_name = newer.line_name" in sql
    assert "older.voltage_text = newer.voltage_text" in sql
    assert "information_schema.statistics" in sql
    assert "uk_ir_tie_line_power_date_name_voltage" in sql
    assert "ALTER TABLE ir_tie_line_power ADD UNIQUE INDEX" in sql
