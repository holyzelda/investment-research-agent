# 试用账号每日额度控制 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the current workspace with TDD. Do not run Git commands unless the user explicitly requests them.

**Goal:** 根据统一平台 `organization/users` 返回的 `roleKey` 判断试用账号，并为试用账号提供每日 5 次成功测算、5 份报告、5 次成功政策咨询的限制；正常账号完全绕过额度逻辑。额度按 `Asia/Shanghai` 自然日自动重置，额度耗尽仅使用现有普通消息提示，不新增弹窗或联系管理员入口。

**Architecture:** 复用现有 `UserCenterClient` 调用 `/api/v1/organization/users`。新增一个轻量试用角色解析服务和一张按 `user_id` 保存当天计数的用量表。受限写接口各自只解析一次角色，并在试用账号路径执行一次数据库事务内的额度占用；业务成功保留占用，业务失败回退。额度状态接口只用于前端展示，不能作为业务授权缓存。

**Tech Stack:** FastAPI, async SQLAlchemy, MySQL, Vue 3, Pinia, Axios, existing `{code,msg,data}` response envelope, existing Element Plus `ElMessage` handling.

## Final Rules

- 试用资格由统一平台角色实时决定：当前用户自己的 `roles` 中，任一 `roleKey`（字符串值或对象的 `value`）大小写不敏感地以 `freetrial` 结尾，即为试用账号。
- 只检查当前用户自己的 `userId` 记录；不使用 `roleName`、用户名、前端字段或本地账号类型判断。
- 用户拥有多个角色时，任一角色匹配即为试用账号。
- 没有 `freetrial` 角色的账号为正常账号；不创建用量记录、不查询用量、不显示顶部提示、不受额度限制。
- 试用没有期限。管理员在统一平台添加/移除 `freetrial` 角色后，下一次受限请求按新状态执行。
- 试用每日上限：成功测算 5 次、成功报告 5 份、成功政策咨询 5 次。
- 每日边界由后端 `Asia/Shanghai` 日期决定，不使用浏览器时间，不需要定时任务。
- 历史会话、历史测算结果、已有报告、历史咨询和地图/资讯浏览不受限制。
- 分享接口暂不受额度限制。
- 不做额度弹窗、不做“联系管理员开通”按钮、不做支付/套餐/订单/后台。
- 数据库结构部署只提供手动执行的 SQL；不创建 Alembic migration Python 文件。运行时 ORM、Service 和 Router Python 代码仍然需要实现业务逻辑。
- 不执行 `git add`、`git commit`、`git reset`、`git checkout`、分支或 worktree 操作。

## Quota Semantics

### Measurement

`POST /ir/calc/tasks` 在参数和资源归属校验通过后占用一次 `calculation` 额度。

- `status=completed`：保留占用，计为一次成功测算。
- `status=failed` 或请求异常：回退占用，不计次数。
- 首次测算、同会话参数重算、新项目测算和新版本测算均计一次。
- 查看历史任务、结果、输入和会话不计次数。

额度占用不能使用“先读 `used`、再普通加一”的非原子流程。服务应在锁定当天用量行后，在同一个事务中完成跨日重置和 `used < 5` 检查/加一。

### Report

`POST /ir/calc/tasks/{task_id}/report` 对一个新报告生成任务占用一次 `report` 额度。

- 已存在 `completed` 报告：直接返回，不占用。
- 已存在 `generating` 报告任务：返回已有任务，不重复占用。
- 新报告任务创建成功：占用一次额度并记录“本次任务已占用”。
- 后台生成成功：保留占用，计为一份报告。
- 后台生成失败：回退占用，允许后续重试。
- 查看已有报告、报告任务状态和报告 SSE 不占用。

为避免现有异步报告流程无法判断是否需要回退，新增报告生成任务的试用占用标记（例如 `trial_quota_reserved`）。旧数据和正常账号任务按未占用处理。该标记只用于运行时回退，不改变报告归属和报告内容。

本版接受“进程在报告占用后、后台失败回退前突然崩溃”导致一次额度暂时消耗的极端边界，不引入额度流水、恢复扫描或定时回收机制。正常异常路径必须回退。

### Consultation

`POST /ir/policy-market/consultations` 在调用咨询执行器前占用一次 `consultation` 额度。

- 成功创建并保存咨询记录：保留占用。
- 参数校验失败、执行失败或保存失败：回退占用。
- 查看历史咨询和资讯：不占用。

### User-center failure

- 用户中心明确返回当前用户存在 `freetrial`：进入试用额度流程。
- 用户中心明确返回当前用户不存在 `freetrial`：按正常账号放行。
- 用户中心超时、网络异常、响应结构异常、当前用户记录缺失：额度敏感写操作不放行，返回“试用权限校验失败，请稍后重试”。不能在无法确认时按正常账号放行。
- 不涉及额度的只读接口继续沿用当前行为，不因试用角色服务异常扩大数据可见范围。

## File Map

### Create

- `agent-backend/app/modules/trial_quota/__init__.py`
- `agent-backend/app/modules/trial_quota/application/__init__.py`
- `agent-backend/app/modules/trial_quota/application/trial_role_service.py`
- `agent-backend/app/modules/trial_quota/application/trial_quota_service.py`
- `agent-backend/app/modules/trial_quota/infrastructure/__init__.py`
- `agent-backend/app/modules/trial_quota/infrastructure/persistence/__init__.py`
- `agent-backend/app/modules/trial_quota/infrastructure/persistence/orm.py`
- `agent-backend/app/modules/trial_quota/interface/__init__.py`
- `agent-backend/app/modules/trial_quota/interface/router.py`
- `agent-backend/app/modules/trial_quota/interface/deps.py` if dependency wiring is used
- `agent-backend/sql/trial_daily_usage.sql`
- `agent-frontend/src/api/trialQuota.js`
- `agent-frontend/src/store/modules/trialQuota.js`
- `agent-frontend/src/components/TrialQuotaBar.vue`
- `agent-backend/tests/unit/trial_quota/test_trial_role_service.py`
- `agent-backend/tests/unit/trial_quota/test_trial_quota_service.py`
- `agent-backend/tests/db/test_trial_quota_schema.py` or the closest existing database-test location
- `agent-frontend/tests/trial-quota.spec.js`

### Modify

- `agent-backend/app/modules/platform_access/infrastructure/user_center_client.py` only if a narrowly scoped current-user role helper is needed; keep the existing organization-user response behavior intact.
- `agent-backend/app/core/constants.py` if a 503 status constant is required.
- `agent-backend/app/infrastructure/web/router_registry.py` to register the trial-quota router.
- `agent-backend/app/modules/calculation/interface/router.py` to reserve/refund calculation quota around `create_and_run`.
- `agent-backend/app/modules/report/interface/router.py` and `agent-backend/app/modules/report/application/report_generation_service.py` to reserve, persist the reservation marker, retain on success, and refund on failure.
- `agent-backend/app/modules/calculation/infrastructure/persistence/orm.py` only if the report reservation marker is kept on the existing `ReportGenerationTaskORM`; otherwise keep the new usage ORM in the trial-quota module.
- `agent-backend/app/modules/policy_market/interface/router.py` to reserve/refund consultation quota.
- `agent-backend/sql/ir_agent_schema.sql` to document the new table and any report reservation column if this repository's full DDL is kept in sync with incremental SQL.
- `agent-frontend/src/store/index.js` only if the project chooses explicit store registration; follow current Pinia auto-use conventions otherwise.
- `agent-frontend/src/layout/index.vue` or the existing shared shell component to mount the quota bar once at the top level.
- `agent-frontend/src/utils/request.js` only if the existing error-message path cannot display the new 403/503 messages without special handling.
- `agent-frontend/src/views/home/index.vue` and `agent-frontend/src/views/policy-market/index.vue` only where refresh hooks or local disabled-state hints are needed.

## Implementation Tasks

### Task 1: Define role resolution contract

**Files:**

- Create `agent-backend/app/modules/trial_quota/application/trial_role_service.py`
- Modify `agent-backend/app/modules/platform_access/infrastructure/user_center_client.py` only as needed
- Test `agent-backend/tests/unit/trial_quota/test_trial_role_service.py`

**Interfaces:**

- `TrialRoleService.resolve(user_id) -> TrialRoleStatus`
- `TrialRoleStatus.is_trial: bool | None`
- `TrialRoleStatus.available: bool`

`is_trial=None` or `available=False` represents an upstream failure and must not be confused with a confirmed normal account.

- [ ] **Step 1: Write failing role parsing tests**

Cover a current-user record with `roleKey="abc_freetrial"`, mixed-case suffix, a role object with `value="abc_freetrial"`, multiple roles where only one matches, no matching role, missing current-user record, malformed roles, and upstream failure.

- [ ] **Step 2: Run focused backend tests and verify RED**

Run from `agent-backend`:

```powershell
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/trial_quota/test_trial_role_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

- [ ] **Step 3: Implement the smallest resolver**

Reuse `UserCenterClient.fetch_organization_users(user_id)`. Select the record whose normalized `userId` equals the current user ID. Normalize `roleKey` from its supported response shape, lower-case it, and apply `endswith("freetrial")`. Do not alter `UserScopeService` administrator rules.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same command. Confirm upstream failure remains distinguishable from confirmed non-trial.

### Task 2: Add runtime ORM and hand-run SQL

**Files:**

- Create `agent-backend/app/modules/trial_quota/infrastructure/persistence/orm.py`
- Create `agent-backend/sql/trial_daily_usage.sql`
- Modify `agent-backend/sql/ir_agent_schema.sql` if full DDL synchronization is required
- Test schema mapping and basic persistence

**Interfaces:**

`TrialDailyUsageORM` stores one row per user:

```text
user_id               primary key
usage_date            date of the counters
calculation_used      unsigned integer, default 0
report_used           unsigned integer, default 0
consultation_used     unsigned integer, default 0
created_at
updated_at
```

Recommended SQL:

```sql
CREATE TABLE IF NOT EXISTS ir_trial_daily_usage (
    user_id VARCHAR(64) NOT NULL,
    usage_date DATE NOT NULL,
    calculation_used TINYINT UNSIGNED NOT NULL DEFAULT 0,
    report_used TINYINT UNSIGNED NOT NULL DEFAULT 0,
    consultation_used TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='试用账号每日额度使用情况';
```

The SQL file is the deployment migration and is executed manually by the user. Do not create `migrations/versions/*trial*.py`.

If the report reservation marker is persisted on `ir_report_generation_task`, append an explicit `ALTER TABLE` statement to the same SQL file, with an idempotent precondition appropriate for the supported MySQL version. Prefer a nullable/default-false marker to preserve existing rows.

- [ ] **Step 1: Write failing ORM/schema tests**

Assert the ORM maps the expected table and columns, the primary key is `user_id`, and a new usage row starts with zero counters. Keep database tests compatible with the repository's SQLite setup; do not require the manual SQL file to be executed by tests.

- [ ] **Step 2: Implement ORM and SQL only**

Import the ORM from its persistence package so `Base.metadata` registration works in tests. Keep the SQL script standalone and safe to run against the existing `ir_agent` database.

- [ ] **Step 3: Run focused schema tests and inspect SQL**

Run the closest existing database test command plus a static check that the SQL contains `PRIMARY KEY (user_id)` and no trial expiration or account-type columns.

### Task 3: Implement simple atomic daily quota service

**Files:**

- Create `agent-backend/app/modules/trial_quota/application/trial_quota_service.py`
- Test `agent-backend/tests/unit/trial_quota/test_trial_quota_service.py`

**Interfaces:**

```python
TRIAL_DAILY_LIMIT = 5

await service.get_today_status(session, user_id, is_trial=True)
await service.reserve(session, user_id, feature="calculation")
await service.refund(session, user_id, feature="calculation")
```

Supported features are exactly `calculation`, `report`, and `consultation`.

The service should:

1. Compute today with `ZoneInfo("Asia/Shanghai")`.
2. For trial users, create the row if absent.
3. Lock the single user row for the short transaction.
4. If `usage_date` is not today, set today and reset all three counters to zero.
5. Check the selected counter against 5 and increment it atomically.
6. Commit the reservation before the expensive external calculation/AI work.
7. Roll back the reservation in a separate short transaction on normal business failure.
8. Return a small reservation result indicating whether a trial quota was actually reserved, so normal accounts and duplicate report requests are not refunded accidentally.

For SQLite tests, use the same service semantics with `session.refresh`/row access; `with_for_update()` may be a no-op in SQLite. Production MySQL must use a row lock or equivalent conditional update so two concurrent requests cannot both consume the fifth slot.

- [ ] **Step 1: Write failing service tests**

Cover normal accounts bypassing the table, first-day row creation, counter increment, sixth operation rejection, date change resetting all counters, each feature using its own counter, refund restoring one slot, and concurrent/conditional boundary behavior where practical.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/trial_quota/test_trial_quota_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

- [ ] **Step 3: Implement quota service**

Keep the service limited to one table and three counters. Do not add a usage ledger, daily scheduler, plan lookup, trial expiration, or payment abstraction. Use a typed feature-to-column map rather than dynamically interpolated untrusted SQL.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same command and verify that normal users do not create rows.

### Task 4: Expose quota status endpoint

**Files:**

- Create `agent-backend/app/modules/trial_quota/interface/router.py`
- Create `agent-backend/app/modules/trial_quota/interface/deps.py` if needed
- Modify `agent-backend/app/infrastructure/web/router_registry.py`
- Test a new trial-quota endpoint

**Interface:**

```http
GET /ir/trial/quota
```

Confirmed normal account response:

```json
{"isTrial": false}
```

Trial response:

```json
{
  "isTrial": true,
  "usageDate": "2026-09-15",
  "calculation": {"used": 2, "limit": 5, "remaining": 3},
  "report": {"used": 1, "limit": 5, "remaining": 4},
  "consultation": {"used": 3, "limit": 5, "remaining": 2}
}
```

The endpoint may create the current user's zeroed usage row if the user is a confirmed trial user. It must not create a row for a confirmed normal user. On role-resolution failure, return a retryable error rather than `isTrial=false`.

- [ ] **Step 1: Write failing endpoint tests**

Assert exact response shape for trial/normal users, current-day reset behavior, and upstream role lookup failure. Verify the endpoint uses the injected `userId` and does not accept a user ID from query/body.

- [ ] **Step 2: Implement and register the router**

Keep the endpoint under authenticated `/ir` routes. Do not modify public share behavior.

- [ ] **Step 3: Run focused endpoint tests and verify GREEN**

Use the repository's `httpx.ASGITransport + AsyncClient` pattern and explicit `asyncio_mode=auto`.

### Task 5: Integrate measurement quota

**Files:**

- Modify `agent-backend/app/modules/calculation/interface/router.py`
- Test existing calculation endpoint tests and add trial-specific endpoint cases

**Implementation:**

After the route has completed conversation, station, and input validation, resolve the trial role once and call `reserve(..., "calculation")` only for a confirmed trial user. Do not reserve for requests that will fail fast on invalid input.

Wrap `create_and_run` so that:

```text
completed -> keep reservation
failed/exception -> refund reservation
```

Preserve the existing response contract for successful and failed calculation tasks. For quota exhaustion, raise/return HTTP 403 with the existing response envelope and message:

```text
今日测算额度已用完，明日恢复
```

For role-resolution failure, return HTTP 503 with:

```text
试用权限校验失败，请稍后重试
```

Do not put quota decisions in `CalculationTaskService`; keep the expensive calculation orchestration independent and make the route responsible for the single reservation around it.

- [ ] **Step 1: Add failing endpoint tests**

Cover trial users at 1st/5th/6th successful calculation, failed calculation refund, normal user bypass, and role lookup failure. Existing tests that do not configure a trial role should continue to behave as normal users through an explicit mocked confirmed non-trial status.

- [ ] **Step 2: Implement route integration**

Ensure every refund path is guarded by the reservation result. Do not refund normal-account operations.

- [ ] **Step 3: Run focused and existing calculation tests**

Run the trial tests first, then the existing calculation endpoint suite. Investigate any changed call counts to the user-center mock.

### Task 6: Integrate asynchronous report quota

**Files:**

- Modify `agent-backend/app/modules/report/interface/router.py`
- Modify `agent-backend/app/modules/report/application/report_generation_service.py`
- Modify report generation ORM/SQL if using a persisted reservation marker
- Test report generation integration tests and new quota cases

**Implementation:**

At report creation:

1. Verify task ownership and completed calculation status using existing service logic.
2. Check for an existing completed report and return it without quota work.
3. Check for an existing generating task and return it without quota work.
4. Resolve trial role once for a genuinely new report generation task.
5. Reserve one `report` slot for a trial user before committing the new generation task.
6. Mark the generation task as having a trial reservation when applicable.
7. If task creation/start fails before the background job is scheduled, refund immediately.

At background completion:

- On successful `ReportSnapshotORM` persistence, retain the reservation.
- On any failure path that changes the generation to `failed`, refund only when the task's reservation marker is true.
- Keep normal account tasks and historical/pre-existing tasks unaffected.
- Do not count repeated requests for the same task.

Quota exhaustion returns HTTP 403 and:

```text
今日报告额度已用完，明日恢复
```

Do not change report SSE payloads for successful generation. The frontend should continue using the existing report task flow.

- [ ] **Step 1: Add failing report tests**

Cover first and fifth new report tasks, sixth rejected, duplicate completed task not counted, duplicate generating task not counted, failed generation refund, retry after failure, and normal account bypass. Include a test proving the reservation marker prevents refunding a normal or historical task.

- [ ] **Step 2: Implement reservation marker and success/failure hooks**

Keep the marker narrow and nullable/default-false. Do not introduce a general billing ledger. Preserve current startup recovery behavior; document the accepted crash-before-refund edge rather than adding recovery infrastructure.

- [ ] **Step 3: Run report integration tests**

Run the existing report generation integration suite plus the new trial cases. Verify completed report idempotency remains unchanged.

### Task 7: Integrate policy consultation quota

**Files:**

- Modify `agent-backend/app/modules/policy_market/interface/router.py`
- Test `agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py` or the nearest endpoint suite

**Implementation:**

After question normalization and before calling `ConsultationService.create`, resolve role once and reserve `consultation` for confirmed trial users. On successful record creation and commit, keep the reservation. On `ConsultationExecutionError`, validation, or persistence exception, refund the reservation before returning the error.

Quota exhaustion returns HTTP 403 with:

```text
今日政策咨询额度已用完，明日恢复
```

Leave all read-only policy/news/source-file endpoints and consultation history behavior unchanged.

- [ ] **Step 1: Add failing endpoint tests**

Cover first/fifth/sixth requests, successful count, execution failure refund, blank-question behavior without consuming quota, normal account bypass, and role lookup failure.

- [ ] **Step 2: Implement and run focused tests**

Preserve the existing `ConsultationExecutionError` handling and response envelope.

### Task 8: Add frontend quota API, store, and top bar

**Files:**

- Create `agent-frontend/src/api/trialQuota.js`
- Create `agent-frontend/src/store/modules/trialQuota.js`
- Create `agent-frontend/src/components/TrialQuotaBar.vue`
- Modify `agent-frontend/src/layout/index.vue` or the existing shared shell
- Modify `agent-frontend/src/views/home/index.vue` / policy page only for refresh hooks if needed
- Test `agent-frontend/tests/trial-quota.spec.js`

**Interface:**

`getTrialQuota()` calls `GET /ir/trial/quota` and preserves the existing API wrapper convention.

Store state:

```javascript
{
  loaded: false,
  isTrial: false,
  usageDate: '',
  calculation: { used: 0, limit: 5, remaining: 5 },
  report: { used: 0, limit: 5, remaining: 5 },
  consultation: { used: 0, limit: 5, remaining: 5 }
}
```

Load once when the authenticated shell is ready. Refresh after successful calculation, successful report completion, successful consultation, and a page revisit. Do not treat the store as permission enforcement.

Render `TrialQuotaBar` only when `isTrial === true`:

```text
试用账号 · 今日剩余 3 次测算 · 4 份报告 · 2 次咨询
```

When all counters are zero:

```text
试用账号 · 今日额度已用完，明日恢复
```

For normal accounts, render no bar and no placeholder. Do not add a modal, upgrade action, contact button, pricing copy, or normal-account banner.

- [ ] **Step 1: Write failing frontend tests**

Assert the store normalizes the backend response, the bar renders only for trial accounts, normal accounts render no trial text, and a refreshed response updates all three counters.

- [ ] **Step 2: Implement API/store/bar**

Use existing XC tokens and shell spacing. Keep the bar compact and non-blocking. Follow the existing explicit/automatic Vue import convention in the file being modified.

- [ ] **Step 3: Add refresh hooks and verify ordinary error handling**

Use the current `request.js` `ElMessage` path for 403/503 messages. Do not add special modal logic. If the backend rejects a request after the displayed number became stale, show the backend message and let the next normal refresh update the bar.

- [ ] **Step 4: Run focused frontend tests and build**

From `agent-frontend`:

```powershell
npm test -- --run tests/trial-quota.spec.js
npm run build
```

### Task 9: Full verification and manual SQL handoff

**Files:**

- No new implementation files; review all changed files and the SQL script.

- [ ] **Step 1: Run backend focused suites**

From `agent-backend`:

```powershell
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/trial_quota', '-q', '-o', 'asyncio_mode=auto']))"
```

Then run the existing calculation, report, and consultation endpoint/integration suites that were touched.

- [ ] **Step 2: Run frontend tests and production build**

From `agent-frontend`:

```powershell
npm test
npm run build
```

- [ ] **Step 3: Inspect the manual SQL before handoff**

Confirm the script is safe to execute manually, creates the usage table, includes any required report reservation column change, contains no expiration or account-type logic, and does not create an Alembic migration file.

- [ ] **Step 4: Manual acceptance scenarios**

Verify with a test user whose role ends in `freetrial`:

```text
进入系统 -> 顶部显示试用额度
成功测算 5 次 -> 第 6 次收到“今日测算额度已用完，明日恢复”
报告成功 5 份 -> 第 6 份被拒绝
政策咨询成功 5 次 -> 第 6 次被拒绝
失败测算/失败报告/失败咨询 -> 对应次数恢复
进入下一自然日 -> 三个计数重新为 0
```

Verify with a user without the role:

```text
不显示顶部试用提示
不创建 ir_trial_daily_usage 记录
测算、报告、政策咨询不受 5 次限制
```

Verify that removing/adding the role in `organization/users` changes behavior on the next request and that history/read-only pages remain accessible after quota exhaustion.

## Non-goals and Explicit Decisions

- No trial expiration or start date.
- No local account-type column; `freetrial` role is the source of truth.
- No local user/organization/RBAC implementation.
- No payment, order, plan, upgrade URL, contact workflow, or admin UI.
- No usage ledger or audit history.
- No scheduled midnight reset; date rollover is lazy on the first request of the new day.
- No share quota.
- No frontend-only authorization.
- No change to calculation formulas, report content, policy retrieval, or public share access.
