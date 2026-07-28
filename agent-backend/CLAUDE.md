# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the backend application.

Read the repository-root `CLAUDE.md` first for PRD authority, cross-end constraints, and Git rules.

## Commands

Run all commands from `agent-backend/`.

```bash
# Install/update dependencies (only through requirements.txt)
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Test wrapper: required because this environment starts Python with sys.stdout=None
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py', '-q']))"
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/calculation/test_task_service_overrides.py', '-q', '-o', 'asyncio_mode=auto']))"
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"

# Start locally; run as a module from this directory
.venv\Scripts\python.exe -m app.main
```

Do not call `python`/`python3`. Use `.venv\Scripts\python.exe`, or `C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe` only when the venv is unavailable.

## Architecture

- `app/core/` provides settings, constants, exceptions, and the `{code,msg,data}` response shell.
- `app/infrastructure/` provides database, Nacos, and web/application-factory concerns.
- `app/modules/platform_access/` 只读取固定 `userId` / `username` 身份 Header 并暴露 `/ir/me`；本地由前端在 ecenter `getInfo` 成功后传递，测试/生产由可信网关认证后注入或覆盖。缺少任一 Header 返回 401。不要添加后端 ecenter 调用、登录、JWT、session 或 RBAC 逻辑。
- `app/modules/calculation/` follows `interface → application → domain`; `domain` cannot depend on FastAPI, database, or external HTTP, while `infrastructure` implements domain ports.
- `infrastructure/data/param_dict.json` is the calculation parameter schema: source, writable/direction, interface mapping, default, and frontend control metadata. Use `ParamDictionary`/`ParamSpec`; do not bypass it with hard-coded parameter behavior.

## Calculation Flow

1. `ParamAssembler` builds a frozen `api_input`: dialogue basics → dictionary defaults → spot-price lookup/inheritance → province revenue structure → mid/long constants → controlled overrides.
2. `CalculationTaskService` copies a Feishu template, `FeishuCalcEngine` writes interface areas and polls `API_META`, then reads output and validates `request_id`/parameter hash.
3. `SnapshotService` stores each successful calculation independently; `report_snapshot` must remain sufficient for historical display.

Controlled overrides accept only dictionary parameters marked `g=1`, `direction=input`, `writable=true`; unknown, output, and null values are ignored. Province is permanently locked in a conversation. Spot prices are recomputed only when node/capacity/power/daily cycles change; otherwise the completed version’s frozen price pair is inherited.

## Feishu Template and Operation-Period Rules

- `FeishuConfig` uses `template_token_15_years` and `template_token_20_years`; do not restore the retired singular `template_token` or add fallback selection.
- `operation_years` defaults to 15. A non-null override must be an exact integer 15 or 20; `null` is ignored by the ordinary override rule.
- After final assembly/overrides, `CalculationTaskService._template_token_for()` selects the token and invokes `FeishuGateway.copy_template(template_token, copy_name)`.
- Preserve `operation_years` in final `api_input`, task response, and `input_snapshot`, but `HttpFeishuGateway.write_input()` must always skip it: templates have fixed periods internally, so never write `API_INPUT!B11` or another interface cell.
- A conversation may mix 15- and 20-year versions. Retry copies once, then reuses the same document token.

## Configuration and Database

- Local defaults: `configs/application.yml`; production-sensitive values come from Nacos/environment. `IR_DB_URL` overrides YAML.
- Runtime/integration defaults use the `ir_agent` test database. Pure tests use in-memory SQLite through `tests/conftest.py`; `tests/db/` deliberately writes test records to the real test database.
- `settings.py` resolves `configs/application.yml` from four directories above `app/core/config/`; changing that traversal can silently load defaults instead of YAML.
- Build schemas manually with `sql/ir_agent_schema.sql`; this project does not use Alembic for schema creation.

## Testing Gotchas

- Use `httpx.ASGITransport` + `AsyncClient` in the main event loop; never `Starlette TestClient`, which can trigger greenlet loading failures under the local application-control policy.
- For async integration tests, pass `-o asyncio_mode=auto` to the pytest wrapper when the project configuration is not applied.
- HTTP headers must be ASCII. The frontend URL-encodes `username`; the backend decodes it before persistence. Never restore anonymous/visitor identity fallback.

在当前会话，当前 main 工作区实施，不创建 worktree、不使用子智能体、不执行 Git 写操作；