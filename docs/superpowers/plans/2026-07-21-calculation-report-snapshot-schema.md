# 测算结果与正式报告快照数据库重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将测算结果快照与未来正式报告快照拆分为语义明确、受 MySQL 约束保护的持久化结构，同时保持现有测算结果和会话历史 HTTP 行为不变。

**Architecture:** 现有结果快照 ORM/表从 `ReportSnapshotORM`/`ir_report_snapshot` 改为 `CalculationResultSnapshotORM`/`ir_calculation_result_snapshot`；所有既有测算写入、结果读取和历史回放只替换这一内部依赖。新增独立、空的 `ReportSnapshotORM`/`ir_report_snapshot` 作为未来正式报告存储，消息表增加通用事件分类和轻量 JSON 载荷。本次不提供任何报告生成或读取业务接口。

**Tech Stack:** Python 3.13、FastAPI、SQLAlchemy 异步 ORM、MySQL 8/InnoDB、pytest、现有 MySQL 测试库。

## Global Constraints

- 后端仅通过 `agent-backend/requirements.txt` 管理依赖；本计划不新增依赖。
- 不调用 `python` 或 `python3`；测试使用 `agent-backend/.venv/Scripts/python.exe` 的 stdout 包装命令。
- 响应壳保持 `{code, msg, data}`；参数校验维持 HTTP 400。
- 飞书仍是唯一权威计算器；不得修改财务公式或飞书接口区规则。
- 历史/结果展示继续只读取计算结果快照，不依赖飞书副本。
- 会话继续软删除；会话、任务和结果读取继续按当前用户过滤，非本人资源返回 404。
- 本次只重构数据库/持久化基础设施；不实现报告生成 API、前端入口、报告详情、报告历史、模板、JSON 内容、PDF、附件、AI、编辑、重生成、状态或任务表。
- 新正式报告表只为未来实现预留；本次不得插入、读取或暴露正式报告行。
- 直接验证 MySQL 测试库的 JSON、外键、唯一约束和索引；不为报告逻辑增加 SQLite 分支、回退或专门测试基础设施。现有 ORM 中已经存在的通用 JSON 映射继续保留，以免破坏全局 ORM 元数据及既有纯单元测试。
- 不执行 `git add`、`git commit`、`git push` 或任何其他 Git 写操作。
- 实际清空/重建测试数据库前，必须展示完整 SQL 并获得用户对该次不可逆操作的再次确认。
- 可操作表范围仅为：`ir_conversation`、`ir_calculation_task`、`ir_message_snapshot`、`ir_input_snapshot`、`ir_data_snapshot`、`ir_feishu_io_snapshot`、旧 `ir_report_snapshot`；不得触碰 `ir_spot_station`、`ir_spot_daily_optimal_province`、`ir_spot_daily_optimal_node` 或无关表。

---

## File Structure

- `changes/PRD-001-login-calc-mainflow/execution-contract.md` — 将结果快照改名和正式报告表预留纳入 active spec-superflow 的数据库基础设施切片，并重申正式报告产品功能仍延期。
- `changes/PRD-001-login-calc-mainflow/tasks.md` — 增加可执行的数据库重构批次、TDD 证据与 MySQL 重建前确认门槛。
- `agent-backend/app/modules/calculation/infrastructure/persistence/orm.py` — 重命名计算结果快照 ORM，新增正式报告 ORM，扩展消息 ORM，并声明唯一约束和索引。
- `agent-backend/app/modules/calculation/infrastructure/persistence/__init__.py` — 导出重命名后的计算结果快照 ORM 与新正式报告 ORM。
- `agent-backend/app/modules/calculation/application/snapshot_service.py` — 成功测算继续写入计算结果快照；普通消息显式采用 `text` 语义。
- `agent-backend/app/modules/calculation/application/conversation_history_service.py` — 从计算结果快照读取版本结果，并向历史响应传递消息类型和轻量载荷。
- `agent-backend/app/modules/calculation/interface/router.py` — 从计算结果快照读取结果，保持现有 HTTP 响应结构。
- `agent-backend/sql/ir_agent_schema.sql` — 作为 MySQL 空库重建 DDL，包含改名后的结果表、新正式报告表、消息字段、约束和索引。
- `agent-backend/tests/db/test_snapshot_service.py` — 将既有真实 MySQL 快照服务测试改为计算结果快照语义并验证消息普通文本默认语义。
- `agent-backend/tests/db/test_snapshot_schema.py` — 新增真实 MySQL 模式约束测试：四类快照与正式报告的唯一性、正式报告字段默认/非空/外键、消息扩展字段和会话查询索引。
- `agent-backend/tests/integration/calculation/test_calc_task_api.py` — 更新/补充测算结果 API 回归，证明底层表改名不改变响应数据。
- `agent-backend/tests/integration/calculation/test_conversation_history_api.py` — 更新/补充会话历史回归，证明消息字段扩展与计算结果读取不破坏回放、软删除和归属行为。

## Task 1: Refresh the active execution contract before application changes

**Files:**
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md`
- Modify: `changes/PRD-001-login-calc-mainflow/tasks.md`
- Test: `changes/PRD-001-login-calc-mainflow/execution-contract.md` (manual consistency review)

**Interfaces:**
- Consumes: approved design at `docs/superpowers/specs/2026-07-21-calculation-report-snapshot-schema-design.md`.
- Produces: an approved active-contract entry authorizing only this schema/persistence slice; all later tasks rely on it.

- [ ] **Step 1: Add a failing compliance checklist to the execution contract**

Add a new database-reconstruction batch under `## Execution Batches` with these required outcomes:

```markdown
### Batch 7 · 测算结果/正式报告快照数据库重构

1. 将既有测算结果快照表和 ORM 从 `report_snapshot` 改为 `calculation_result_snapshot`；既有结果接口与历史回放对外响应不变。
2. 新建空的 `ir_report_snapshot` 正式报告表；本批不得实现报告生成、读取或前端功能。
3. 为 input/data/feishu I/O/calculation-result 四类快照增加 `UNIQUE(task_id)`。
4. 为 message snapshot 增加 `message_type='text'` 默认值和可空 JSON `payload`。
5. 仅在用户确认后清空规定的 MySQL 测试表并按完整 DDL 重建；不得触碰现货预计算表。
6. 用真实 MySQL 约束测试以及既有结果/会话 HTTP 回归验证。
```

- [ ] **Step 2: Record that the existing contract is intentionally failing scope alignment**

In the contract scope fence and the existing snapshot/result wording, replace ambiguous uses of `report_snapshot` that mean the current calculation result with `calculation_result_snapshot`. Keep “报告本体/PDF及报告历史” out of scope, but add that the **empty persistence table only** is in scope for Batch 7. Explicitly state that no report payload schema or report API is authorized.

- [ ] **Step 3: Add the executable Batch 7 items to the active task list**

Add a checked-list section to `changes/PRD-001-login-calc-mainflow/tasks.md` after the existing batch sections. Its test-first acceptance items must name:

```markdown
- MySQL schema constraints for all four snapshot `task_id` uniqueness rules.
- New `ir_report_snapshot` fields: report_id uniqueness, task_id uniqueness/FK, conversation_id FK, user_id index, schema_version default, JSON non-null payload, conversation_id+created_at index.
- message_type default `text` and nullable payload.
- result and conversation-history HTTP response compatibility.
- explicit user confirmation before destructive MySQL reset.
```

- [ ] **Step 4: Review the refreshed documents for contradictory scope**

Read the changed contract and tasks. Verify each statement below is true:

```text
- “report_snapshot” means only the new future formal-report table.
- “calculation_result_snapshot” means the existing three-module result data source.
- Batch 7 does not authorize report generation or report UI.
- MySQL reset is limited to the approved seven existing tables.
```

Expected: no remaining statement claims that the old `report_snapshot` table is the historical calculation result source.

- [ ] **Step 5: Stop for contract approval if it has changed materially**

Present the exact Batch 7 contract/task delta to the user and wait for explicit confirmation before modifying backend application code. Do not run schema SQL in this task.

## Task 2: Define the persistence model and MySQL DDL with failing schema tests

**Files:**
- Modify: `agent-backend/app/modules/calculation/infrastructure/persistence/orm.py`
- Modify: `agent-backend/app/modules/calculation/infrastructure/persistence/__init__.py`
- Modify: `agent-backend/sql/ir_agent_schema.sql`
- Create: `agent-backend/tests/db/test_snapshot_schema.py`

**Interfaces:**
- Consumes: Batch 7 contract approval from Task 1.
- Produces: `CalculationResultSnapshotORM`, future-only `ReportSnapshotORM`, extended `MessageSnapshotORM`, and matching MySQL DDL. Tasks 3–5 import the renamed calculation-result model.

- [ ] **Step 1: Write failing MySQL schema tests**

Create `tests/db/test_snapshot_schema.py`. Use the existing `tests.db.conftest` MySQL session/engine fixtures and a random unique identifier. Add tests that perform the following observable checks:

```python
async def test_snapshot_tables_reject_second_row_for_same_task(db_session):
    # Create one conversation and one CalculationTaskORM.
    # Insert one InputSnapshotORM for its id, then attempt a second.
    # Repeat independently for DataSnapshotORM, FeishuIoSnapshotORM,
    # and CalculationResultSnapshotORM.
    # Each second insert must raise sqlalchemy.exc.IntegrityError.

async def test_formal_report_schema_enforces_future_report_contract(db_session):
    # Create one conversation and one CalculationTaskORM.
    # Insert ReportSnapshotORM with a unique report_id and payload={"kind": "test"}.
    # Assert schema_version == 1 and payload round-trips.
    # A second row for the same task_id must raise IntegrityError.
    # A row with a duplicate report_id for another task must raise IntegrityError.
    # A row with a missing task_id or conversation_id must raise IntegrityError.

async def test_message_snapshot_defaults_to_text_and_accepts_nullable_payload(db_session):
    # Insert MessageSnapshotORM with only conversation_id, role and content.
    # Reload and assert message_type == "text" and payload is None.
    # Insert a second message with message_type="report_generated" and
    # payload={"report_id": "r-test", "task_id": task_id}; assert it round-trips.
```

Use a nested transaction or explicit rollback after each expected `IntegrityError` so the session remains usable. Add a MySQL metadata assertion using `inspect`/`SHOW INDEX` to verify the formal-report `(conversation_id, created_at)` index and `user_id` index exist.

- [ ] **Step 2: Run the new schema tests and verify they fail**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/db/test_snapshot_schema.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because `CalculationResultSnapshotORM` and the formal-report fields/constraints do not yet exist, and the MySQL test database has the old DDL.

- [ ] **Step 3: Implement the ORM model changes**

In `orm.py`, make these exact declarations while preserving the existing shared primary-key/time mixin:

```python
class MessageSnapshotORM(_PkTimestamp, Base):
    __tablename__ = "ir_message_snapshot"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="text", server_default="text"
    )
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
```

Replace the old result model with:

```python
class CalculationResultSnapshotORM(_PkTimestamp, Base):
    __tablename__ = "ir_calculation_result_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ir_calculation_task.id"),
        nullable=False,
        unique=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
```

Add `unique=True` to `task_id` in `InputSnapshotORM`, `DataSnapshotORM`, and `FeishuIoSnapshotORM`. Do not add a calculation-version uniqueness constraint.

Add the future-only report model:

```python
class ReportSnapshotORM(_PkTimestamp, Base):
    __tablename__ = "ir_report_snapshot"
    __table_args__ = (
        Index("ix_ir_report_snapshot_conversation_created_at", "conversation_id", "created_at"),
    )

    report_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ir_calculation_task.id"),
        nullable=False,
        unique=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_conversation.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
```

Import `Index` and `SmallInteger`. Do not add report write/read methods, relationships, update support, report statuses, report message generation, or SQLite-specific conditionals.

- [ ] **Step 4: Update persistence package exports**

In `infrastructure/persistence/__init__.py`, remove the old result-model export name and export both names with their new roles:

```python
from .orm import CalculationResultSnapshotORM, ReportSnapshotORM

__all__ = [
    # preserve all existing exports,
    "CalculationResultSnapshotORM",
    "ReportSnapshotORM",
]
```

- [ ] **Step 5: Make the full MySQL DDL match ORM metadata**

Replace the old result table block in `sql/ir_agent_schema.sql` with a `ir_calculation_result_snapshot` table that has `task_id BIGINT NOT NULL UNIQUE`, JSON `payload`, primary key, and task foreign key.

Add the new formal report DDL with these exact column/constraint semantics:

```sql
CREATE TABLE ir_report_snapshot (
    report_id VARCHAR(64) NOT NULL,
    task_id BIGINT NOT NULL,
    conversation_id BIGINT NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    schema_version SMALLINT NOT NULL DEFAULT 1,
    payload JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_report_snapshot_report_id (report_id),
    UNIQUE KEY uq_ir_report_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id),
    FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_report_snapshot_user_id ON ir_report_snapshot (user_id);
CREATE INDEX ix_ir_report_snapshot_conversation_created_at
    ON ir_report_snapshot (conversation_id, created_at);
```

Add `message_type VARCHAR(32) NOT NULL DEFAULT 'text'` and `payload JSON` to the message table. Replace each snapshot table’s standalone task index with a unique key/index consistent with `unique=True`; do not create a redundant second non-unique task index.

- [ ] **Step 6: Inspect ORM metadata vs DDL without destructive SQL**

Use a read-only comparison of the edited ORM declarations and DDL. Verify all names and semantics match:

```text
CalculationResultSnapshotORM -> ir_calculation_result_snapshot
ReportSnapshotORM -> ir_report_snapshot
message_type -> VARCHAR(32) NOT NULL DEFAULT 'text'
message payload -> JSON NULL
input/data/feishu/calculation-result task_id -> UNIQUE
formal report report_id/task_id -> UNIQUE
formal report schema_version -> SMALLINT DEFAULT 1
formal report payload -> JSON NOT NULL
formal report indexes -> user_id and (conversation_id, created_at)
```

- [ ] **Step 7: Obtain explicit confirmation for the destructive test-database reset**

Show the user the exact SQL prepared in Task 3 before executing it. Do not run it until they explicitly approve that individual action.

## Task 3: Rebuild only the approved MySQL test tables

**Files:**
- Create: `agent-backend/sql/rebuild_snapshot_schema_test.sql`
- Modify: `agent-backend/sql/ir_agent_schema.sql` (only if Task 2 comparison found a mismatch)
- Test: `agent-backend/tests/db/test_snapshot_schema.py`

**Interfaces:**
- Consumes: matching ORM/DDL from Task 2 and explicit user confirmation for this destructive execution.
- Produces: MySQL test database with only the approved conversation/calculation/snapshot tables rebuilt under the new schema.

- [ ] **Step 1: Create an explicit, narrowly scoped reset SQL script**

Create `sql/rebuild_snapshot_schema_test.sql` with the following order, preserving all unrelated tables:

```sql
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ir_report_snapshot;
DROP TABLE IF EXISTS ir_calculation_result_snapshot;
DROP TABLE IF EXISTS ir_feishu_io_snapshot;
DROP TABLE IF EXISTS ir_data_snapshot;
DROP TABLE IF EXISTS ir_input_snapshot;
DROP TABLE IF EXISTS ir_message_snapshot;
DROP TABLE IF EXISTS ir_calculation_task;
DROP TABLE IF EXISTS ir_conversation;
SET FOREIGN_KEY_CHECKS = 1;
```

After the drops, include the eight relevant `CREATE TABLE`/`CREATE INDEX` definitions copied from the verified `ir_agent_schema.sql`: conversation, calculation task, message, input, data, Feishu I/O, calculation result, and formal report. Do not reference any spot or other tables.

- [ ] **Step 2: Display the exact SQL and request one-time destructive-operation confirmation**

Present the script contents and explicitly state that it drops only these seven existing tables:

```text
ir_conversation
ir_calculation_task
ir_message_snapshot
ir_input_snapshot
ir_data_snapshot
ir_feishu_io_snapshot
ir_report_snapshot
```

It additionally drops the new-name result table only if a prior interrupted test rebuild left it behind. Confirm no spot table is named in the script. Wait for explicit user confirmation.

- [ ] **Step 3: Execute the approved SQL against the configured MySQL test database**

Use the project’s existing configured test database connection method; do not invent connection flags or credentials. Execute only `sql/rebuild_snapshot_schema_test.sql` after confirmation.

Expected: the seven approved old tables are rebuilt, `ir_calculation_result_snapshot` exists, new `ir_report_snapshot` exists and is empty, and spot tables are unchanged.

- [ ] **Step 4: Run schema tests against the rebuilt MySQL database**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/db/test_snapshot_schema.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

- [ ] **Step 5: Verify excluded tables were untouched**

Use a read-only MySQL metadata query through the project’s configured connection to verify these tables still exist after the reset:

```text
ir_spot_station
ir_spot_daily_optimal_province
ir_spot_daily_optimal_node
```

Expected: all three tables exist; this task has not issued DDL or DML for them.

## Task 4: Move existing calculation persistence to the renamed result model

**Files:**
- Modify: `agent-backend/app/modules/calculation/application/snapshot_service.py`
- Modify: `agent-backend/app/modules/calculation/application/conversation_history_service.py`
- Modify: `agent-backend/app/modules/calculation/interface/router.py`
- Modify: `agent-backend/tests/db/test_snapshot_service.py`
- Modify: `agent-backend/tests/integration/calculation/test_calc_task_api.py`
- Modify: `agent-backend/tests/integration/calculation/test_conversation_history_api.py`

**Interfaces:**
- Consumes: `CalculationResultSnapshotORM` from Task 2 and rebuilt MySQL schema from Task 3.
- Produces: unchanged result/history HTTP response contracts backed by `ir_calculation_result_snapshot`.

- [ ] **Step 1: Update tests to express the external compatibility contract**

In `tests/db/test_snapshot_service.py`, replace imports and assertions that refer to `ReportSnapshotORM` as a calculation result with `CalculationResultSnapshotORM`. Preserve the existing two-calculation scenario and add these assertions:

```python
assert result_snapshot.payload["basicInfo"]["province"] == "甘肃"
assert message.message_type == "text"
assert message.payload is None
```

In `tests/integration/calculation/test_calc_task_api.py`, ensure the existing completed-task result test asserts the same response envelope and result fields it asserted before the schema rename; the test must not expose a table name.

In `tests/integration/calculation/test_conversation_history_api.py`, assert each normal historic message serializes with its original role/content and with `messageType == "text"` plus `payload is None` once the API is extended in Step 3. Preserve existing soft-delete and cross-user-404 assertions.

- [ ] **Step 2: Run the focused tests and verify they fail before service/API edits**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/db/test_snapshot_service.py', 'tests/integration/calculation/test_calc_task_api.py', 'tests/integration/calculation/test_conversation_history_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL due to remaining old result-model imports/queries and missing message fields in the history response.

- [ ] **Step 3: Change snapshot writing to calculation-result persistence**

In `snapshot_service.py`:

```python
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    # retain the existing imports
)

# In persist_success after FeishuIoSnapshotORM:
session.add(
    CalculationResultSnapshotORM(
        task_id=task.id,
        payload=to_report_payload(result),
    )
)
```

For ordinary messages, write the new generic fields explicitly:

```python
MessageSnapshotORM(
    conversation_id=conversation_id,
    role="user",
    content=user_message,
    message_type="text",
    payload=None,
)
```

Apply the same `message_type="text", payload=None` pattern to the assistant message. Update comments/docstrings so “calculation-result snapshot” refers to the three-module result and “formal report” is never implied.

- [ ] **Step 4: Change read paths without changing their external result contract**

In `conversation_history_service.py`, import and query `CalculationResultSnapshotORM` instead of the old result model. Build `result_by_task` from `snapshot.payload` exactly as before.

Extend each serialized message to use camel-case API names:

```python
{
    "role": message.role,
    "content": message.content,
    "messageType": message.message_type,
    "payload": message.payload,
    "createdAt": message.created_at.isoformat(),
}
```

In the calculation result router, import/query `CalculationResultSnapshotORM` in place of the old result model, but return the same established result data envelope and payload. Do not add report routes.

- [ ] **Step 5: Run focused persistence and HTTP regression tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/db/test_snapshot_service.py', 'tests/integration/calculation/test_calc_task_api.py', 'tests/integration/calculation/test_conversation_history_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. The result endpoint and conversation history return calculation-result data as before; normal messages expose `messageType: "text"` and `payload: null`.

## Task 5: Perform the full regression and schema/contract review

**Files:**
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md` (mark Batch 7 evidence only after all checks pass)
- Modify: `changes/PRD-001-login-calc-mainflow/tasks.md` (mark completed items only after all checks pass)
- Test: `agent-backend/tests/db/test_snapshot_schema.py`
- Test: `agent-backend/tests/db/test_snapshot_service.py`
- Test: `agent-backend/tests/integration/calculation/test_calc_task_api.py`
- Test: `agent-backend/tests/integration/calculation/test_conversation_history_api.py`

**Interfaces:**
- Consumes: passing Task 2–4 tests.
- Produces: verified Batch 7 persistence slice with active contract evidence updated; no report feature surface.

- [ ] **Step 1: Run the complete backend suite with the project-required wrapper**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. If any existing test still imports the old calculation-result model name or expects old message response shape, update only that test/code path to the approved new semantics; do not add compatibility aliases that retain `ReportSnapshotORM` as the calculation-result model.

- [ ] **Step 2: Perform a semantic-reference scan**

Search backend source, backend tests, DDL, and active spec documents for `ir_report_snapshot` and `ReportSnapshotORM`. Classify every remaining occurrence:

```text
Allowed: the new future formal-report model/table/DDL/schema tests.
Disallowed: existing calculation result persistence, result endpoint, or history replay.
```

Search for `ir_calculation_result_snapshot` and `CalculationResultSnapshotORM`. Verify they appear in all calculation-result write/read locations.

- [ ] **Step 3: Verify no formal-report product feature leaked into this slice**

Confirm all statements are true:

```text
- No API route creates or reads a formal report.
- No application service inserts ReportSnapshotORM.
- No frontend file changed for reports.
- No report payload schema, template, PDF, attachment, status, retry, update, or task logic exists.
- No spot precompute file or table changed.
```

- [ ] **Step 4: Record passing evidence in the active contract and task list**

Only after all tests pass, update Batch 7 status/evidence in `execution-contract.md` and check corresponding `tasks.md` items. Record the exact pytest commands from Steps 3–5 and their PASS outcomes. Do not mark any report-product capability as complete.

- [ ] **Step 5: Report completion without Git operations**

Summarize:

```text
- files changed;
- exact MySQL tables rebuilt;
- confirmation that spot tables were untouched;
- tests executed and their outcomes;
- explicitly deferred report product capabilities.
```

Do not stage, commit, or push changes.
