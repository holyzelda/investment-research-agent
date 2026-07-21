# 联络线功率宽表实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 MySQL 手工 DDL 中新增与 Excel 时段列完全一致的 `ir_tie_line_power` 宽表，用于后续存储联络线功率时序数据。

**Architecture:** 仅在 `agent-backend/sql/ir_agent_schema.sql` 的联络线静态表之后定义独立宽表。表保留 Excel 的 `00:15` 至 `24:00` 原始列名，且为每个时段提供 MW 备注；不创建外键、ORM、API、服务或导入逻辑。

**Tech Stack:** MySQL 8、InnoDB、utf8mb4、pytest、Python 3.12。

---

## 文件结构

- 修改：`agent-backend/sql/ir_agent_schema.sql`
  - 在 `ir_tie_line_map` 之后新增 `ir_tie_line_power` 建表语句、96 个时段功率列的备注及三个普通索引。
- 创建：`agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py`
  - 静态解析 DDL，验证表字段、时段列名/顺序/类型/备注、索引及无外键约束。

### Task 1: 添加 DDL 结构测试

**Files:**
- Create: `agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py`

- [ ] **Step 1: 创建失败的 DDL 结构测试**

新建 `agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py`，以正则从 DDL 中提取 `ir_tie_line_power` 的表体，并验证 96 个时段列、备注和索引：

```python
"""联络线功率宽表 DDL 结构测试。"""
from pathlib import Path
import re


_DDL_PATH = Path(__file__).resolve().parents[3] / "sql" / "ir_agent_schema.sql"
_EXPECTED_TIME_COLUMNS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in (15, 30, 45)
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
    assert "UNIQUE" not in _power_table_ddl()
```

- [ ] **Step 2: 运行测试，确认因为表尚未定义而失败**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_ddl.py', '-q']))"
```

Expected: FAIL，错误包含“未找到 ir_tie_line_power 建表语句”。

### Task 2: 创建 Excel 宽表 DDL

**Files:**
- Modify: `agent-backend/sql/ir_agent_schema.sql:80-104`
- Test: `agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py`

- [ ] **Step 1: 在 `ir_tie_line_map` 后新增宽表字段和索引**

在 `agent-backend/sql/ir_agent_schema.sql` 中的以下现有索引之后：

```sql
CREATE INDEX ix_ir_tie_line_map_name ON ir_tie_line_map (name);
```

并在 `CREATE TABLE ir_report_snapshot` 之前，增加以下表定义。中间时段列按照给定模式逐一完整写出，不能使用 SQL 注释、占位符或动态 SQL：

```sql
CREATE TABLE ir_tie_line_power (
    line_id BIGINT COMMENT '匹配 ir_tie_line_map 的线路 ID，无外键约束',
    data_date DATE NOT NULL COMMENT 'Excel 日期',
    line_name VARCHAR(128) NOT NULL COMMENT 'Excel 名称',
    voltage_text VARCHAR(64) NOT NULL COMMENT 'Excel 电压等级',
    `00:15` DECIMAL(12,3) COMMENT '00:15 时段功率，单位：MW',
    `00:30` DECIMAL(12,3) COMMENT '00:30 时段功率，单位：MW',
    `00:45` DECIMAL(12,3) COMMENT '00:45 时段功率，单位：MW',
    `01:15` DECIMAL(12,3) COMMENT '01:15 时段功率，单位：MW',
    `01:30` DECIMAL(12,3) COMMENT '01:30 时段功率，单位：MW',
    `01:45` DECIMAL(12,3) COMMENT '01:45 时段功率，单位：MW',
    `02:15` DECIMAL(12,3) COMMENT '02:15 时段功率，单位：MW',
    `02:30` DECIMAL(12,3) COMMENT '02:30 时段功率，单位：MW',
    `02:45` DECIMAL(12,3) COMMENT '02:45 时段功率，单位：MW',
    `03:15` DECIMAL(12,3) COMMENT '03:15 时段功率，单位：MW',
    `03:30` DECIMAL(12,3) COMMENT '03:30 时段功率，单位：MW',
    `03:45` DECIMAL(12,3) COMMENT '03:45 时段功率，单位：MW',
    `04:15` DECIMAL(12,3) COMMENT '04:15 时段功率，单位：MW',
    `04:30` DECIMAL(12,3) COMMENT '04:30 时段功率，单位：MW',
    `04:45` DECIMAL(12,3) COMMENT '04:45 时段功率，单位：MW',
    `05:15` DECIMAL(12,3) COMMENT '05:15 时段功率，单位：MW',
    `05:30` DECIMAL(12,3) COMMENT '05:30 时段功率，单位：MW',
    `05:45` DECIMAL(12,3) COMMENT '05:45 时段功率，单位：MW',
    `06:15` DECIMAL(12,3) COMMENT '06:15 时段功率，单位：MW',
    `06:30` DECIMAL(12,3) COMMENT '06:30 时段功率，单位：MW',
    `06:45` DECIMAL(12,3) COMMENT '06:45 时段功率，单位：MW',
    `07:15` DECIMAL(12,3) COMMENT '07:15 时段功率，单位：MW',
    `07:30` DECIMAL(12,3) COMMENT '07:30 时段功率，单位：MW',
    `07:45` DECIMAL(12,3) COMMENT '07:45 时段功率，单位：MW',
    `08:15` DECIMAL(12,3) COMMENT '08:15 时段功率，单位：MW',
    `08:30` DECIMAL(12,3) COMMENT '08:30 时段功率，单位：MW',
    `08:45` DECIMAL(12,3) COMMENT '08:45 时段功率，单位：MW',
    `09:15` DECIMAL(12,3) COMMENT '09:15 时段功率，单位：MW',
    `09:30` DECIMAL(12,3) COMMENT '09:30 时段功率，单位：MW',
    `09:45` DECIMAL(12,3) COMMENT '09:45 时段功率，单位：MW',
    `10:15` DECIMAL(12,3) COMMENT '10:15 时段功率，单位：MW',
    `10:30` DECIMAL(12,3) COMMENT '10:30 时段功率，单位：MW',
    `10:45` DECIMAL(12,3) COMMENT '10:45 时段功率，单位：MW',
    `11:15` DECIMAL(12,3) COMMENT '11:15 时段功率，单位：MW',
    `11:30` DECIMAL(12,3) COMMENT '11:30 时段功率，单位：MW',
    `11:45` DECIMAL(12,3) COMMENT '11:45 时段功率，单位：MW',
    `12:15` DECIMAL(12,3) COMMENT '12:15 时段功率，单位：MW',
    `12:30` DECIMAL(12,3) COMMENT '12:30 时段功率，单位：MW',
    `12:45` DECIMAL(12,3) COMMENT '12:45 时段功率，单位：MW',
    `13:15` DECIMAL(12,3) COMMENT '13:15 时段功率，单位：MW',
    `13:30` DECIMAL(12,3) COMMENT '13:30 时段功率，单位：MW',
    `13:45` DECIMAL(12,3) COMMENT '13:45 时段功率，单位：MW',
    `14:15` DECIMAL(12,3) COMMENT '14:15 时段功率，单位：MW',
    `14:30` DECIMAL(12,3) COMMENT '14:30 时段功率，单位：MW',
    `14:45` DECIMAL(12,3) COMMENT '14:45 时段功率，单位：MW',
    `15:15` DECIMAL(12,3) COMMENT '15:15 时段功率，单位：MW',
    `15:30` DECIMAL(12,3) COMMENT '15:30 时段功率，单位：MW',
    `15:45` DECIMAL(12,3) COMMENT '15:45 时段功率，单位：MW',
    `16:15` DECIMAL(12,3) COMMENT '16:15 时段功率，单位：MW',
    `16:30` DECIMAL(12,3) COMMENT '16:30 时段功率，单位：MW',
    `16:45` DECIMAL(12,3) COMMENT '16:45 时段功率，单位：MW',
    `17:15` DECIMAL(12,3) COMMENT '17:15 时段功率，单位：MW',
    `17:30` DECIMAL(12,3) COMMENT '17:30 时段功率，单位：MW',
    `17:45` DECIMAL(12,3) COMMENT '17:45 时段功率，单位：MW',
    `18:15` DECIMAL(12,3) COMMENT '18:15 时段功率，单位：MW',
    `18:30` DECIMAL(12,3) COMMENT '18:30 时段功率，单位：MW',
    `18:45` DECIMAL(12,3) COMMENT '18:45 时段功率，单位：MW',
    `19:15` DECIMAL(12,3) COMMENT '19:15 时段功率，单位：MW',
    `19:30` DECIMAL(12,3) COMMENT '19:30 时段功率，单位：MW',
    `19:45` DECIMAL(12,3) COMMENT '19:45 时段功率，单位：MW',
    `20:15` DECIMAL(12,3) COMMENT '20:15 时段功率，单位：MW',
    `20:30` DECIMAL(12,3) COMMENT '20:30 时段功率，单位：MW',
    `20:45` DECIMAL(12,3) COMMENT '20:45 时段功率，单位：MW',
    `21:15` DECIMAL(12,3) COMMENT '21:15 时段功率，单位：MW',
    `21:30` DECIMAL(12,3) COMMENT '21:30 时段功率，单位：MW',
    `21:45` DECIMAL(12,3) COMMENT '21:45 时段功率，单位：MW',
    `22:15` DECIMAL(12,3) COMMENT '22:15 时段功率，单位：MW',
    `22:30` DECIMAL(12,3) COMMENT '22:30 时段功率，单位：MW',
    `22:45` DECIMAL(12,3) COMMENT '22:45 时段功率，单位：MW',
    `23:15` DECIMAL(12,3) COMMENT '23:15 时段功率，单位：MW',
    `23:30` DECIMAL(12,3) COMMENT '23:30 时段功率，单位：MW',
    `23:45` DECIMAL(12,3) COMMENT '23:45 时段功率，单位：MW',
    `24:00` DECIMAL(12,3) COMMENT '24:00 时段功率，单位：MW',
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '功率时序记录主键',
    created_at DATETIME NOT NULL DEFAULT now() COMMENT '记录创建时间',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='联络线功率宽表，时段列与 Excel 保持一致';
CREATE INDEX ix_ir_tie_line_power_line_id_date ON ir_tie_line_power (line_id, data_date);
CREATE INDEX ix_ir_tie_line_power_name_voltage_date ON ir_tie_line_power (line_name, voltage_text, data_date);
CREATE INDEX ix_ir_tie_line_power_data_date ON ir_tie_line_power (data_date);
```

该建表语句不包含 `FOREIGN KEY`、`UNIQUE` 或其他关联约束。

- [ ] **Step 2: 运行 DDL 结构测试，确认通过**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_ddl.py', '-q']))"
```

Expected: PASS，2 passed。

- [ ] **Step 3: 运行现有联络线端点回归测试**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/', 'tests/unit/tie_line_map/test_tie_line_power_ddl.py', 'tests/unit/test_architecture_layout.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS，现有联络线 API 测试、架构布局测试和新增 DDL 结构测试全部通过。

- [ ] **Step 4: 检查变更范围**

Run:

```bash
git diff --check -- agent-backend/sql/ir_agent_schema.sql agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py
git diff -- agent-backend/sql/ir_agent_schema.sql agent-backend/tests/unit/tie_line_map/test_tie_line_power_ddl.py
```

Expected: `git diff --check` 无输出；差异仅包含宽表 DDL 及其结构测试。项目约束禁止未经用户明确要求执行 `git add`、`git commit` 或 `git push`。

## 实施后验收

- [ ] `ir_tie_line_power` 包含 `00:15` 到 `24:00` 共 96 个时段数据库列，每列均为可空 `DECIMAL(12,3)`，备注为对应“HH:MM 时段功率，单位：MW”。
- [ ] `id` 是自增主键；`line_id` 保持可空普通字段，且 DDL 不含 `FOREIGN KEY(line_id)`。
- [ ] DDL 含三个预定普通索引，不含唯一约束。
- [ ] 未修改 ORM、API、服务层、前端、Excel 文件或真实数据库。
