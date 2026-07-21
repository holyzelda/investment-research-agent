# 联络线功率导入接口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `POST /ir/tie-lines/power/import`，以一个路由支持 JSON 宽表记录和 Excel 文件上传，并以业务键幂等覆盖联络线功率数据。

**Architecture:** 表现层按 `Content-Type` 将 JSON 或 Excel 解析为同一组应用层导入记录。应用服务在校验全部记录和线路名称匹配后，于单一事务内删除相同业务键的旧记录并插入新记录；基础设施 ORM 映射宽表的 96 个原始时段列。独立数据库维护脚本先按最大 `id` 清理存量重复记录，再幂等创建业务唯一索引。

**Tech Stack:** FastAPI 0.115、Pydantic 2、SQLAlchemy 2 异步 ORM、MySQL 8、SQLite 测试库、openpyxl、python-multipart、pytest/httpx。

---

## 文件结构

- 修改：`agent-backend/requirements.txt`
  - 以文本依赖清单形式管理 `openpyxl` 与 `python-multipart` 的版本范围。实施前先将当前二进制文件替换为有效 UTF-8 requirements 文件，内容依据实际已用依赖锁定。
- 修改：`agent-backend/app/modules/tie_line_map/infrastructure/persistence/orm.py`
  - 新增 `TieLinePowerORM`，以合法 Python 属性映射 `ir_tie_line_power` 的 96 个原始时段列；定义业务唯一索引。
- 创建：`agent-backend/app/modules/tie_line_map/application/power_import_service.py`
  - 定义不可变导入记录 DTO、固定时段常量、字段校验、名称匹配、幂等替换与统计逻辑。
- 创建：`agent-backend/app/modules/tie_line_map/interface/power_import_parser.py`
  - 解析和验证 Excel 文件；输出应用服务导入记录。
- 修改：`agent-backend/app/modules/tie_line_map/interface/router.py`
  - 添加单一路由，以 `Content-Type` 分派 JSON/Excel 解析，调用导入服务并返回统一响应壳。
- 创建：`agent-backend/sql/maintain_tie_line_power_unique.sql`
  - 生产维护脚本：删重（保留最大 `id`）并在索引不存在时创建唯一索引。
- 创建：`agent-backend/tests/e2e/tie_line_map/test_tie_line_power_import_endpoints.py`
  - 使用 ASGITransport + 内存 SQLite 覆盖双输入格式、覆盖写入和所有 400 错误路径。
- 修改：`my_projects/联络线地图模块-功能与开发文档.md`
  - 同步功率导入 API、业务唯一键、输入格式及当前无查询/图表能力。

### Task 1: 修复后端依赖清单并新增时段列 ORM

**Files:**
- Modify: `agent-backend/requirements.txt`
- Modify: `agent-backend/app/modules/tie_line_map/infrastructure/persistence/orm.py:1-45`
- Create: `agent-backend/tests/unit/tie_line_map/test_tie_line_power_orm.py`

- [ ] **Step 1: 编写失败的 ORM 结构测试**

创建 `agent-backend/tests/unit/tie_line_map/test_tie_line_power_orm.py`：

```python
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
```

- [ ] **Step 2: 执行 ORM 测试，确认因模型未定义而失败**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_orm.py', '-q']))"
```

Expected: FAIL，包含 `cannot import name 'TieLinePowerORM'`。

- [ ] **Step 3: 将 requirements 替换为有效的 UTF-8 文本依赖清单**

当前 `agent-backend/requirements.txt` 是二进制内容，不能作为依赖管理来源。先通过实际运行环境确认核心库版本，再将整个文件写为下列兼容范围；不要把数据库密码、内网地址或其他凭据写入文件：

```text
fastapi>=0.115,<0.116
uvicorn[standard]>=0.34,<0.35
sqlalchemy>=2.0,<2.1
aiosqlite>=0.21,<0.22
asyncmy>=0.2,<0.3
pydantic>=2.13,<2.14
pydantic-settings>=2.10,<2.11
httpx>=0.28,<0.29
PyYAML>=6.0,<7.0
loguru>=0.7,<0.8
openpyxl>=3.1,<3.2
python-multipart>=0.0.20,<0.1
pytest>=8.0,<9.0
pytest-asyncio>=0.24,<0.25
```

安装或升级前遵循项目依赖规则：

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -m pip install -r requirements.txt
```

Expected: 安装成功，`import openpyxl` 和 `import multipart` 均成功。

- [ ] **Step 4: 以 96 个显式声明字段实现 ORM**

在 `orm.py` 中添加：

```python
from datetime import date, datetime
```

以及 SQLAlchemy 导入：

```python
from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, Numeric, String, Text, func
```

在 `TieLineMapORM` 后添加 `TieLinePowerORM`。不要使用类定义后的 `setattr()` 或 SQLAlchemy `column()` 动态绑定；必须在类体内用 `mapped_column("HH:MM", Numeric(12, 3), ...)` 显式声明全部 96 个属性。下方给出定义的首部与末尾，所有中间属性按同一格式完成：

```python
class TieLinePowerORM(_PkTimestamp, Base):
    """联络线功率宽表：96 个时段列与 Excel 保持一致。"""

    __tablename__ = "ir_tie_line_power"
    __table_args__ = (
        Index(
            "uk_ir_tie_line_power_date_name_voltage",
            "data_date",
            "line_name",
            "voltage_text",
            unique=True,
        ),
    )

    line_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    line_name: Mapped[str] = mapped_column(String(128), nullable=False)
    voltage_text: Mapped[str] = mapped_column(String(64), nullable=False)
    power_0015_mw: Mapped[Optional[Decimal]] = mapped_column(
        "00:15", Numeric(12, 3), nullable=True
    )
    power_0030_mw: Mapped[Optional[Decimal]] = mapped_column(
        "00:30", Numeric(12, 3), nullable=True
    )
    power_0045_mw: Mapped[Optional[Decimal]] = mapped_column(
        "00:45", Numeric(12, 3), nullable=True
    )
    power_0100_mw: Mapped[Optional[Decimal]] = mapped_column(
        "01:00", Numeric(12, 3), nullable=True
    )
    # 按相同格式显式声明 01:15 至 23:45 与 24:00，按 Excel 表头顺序排列。
    power_2400_mw: Mapped[Optional[Decimal]] = mapped_column(
        "24:00", Numeric(12, 3), nullable=True
    )
```

属性命名规则：`HH:MM` 对应 `power_HHMM_mw`；例如 `12:45` 对应 `power_1245_mw`。每一个时段字段均可空；不定义外键。

- [ ] **Step 5: 运行 ORM 结构测试，确认通过**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_orm.py', '-q']))"
```

Expected: PASS，1 passed。

### Task 2: 实现应用层导入模型与幂等覆盖服务

**Files:**
- Create: `agent-backend/app/modules/tie_line_map/application/power_import_service.py`
- Create: `agent-backend/tests/unit/tie_line_map/test_power_import_service.py`

- [ ] **Step 1: 编写失败的服务测试**

创建 `test_power_import_service.py`，使用内存 SQLite 的 `Base.metadata.create_all`，插入一个 `TieLineMapORM(name="吉泉直流", ...)`，再覆盖以下行为：

```python
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.tie_line_map.application.power_import_service import (
    PowerImportRecord,
    PowerImportService,
    POWER_TIME_COLUMNS,
)
from app.modules.tie_line_map.infrastructure.persistence.orm import (
    TieLineMapORM,
    TieLinePowerORM,
)


def _record(value: Decimal = Decimal("8799")) -> PowerImportRecord:
    return PowerImportRecord(
        data_date=date(2025, 1, 1),
        line_name="吉泉直流",
        voltage_text="±1100kV",
        powers={time: value for time in POWER_TIME_COLUMNS},
    )


@pytest.mark.asyncio
async def test_import_replaces_same_business_key_and_uses_matched_line_id():
    # 建立内存库和静态线路种子后，先导入 8799，再导入 8800。
    # 断言第二次统计 deleted_count=1、inserted_count=1、总行数仍为 1，
    # 且存储行 line_id 等于种子 id、数据库 `00:15` 为 Decimal("8800")。
    ...


@pytest.mark.asyncio
async def test_import_rejects_unknown_line_before_writing():
    # 用名称“不存在的线路”调用服务，断言 ValidationException，
    # 且 ir_tie_line_power 行数仍为 0。
    ...


def test_power_import_record_rejects_duplicate_business_keys_and_incomplete_times():
    # 调用服务的 validate_records：
    # 1) 同键两条记录抛 ValidationException；
    # 2) powers 少一个时段抛 ValidationException；
    ...
```

将 `...` 替换为完整可执行的 fixture 和断言；测试不得使用 mock。

- [ ] **Step 2: 运行服务测试，确认导入模块不存在而失败**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_power_import_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL，包含 `ModuleNotFoundError`。

- [ ] **Step 3: 实现最小的应用服务**

在 `power_import_service.py` 中定义固定时段常量，顺序必须与 Excel 一致：

```python
POWER_TIME_COLUMNS = tuple(
    f"{hour:02d}:{minute:02d}"
    for hour in range(24)
    for minute in (15, 30, 45)
) + tuple(f"{hour:02d}:00" for hour in range(1, 24)) + ("24:00",)
POWER_TIME_COLUMNS = tuple(
    sorted(
        POWER_TIME_COLUMNS,
        key=lambda value: (24 if value == "24:00" else int(value[:2]), int(value[3:])),
    )
)
```

定义不可变记录和结果：

```python
@dataclass(frozen=True)
class PowerImportRecord:
    data_date: date
    line_name: str
    voltage_text: str
    powers: Mapping[str, Decimal | None]


@dataclass(frozen=True)
class PowerImportResult:
    received_count: int
    deleted_count: int
    inserted_count: int
    matched_line_count: int
```

`PowerImportService.import_records(session, records)` 必须：

1. 调用 `validate_records(records)`，检查非空、名称/电压非空、功率键集合精确等于 `POWER_TIME_COLUMNS`、数值是有限 `Decimal` 或 `None`、同一批内业务键唯一；
2. 一次 `select(TieLineMapORM.id, TieLineMapORM.name).where(TieLineMapORM.name.in_(...))` 匹配所有名称；未匹配名称抛 `ValidationException("未匹配的联络线名称：...")`；
3. 以 `tuple_(TieLinePowerORM.data_date, TieLinePowerORM.line_name, TieLinePowerORM.voltage_text).in_(keys)` 删除旧行，并记录 `result.rowcount`；
4. 用 `session.add_all()` 插入 `TieLinePowerORM`，将每个 `powers["HH:MM"]` 显式传给对应合法属性；
5. `await session.flush()` 后返回统计。服务不调用 `commit()` 或 `rollback()`，由路由会话边界控制事务。

- [ ] **Step 4: 运行服务测试，确认通过**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_power_import_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS，3 passed。

### Task 3: 实现 Excel 解析和单路由双 Content-Type 入口

**Files:**
- Create: `agent-backend/app/modules/tie_line_map/interface/power_import_parser.py`
- Modify: `agent-backend/app/modules/tie_line_map/interface/router.py:1-32`
- Modify: `agent-backend/tests/e2e/tie_line_map/test_tie_line_power_import_endpoints.py`

- [ ] **Step 1: 编写失败的端点测试**

创建端点测试，基于既有 `test_tie_line_endpoints.py` 的 `StaticPool` / `ASGITransport` 模式，并覆盖：

```python
@pytest.mark.asyncio
async def test_import_json_replaces_existing_record(seeded_client):
    payload = {
        "records": [{
            "dataDate": "2025-01-01",
            "lineName": "祁韶直流",
            "voltageText": "±800kV",
            "powers": {time: 100 for time in POWER_TIME_COLUMNS},
        }],
    }
    first = await seeded_client.post("/ir/tie-lines/power/import", json=payload)
    second_payload = {**payload}
    second_payload["records"][0]["powers"] = {
        time: 200 for time in POWER_TIME_COLUMNS
    }
    second = await seeded_client.post("/ir/tie-lines/power/import", json=second_payload)

    assert first.status_code == 200
    assert first.json()["data"]["insertedCount"] == 1
    assert second.status_code == 200
    assert second.json()["data"]["deletedCount"] == 1
    assert second.json()["data"]["insertedCount"] == 1
    # 直接查询数据库断言仅 1 条且 `00:15` 等于 Decimal("200")。
```

在同一文件中加入：Excel 通过 `io.BytesIO` + `openpyxl.Workbook` 构造最小完整 99 列工作簿并上传后返回 200；JSON 缺少一个时段、未知线路、重复业务键、Excel 表头错误、错误 Content-Type 返回 400，且失败时表行数不变。

- [ ] **Step 2: 运行端点测试，确认路由尚未实现而失败**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/test_tie_line_power_import_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL，路由返回 404。

- [ ] **Step 3: 编写 Excel 解析器**

`power_import_parser.py` 提供：

```python
async def parse_excel_import(upload: UploadFile) -> list[PowerImportRecord]:
```

实现要求：

1. 文件名为空或不是 `.xlsx`（大小写不敏感）时抛 `ValidationException("仅支持 .xlsx 文件")`；
2. 用 `await upload.read()` 取得字节，空内容抛 `ValidationException("Excel 文件不能为空")`；
3. `openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)` 解析，`BadZipFile`、`InvalidFileException` 等异常转为 `ValidationException("Excel 文件格式无效")`；
4. 缺少“功率”工作表抛 `ValidationException("Excel 缺少“功率”工作表")`；
5. 第一行严格等于 `("日期", "名称", "电压等级", *POWER_TIME_COLUMNS)`；否则抛 `ValidationException("Excel 表头与功率模板不一致")`；
6. 逐行检查：空整行跳过；日期转为 `date`，字符串日期只接收 ISO 格式；名称和电压去除首尾空格后不得为空；功率空白转 `None`，其他值 `Decimal(str(value))` 并检查 `is_finite()`；任一问题抛包含 Excel 行号的 `ValidationException`；
7. 无有效行抛 `ValidationException("Excel 不包含功率数据")`；返回记录列表。重复键和完整键校验由应用服务统一处理。

- [ ] **Step 4: 在路由添加 Pydantic JSON 模型和导入入口**

在 `router.py` 增加导入：

```python
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
```

定义：

```python
class PowerJsonRecordReq(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_date: date = Field(alias="dataDate")
    line_name: str = Field(alias="lineName", min_length=1, max_length=128)
    voltage_text: str = Field(alias="voltageText", min_length=1, max_length=64)
    powers: dict[str, Decimal | None]


class PowerJsonImportReq(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[PowerJsonRecordReq] = Field(min_length=1)
```

在记录模型 validator 中拒绝非有限数值；在路由中对名称、电压执行 `strip()` 后检查非空。

新增：

```python
@router.post("/power/import")
async def import_tie_line_power(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "application/json":
        payload = PowerJsonImportReq.model_validate(await request.json())
        records = [
            PowerImportRecord(
                data_date=item.data_date,
                line_name=item.line_name.strip(),
                voltage_text=item.voltage_text.strip(),
                powers=item.powers,
            )
            for item in payload.records
        ]
    elif content_type == "multipart/form-data":
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ValidationException("请使用 file 字段上传 Excel 文件")
        records = await parse_excel_import(upload)
    else:
        raise ValidationException("仅支持 application/json 或 multipart/form-data")

    result = await _power_import_service.import_records(session, records)
    await session.commit()
    return ok({
        "receivedCount": result.received_count,
        "deletedCount": result.deleted_count,
        "insertedCount": result.inserted_count,
        "matchedLineCount": result.matched_line_count,
    })
```

在 `try/except` 中捕捉写入阶段异常并执行 `await session.rollback()` 后重新抛出，确保不会留下半写入状态。解析/校验在调用 `import_records` 前完成，不得触发任何数据库写入。

- [ ] **Step 5: 运行端点测试，确认 JSON 和 Excel 两种路径通过**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/test_tie_line_power_import_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS，所有 JSON/Excel 成功和 400 场景通过。

### Task 4: 添加存量清理和唯一索引维护脚本

**Files:**
- Create: `agent-backend/sql/maintain_tie_line_power_unique.sql`
- Create: `agent-backend/tests/unit/tie_line_map/test_tie_line_power_maintenance_sql.py`

- [ ] **Step 1: 编写失败的维护脚本静态测试**

创建测试，读取脚本并断言其：

```python
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
```

- [ ] **Step 2: 执行测试，确认维护脚本不存在而失败**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_maintenance_sql.py', '-q']))"
```

Expected: FAIL，报错找不到 SQL 文件。

- [ ] **Step 3: 编写可重复安全的 MySQL 维护脚本**

创建 `maintain_tie_line_power_unique.sql`：

```sql
-- 对同一日期、线路名称和电压等级的历史重复记录保留最大 id。
DELETE older
FROM ir_tie_line_power AS older
JOIN ir_tie_line_power AS newer
  ON older.data_date = newer.data_date
 AND older.line_name = newer.line_name
 AND older.voltage_text = newer.voltage_text
 AND older.id < newer.id;

SET @index_exists := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'ir_tie_line_power'
    AND index_name = 'uk_ir_tie_line_power_date_name_voltage'
);
SET @sql := IF(
  @index_exists = 0,
  'ALTER TABLE ir_tie_line_power ADD UNIQUE INDEX uk_ir_tie_line_power_date_name_voltage (data_date, line_name, voltage_text)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

- [ ] **Step 4: 运行维护脚本静态测试，确认通过**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/test_tie_line_power_maintenance_sql.py', '-q']))"
```

Expected: PASS，1 passed。

### Task 5: 同步模块文档并执行回归验证

**Files:**
- Modify: `my_projects/联络线地图模块-功能与开发文档.md:136-151`

- [ ] **Step 1: 更新联络线模块文档**

将“后续改动指引”的功率时序部分更新为当前已具备的导入能力：

- 说明宽表 `ir_tie_line_power` 的业务唯一键是 `data_date + line_name + voltage_text`；
- 说明 `POST /ir/tie-lines/power/import` 对 JSON 和 Excel 的 Content-Type 分派；
- 指明 JSON 的 96 时段嵌套于 `powers`，Excel 使用固定“功率”工作表和严格表头；
- 说明导入按名称匹配 `line_id`，在单事务中替换相同业务键旧数据；
- 保留“尚未实现功率查询 API、趋势图和真实潮流方向”的范围说明。

- [ ] **Step 2: 执行全部相关测试**

Run:

```bash
cd agent-backend && ../.mypython/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tie_line_map/', 'tests/e2e/tie_line_map/', 'tests/unit/test_architecture_layout.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS，新增单元/端点测试和既有联络线、架构测试全部通过。

- [ ] **Step 3: 执行差异检查**

Run:

```bash
git diff --check -- agent-backend/requirements.txt agent-backend/app/modules/tie_line_map agent-backend/sql/maintain_tie_line_power_unique.sql agent-backend/tests/unit/tie_line_map agent-backend/tests/e2e/tie_line_map my_projects/联络线地图模块-功能与开发文档.md
git diff --stat
```

Expected: `git diff --check` 无输出；差异仅包含计划文件中列出的依赖、导入接口、ORM、维护脚本、测试和模块文档。根据项目规则，不执行 `git add`、`git commit` 或 `git push`。
