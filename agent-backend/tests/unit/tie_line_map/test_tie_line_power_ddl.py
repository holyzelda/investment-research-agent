"""联络线功率宽表 DDL 结构测试。"""
from pathlib import Path
import re


_DDL_PATH = Path(__file__).resolve().parents[3] / "sql" / "ir_agent_schema.sql"
_EXPECTED_TIME_COLUMNS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in (0, 15, 30, 45)
    if not (hour == 0 and minute == 0)
] + ["24:00"]


def _power_table_ddl() -> str:
    ddl = _DDL_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE ir_tie_line_power \((.*?)\) ENGINE=InnoDB",
        ddl,
        flags=re.DOTALL,
    )
    assert match, "未找到 ir_tie_line_power 建表语句"
    return match.group(1)


def test_tie_line_power_ddl_preserves_excel_time_columns_and_comments():
    table_ddl = _power_table_ddl()
    actual_time_columns = re.findall(r"`(\d{2}:\d{2})` DECIMAL\(12,3\)", table_ddl)

    assert actual_time_columns == _EXPECTED_TIME_COLUMNS
    assert "id BIGINT NOT NULL AUTO_INCREMENT COMMENT '功率时序记录主键'" in table_ddl
    assert "line_id BIGINT COMMENT '匹配 ir_tie_line_map 的线路 ID，无外键约束'" in table_ddl
    assert "data_date DATE NOT NULL COMMENT 'Excel 日期'" in table_ddl
    assert "line_name VARCHAR(128) NOT NULL COMMENT 'Excel 名称'" in table_ddl
    assert "voltage_text VARCHAR(64) NOT NULL COMMENT 'Excel 电压等级'" in table_ddl

    for time_column in _EXPECTED_TIME_COLUMNS:
        assert (
            f"`{time_column}` DECIMAL(12,3) "
            f"COMMENT '{time_column} 时段功率，单位：MW'"
        ) in table_ddl


def test_tie_line_power_ddl_uses_required_indexes_without_foreign_or_unique_key():
    ddl = _DDL_PATH.read_text(encoding="utf-8")

    assert "CREATE INDEX ix_ir_tie_line_power_line_id_date ON ir_tie_line_power (line_id, data_date);" in ddl
    assert "CREATE INDEX ix_ir_tie_line_power_name_voltage_date ON ir_tie_line_power (line_name, voltage_text, data_date);" in ddl
    assert "CREATE INDEX ix_ir_tie_line_power_data_date ON ir_tie_line_power (data_date);" in ddl
    assert "FOREIGN KEY(line_id)" not in _power_table_ddl()
    assert (
        "UNIQUE KEY uk_ir_tie_line_power_date_name_voltage "
        "(data_date, line_name, voltage_text)" in _power_table_ddl()
    )
