# 测算结果与正式报告快照数据库设计

## Problem Statement

当前 `ir_report_snapshot` 实际保存的是一次测算的结果三模块快照，用于结果页和会话历史回放；它不是用户主动生成的正式报告。该命名会与未来正式报告模块冲突。

现有测算快照表仅以普通索引关联 `task_id`，数据库没有保证一次测算至多一份输入、数据、飞书 I/O 和结果快照。消息快照表也只能表达纯文本消息，不能稳定保存未来报告生成等结构化会话时间线事件。

本次工作要先完成数据库和持久化基础设施重构：明确测算结果快照与正式报告快照的不同职责，并保持现有测算结果和会话历史 API 行为不变。正式报告内容、模板、生成和展示功能尚未定义，不能在本次预设。

## Solution

将当前结果快照表改名为 `ir_calculation_result_snapshot`，继续作为每次成功测算的结果三模块快照和历史回放数据源。新建空的 `ir_report_snapshot`，为未来用户主动生成、不可修改且可独立恢复的正式报告准备持久化结构。

本次以 MySQL 测试库为目标，对已确认的会话、测算和快照表执行受控清空与重建。现有测算和会话接口对外保持兼容，仅替换内部读取和写入的结果快照表。新报告表本次不写入、不读取、不暴露 API。

## User Stories

1. As an investment analyst, I want each completed calculation to retain one immutable calculation-result snapshot, so that the result can be viewed after the Feishu copy is unavailable.
2. As an investment analyst, I want the calculation-result snapshot to have an unambiguous name, so that it is not confused with a future formal report.
3. As an investment analyst, I want multiple independent calculations in one conversation to keep separate results, so that later calculations do not alter earlier history.
4. As an investment analyst, I want a future formal report to be tied to at most one calculation record, so that a calculation cannot produce duplicate formal reports.
5. As an investment analyst, I want a future formal report to be optional, so that calculations without a report request have no report record.
6. As an investment analyst, I want a future formal report to contain one complete immutable snapshot, so that its display can be restored without recalculation or a Feishu dependency.
7. As an investment analyst, I want the future formal report to be discoverable within its conversation, so that the conversation can show its report history without duplicate report data.
8. As an investment analyst, I want future report-generation events to appear in the conversation timeline, so that the order of interactions is retained.
9. As an investment analyst, I want report-generation timeline events to reference, rather than duplicate, report content, so that the report has one authoritative stored copy.
10. As a user, I want the existing calculation result endpoint to keep returning the same result shape, so that current clients do not break because of an internal table rename.
11. As a user, I want conversation replay to continue returning messages, calculation records, and their results, so that historical conversations behave as before.
12. As a user, I want a soft-deleted conversation and all its calculations and snapshots to remain stored but inaccessible through normal reads, so that history can be retained and later restored with the conversation.
13. As a maintainer, I want database uniqueness constraints for each calculation snapshot type, so that corrupted duplicate snapshots cannot silently enter the database.
14. As a maintainer, I want MySQL to validate JSON and relational constraints for the new report structure, so that production-relevant persistence semantics are exercised in tests.

## Implementation Decisions

### Scope and data model

- This implementation is a persistence-infrastructure slice only. It does not implement formal-report generation, report APIs, frontend report controls, report detail rendering, a conversation-side report list, report templates, report payload contents, PDF output, attachments, object storage, AI generation, report editing, regeneration, revision history, report statuses, retries, or report-generation task records.
- A conversation may contain multiple independent calculation records. Existing `version` remains a conversation-local display sequence and is not a report revision mechanism. This change does not add a uniqueness constraint for `(conversation_id, version)`.
- A calculation task has one input snapshot, one data snapshot, one Feishu I/O snapshot, and one calculation-result snapshot at most. A future formal report is optional and has one report snapshot at most.

### Calculation result snapshot rename

- Rename the existing calculation-result persistence concept from `ir_report_snapshot` to `ir_calculation_result_snapshot`.
- Rename the corresponding ORM model and all internal reads/writes to use the calculation-result name.
- Continue to store the existing result payload shape in the renamed table.
- Preserve external behavior: the result endpoint and conversation detail response continue to return the current calculation-result JSON shape. API field names are not changed in this slice solely because the underlying table was renamed.
- The calculation-result snapshot remains the only data source used by existing historical result replay. It remains independent of the Feishu copy.

### Formal report snapshot table

- Create a new, initially unused `ir_report_snapshot` table for future successfully generated formal reports.
- The table contains an auto-increment internal primary key, plus `report_id VARCHAR(64) NOT NULL UNIQUE` as the immutable opaque external report identifier. The application will choose the identifier format later; no UUID, ULID, prefix, or ordering semantics are fixed now.
- `task_id` is `NOT NULL`, has a foreign key to the calculation task, and is unique. It enforces that one calculation record can have zero or one formal report.
- `conversation_id` is `NOT NULL` and has a foreign key to the conversation. Its value is copied from the source calculation's conversation when a future report is generated. The application validates task/conversation ownership; no composite foreign key or extra database consistency rule is introduced.
- `user_id` is `VARCHAR(64) NOT NULL`, with the same definition, character semantics, and index meaning as the conversation owner field. It is a denormalized ownership/query field copied from the conversation and has no local-user foreign key.
- `schema_version` is `SMALLINT NOT NULL DEFAULT 1`. It only identifies the structure version of the future report JSON; it does not define report sections or templates.
- `payload` is MySQL native `JSON NOT NULL`. It will eventually hold one complete, independently restorable report snapshot. This implementation does not define its JSON structure or write any rows.
- `created_at` follows the existing snapshot convention: `DATETIME NOT NULL DEFAULT NOW()`. For a future report row, it means successful generation and freezing time.
- Add a composite index on `(conversation_id, created_at)` for conversation-local report history ordered by generation time, and an index on `user_id` consistent with conversation-owner query semantics.
- Do not store `calculation_version` or a calculation-result-snapshot identifier on the report table. The source task is the only source association, and the eventual report payload may define its own content when report requirements exist.
- Do not impose a business payload-size limit. Do not store binary attachments in the JSON; any future attachments require external storage references.
- Do not add a trigger or other database-level immutability guard. Future application code will insert and read report rows only, with no update API. The unique task constraint remains a data-consistency rule.

### Message timeline extension

- Extend `ir_message_snapshot` with `message_type VARCHAR(32) NOT NULL DEFAULT 'text'` and nullable native `JSON` `payload`.
- Existing and ordinary human-readable messages retain `message_type='text'`, a user-visible `content` value, and `payload=NULL`.
- `content` remains part of the conversation display model; it is not an implementation-only log field.
- A future report-generation success event uses `message_type='report_generated'`, a short visible content message, and a lightweight payload containing `report_id` and `task_id`.
- The event payload does not duplicate the formal report JSON. It has no report-specific columns or foreign keys in the message table. This implementation only adds the generic fields and does not generate or consume report events.

### Existing snapshot integrity

- Add `UNIQUE(task_id)` to input, data, Feishu I/O, and calculation-result snapshot tables.
- The constraints prevent duplicate snapshot rows for the same calculation task but do not limit the number of independent calculation tasks in a conversation.

### Deletion and ownership

- Preserve the current soft-delete rule: setting a conversation's deletion timestamp does not physically delete tasks, messages, calculation-result snapshots, or future formal report snapshots.
- Existing normal read paths keep excluding soft-deleted conversations and enforcing current-user ownership. A future report read path must follow the same rule, including when a report is addressed by its external identifier.
- Do not add cascade deletes.

### Database execution boundary

- The target data store for this schema work is the MySQL test database. Do not add SQLite fallback types, compatibility paths, or report-specific SQLite test infrastructure.
- Before executing destructive SQL, present the exact SQL and require an explicit confirmation.
- The permitted destructive scope is limited to `ir_conversation`, `ir_calculation_task`, `ir_message_snapshot`, `ir_input_snapshot`, `ir_data_snapshot`, `ir_feishu_io_snapshot`, and the existing `ir_report_snapshot`. Rebuild these tables and create `ir_calculation_result_snapshot` and the new `ir_report_snapshot`.
- Do not modify or delete `ir_spot_station`, `ir_spot_daily_optimal_province`, `ir_spot_daily_optimal_node`, or unrelated tables.
- Historical test data in the permitted scope does not need preservation.

## Testing Decisions

- Test observable persistence and HTTP behavior, not private ORM implementation details.
- Use the existing FastAPI HTTP integration seam to verify that a completed calculation still returns the same result JSON and that conversation detail still replays messages, calculation records, and calculation results.
- Retain existing ownership and soft-delete regression coverage: cross-user access remains a 404, and soft deletion retains underlying rows while hiding normal reads.
- Add MySQL integration coverage for the new physical schema: presence of the calculation-result and formal-report tables, the four `UNIQUE(task_id)` constraints, formal-report `report_id` and task uniqueness, report foreign keys, `schema_version` default, `payload JSON NOT NULL`, conversation-history index, and message defaults/nullability.
- Database tests may directly operate on the MySQL test database. Do not add SQLite compatibility branches or dedicated SQLite verification for report persistence.
- Existing snapshot-service tests remain the prior art for a successful calculation's independent snapshot persistence. Existing calculation-result API and conversation-history API tests remain the prior art for the external HTTP regression seam.

## Out of Scope

- Defining formal report sections, fields, input sources, templates, rendering, or JSON payload format.
- Creating, rendering, listing, querying, editing, regenerating, exporting, or deleting formal reports.
- Frontend changes for report buttons, inline report cards, report detail pages, or the right-side report-history area.
- PDF generation, attachments, object storage, AI report generation, and report audit/status/task mechanisms.
- Data-preserving production migration, automatic deduplication, or cleanup of historical snapshot rows.
- Any changes to Feishu calculation formulas, parameter dictionaries, calculation behavior, or calculation version semantics.
- Changes to the spot precompute tables and jobs.

## Further Notes

The active PRD-001 execution contract currently classifies report body and report history as deferred. This schema-only work changes the reserved persistence terminology and prepares report storage without implementing the deferred report product feature. Before application-code implementation begins, the active execution contract and plan must be refreshed to include this approved database slice.

The existing full DDL is manually maintained alongside ORM metadata. Both must remain aligned after implementation. The current database setup does not use Alembic as the authoritative schema-creation workflow; the rebuild script and MySQL validation are the execution path for this testing scope.
