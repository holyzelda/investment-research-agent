# Middle Platform Calculation Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route natural-language storage-project calculation requests through the middle platform while preserving the IR application's conversation, calculation, snapshot, result, and report contracts.

**Architecture:** Add a thin `POST /ir/chat/diag` backend proxy. It creates or validates the IR conversation, caches a per-user middle-platform token, forwards the user identity and internal conversation context to `/api/v1/chat/diag`, persists the returned platform `session_id`, and relays platform SSE frames without changing them. The middle platform invokes the existing `/ir/calc/tasks`; that endpoint gains an interface-only `duration_hours` normalizer so the existing calculation domain still receives only `capacity_mwh` and `power_mw`.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async/MySQL, httpx, Vue 3, Pinia, Vite/Vitest, Fetch Streams, YAML.

## Global Constraints

- The authoritative business requirement is `D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md`; follow repository-root and child `CLAUDE.md` instructions.
- Do not perform `git add`, `git commit`, `git push`, or any other Git write operation.
- Keep the existing `{code,msg,data}` response shell; request validation returns HTTP 400, and resources not owned by the current user return 404.
- IR business requests require non-empty `userId` and URL-encoded `username`; do not restore anonymous/visitor fallback.
- The middle platform owns intent recognition, parameter extraction, follow-up questions, and tool orchestration. Do not duplicate those capabilities in IR.
- IR owns `conversation_id`, calculation versions, snapshots, results, reports, and historical replay. A middle-platform `session_id` is only an internal continuation cursor.
- Middle-platform SSE frames (`event`, `id`, and `data`) must be relayed unchanged. Only IR-generated proxy failures may emit an IR `error` SSE event.
- `duration_hours` is an interface-only input. It must never become a parameter-dictionary entry, a Feishu `API_INPUT` field, or a persisted frozen input field.
- Feishu remains the sole calculator. Do not reimplement financial formulas.
- Backend dependencies are managed only in `agent-backend/requirements.txt`; no dependency is needed for this plan because `httpx` is already present.
- Frontend dependencies are managed only through npm; no new frontend dependency is needed because browser Fetch and `TextDecoder` are built in.
- Run backend tests through `.venv\\Scripts\\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([...]))"`, adding `-o asyncio_mode=auto` for async integration tests when required.
- Schema creation remains manual via `agent-backend/sql/ir_agent_schema.sql`; do not introduce Alembic for this change.

---

## File Structure

- Modify: `agent-backend/app/modules/calculation/infrastructure/persistence/orm.py` — add nullable platform-session mapping to `ConversationORM` and its user-scoped unique index.
- Modify: `agent-backend/sql/ir_agent_schema.sql` — make a fresh schema contain the new conversation column and index.
- Create: `agent-backend/sql/20260723_add_middle_platform_session_id.sql` — idempotent-in-intent operational DDL for the existing `ir_agent.ir_conversation` table; operators run it once before deployment.
- Modify: `agent-backend/app/core/config/settings.py` — add middle-platform configuration and CORS exposed-header configuration.
- Modify: `agent-backend/configs/application.yml` — add local middle-platform endpoint, app ID, app secret, and local declaration-package service-token values.
- Create: `agent-backend/app/modules/middle_platform/application/token_cache.py` — process-local per-user token cache.
- Create: `agent-backend/app/modules/middle_platform/infrastructure/http_client.py` — typed middle-platform token and streaming chat HTTP client.
- Create: `agent-backend/app/modules/middle_platform/application/chat_proxy_service.py` — conversation creation/ownership, platform-session persistence, message assembly, token retry, and SSE relay.
- Create: `agent-backend/app/modules/middle_platform/interface/router.py` — `POST /ir/chat/diag` request model and `StreamingResponse` endpoint.
- Modify: `agent-backend/app/main.py` — register the middle-platform router and configure `CORSMiddleware.expose_headers`.
- Modify: `agent-backend/app/modules/calculation/interface/router.py` — accept optional capacity, power, and `duration_hours`, then normalize into existing `ProjectBasics` before the task service runs.
- Create: `agent-backend/app/modules/calculation/application/input_normalizer.py` — pure calculation-input normalization with conflict validation.
- Modify: `agent-backend/tests/unit/calculation/test_input_normalizer.py` — cover all accepted combinations, defaults, and rejection cases.
- Create: `agent-backend/tests/integration/middle_platform/test_chat_proxy.py` — cover conversation creation, token reuse/retry, exact SSE relay, and platform-session persistence with `httpx.MockTransport`.
- Modify: `agent-backend/tests/db/test_calc_task_api.py` — verify `duration_hours` is accepted at the HTTP boundary and the frozen input contains only normalized capacity/power.
- Create: `agent-backend/configs/middle-platform/ir-agent.yaml.template` — strict platform declaration template without real secrets.
- Create: `agent-backend/tools/render_middle_platform_yaml.py` — read local/Nacos-effective middle-platform configuration and render a non-committed uploadable `ir-agent.yaml` with the real service token and inbound app secret.
- Create: `agent-backend/tests/unit/middle_platform/test_declaration_renderer.py` — verify rendering substitutes secrets in the generated output while the committed template contains no secret value.
- Create: `agent-frontend/src/api/chat.js` — `fetch`-based streaming call that carries existing platform headers, obtains `X-IR-Conversation-Id`, and forwards parsed SSE frames.
- Create: `agent-frontend/src/utils/chatSse.js` — incremental SSE block parser that handles UTF-8 and chunk boundaries.
- Modify: `agent-frontend/src/store/modules/calculation.js` — replace first-message direct calculation submission with chat proxy streaming and apply `answer.data.biz` through the existing result-loading flow.
- Modify: `agent-frontend/src/views/home/index.vue` — retain the existing send hook but make the composer lifecycle work with streaming follow-up/question frames.
- Create: `agent-frontend/tests/chat-sse.spec.js` — unit-test partial/chunked SSE parsing.
- Modify: `agent-frontend/tests/calc-flow.spec.js` — replace direct task creation expectations for natural-language entry with stream-based `/ir/chat/diag` expectations and existing result rendering assertions.

## Task 1: Persist the External Platform Session Mapping

**Files:**
- Modify: `agent-backend/app/modules/calculation/infrastructure/persistence/orm.py:44-53`
- Modify: `agent-backend/sql/ir_agent_schema.sql:8-17`
- Create: `agent-backend/sql/20260723_add_middle_platform_session_id.sql`
- Test: `agent-backend/tests/unit/middle_platform/test_conversation_session_mapping.py`

**Interfaces:**
- Consumes: Existing `ConversationORM` ownership fields `id`, `user_id`, `deleted_at`.
- Produces: `ConversationORM.middle_platform_session_id: str | None`, limited to 255 characters; the database enforces `UNIQUE(user_id, middle_platform_session_id)`.

- [ ] **Step 1: Write the failing ORM persistence tests**

Create `tests/unit/middle_platform/test_conversation_session_mapping.py` with an in-memory SQLAlchemy session fixture and these assertions:

```python
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.calculation.infrastructure.persistence.orm import ConversationORM


@pytest.mark.asyncio
async def test_conversation_persists_nullable_middle_platform_session_id(session):
    conversation = ConversationORM(
        user_id="u-1",
        username="张三",
        title="测试会话",
        middle_platform_session_id="platform-session-1",
    )
    session.add(conversation)
    await session.commit()

    stored = (await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation.id)
    )).scalar_one()
    assert stored.middle_platform_session_id == "platform-session-1"


@pytest.mark.asyncio
async def test_same_user_cannot_bind_same_platform_session_twice(session):
    session.add_all([
        ConversationORM(user_id="u-1", username="张三", middle_platform_session_id="s-1"),
        ConversationORM(user_id="u-1", username="张三", middle_platform_session_id="s-1"),
    ])

    with pytest.raises(IntegrityError):
        await session.commit()
```

Also add a test that two rows with the same `user_id` and `None` session IDs persist successfully, confirming that initial conversations may exist before the platform returns a session ID.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/middle_platform/test_conversation_session_mapping.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: collection/import failure because `ConversationORM` has no `middle_platform_session_id` field or no matching unique constraint.

- [ ] **Step 3: Add the ORM column and index**

In `ConversationORM`, add the column and table argument:

```python
class ConversationORM(_PkTimestamp, Base):
    __tablename__ = "ir_conversation"
    __table_args__ = (
        Index(
            "uq_ir_conversation_user_middle_session",
            "user_id",
            "middle_platform_session_id",
            unique=True,
        ),
    )

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    middle_platform_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
```

Do not add this value to history-list or history-detail DTOs; it is an internal proxy cursor.

- [ ] **Step 4: Update the manual fresh-schema DDL and add operational DDL**

Update `sql/ir_agent_schema.sql` so `ir_conversation` contains:

```sql
middle_platform_session_id VARCHAR(255),
```

and immediately after the existing user index contains:

```sql
CREATE UNIQUE INDEX uq_ir_conversation_user_middle_session
    ON ir_conversation (user_id, middle_platform_session_id);
```

Create `sql/20260723_add_middle_platform_session_id.sql` with the production/test-database migration to be run manually once:

```sql
ALTER TABLE ir_conversation
    ADD COLUMN middle_platform_session_id VARCHAR(255) NULL
    COMMENT '中台 chat/diag 会话标识，仅供后端续接';

CREATE UNIQUE INDEX uq_ir_conversation_user_middle_session
    ON ir_conversation (user_id, middle_platform_session_id);
```

State in the SQL file comment that MySQL permits multiple `NULL` values in this composite unique index, which is necessary for conversations that have not yet received an external session ID.

- [ ] **Step 5: Run the focused test and the existing conversation-history suite**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/middle_platform/test_conversation_session_mapping.py', 'tests/e2e/platform_access/test_identity.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. The existing identity behavior remains unchanged.

## Task 2: Normalize Optional Duration Input at the Existing Task Boundary

**Files:**
- Create: `agent-backend/app/modules/calculation/application/input_normalizer.py`
- Modify: `agent-backend/app/modules/calculation/interface/router.py:116-145`
- Test: `agent-backend/tests/unit/calculation/test_input_normalizer.py`
- Test: `agent-backend/tests/db/test_calc_task_api.py`

**Interfaces:**
- Consumes: `province`, optional positive `capacity_mwh`, optional positive `power_mw`, optional positive `duration_hours`, optional `node_name`, and `voltage_kv`.
- Produces: `normalize_project_basics(...) -> ProjectBasics`, or raises `ValidationException` whose response is HTTP 400.
- Produces: `TaskCreateReq` accepts `duration_hours` but passes only normalized `ProjectBasics` into `CalculationTaskService`.

- [ ] **Step 1: Write pure failing normalization tests**

Create `tests/unit/calculation/test_input_normalizer.py`:

```python
import pytest

from app.core.exceptions import ValidationException
from app.modules.calculation.application.input_normalizer import normalize_project_basics


def test_uses_explicit_capacity_and_power():
    basics = normalize_project_basics(
        province="甘肃", capacity_mwh=800, power_mw=200, duration_hours=None,
        node_name=None, voltage_kv=220,
    )
    assert basics.capacity_mwh == 800
    assert basics.power_mw == 200


def test_derives_capacity_from_power_and_duration():
    basics = normalize_project_basics(
        province="甘肃", capacity_mwh=None, power_mw=100, duration_hours=2,
        node_name=None, voltage_kv=220,
    )
    assert basics.capacity_mwh == 200
    assert basics.power_mw == 100


def test_derives_power_from_capacity_and_duration():
    basics = normalize_project_basics(
        province="甘肃", capacity_mwh=400, power_mw=None, duration_hours=4,
        node_name=None, voltage_kv=220,
    )
    assert basics.capacity_mwh == 400
    assert basics.power_mw == 100


def test_uses_100mw_default_for_duration_only():
    basics = normalize_project_basics(
        province="甘肃", capacity_mwh=None, power_mw=None, duration_hours=2,
        node_name=None, voltage_kv=220,
    )
    assert basics.power_mw == 100
    assert basics.capacity_mwh == 200


@pytest.mark.parametrize("capacity_mwh,power_mw,duration_hours", [
    (150, 100, 2),
    (None, 100, None),
    (200, None, None),
])
def test_rejects_conflicting_or_incomplete_combinations(
    capacity_mwh, power_mw, duration_hours
):
    with pytest.raises(ValidationException):
        normalize_project_basics(
            province="甘肃", capacity_mwh=capacity_mwh, power_mw=power_mw,
            duration_hours=duration_hours, node_name=None, voltage_kv=220,
        )
```

Add a positive three-field test for `capacity_mwh=200`, `power_mw=100`, `duration_hours=2`.

- [ ] **Step 2: Run the focused unit test and confirm it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', '-q']))"
```

Expected: FAIL because `input_normalizer.py` does not exist.

- [ ] **Step 3: Implement the pure normalizer**

Create `input_normalizer.py` with a pure function. Use `math.isclose` for the three-input consistency check and preserve arbitrary positive numeric values:

```python
import math
from typing import Optional

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.models import ProjectBasics

_DEFAULT_POWER_MW = 100.0


def normalize_project_basics(
    *,
    province: str,
    capacity_mwh: Optional[float],
    power_mw: Optional[float],
    duration_hours: Optional[float],
    node_name: Optional[str],
    voltage_kv: int,
) -> ProjectBasics:
    if capacity_mwh is not None and power_mw is not None:
        if duration_hours is not None and not math.isclose(
            capacity_mwh, power_mw * duration_hours, rel_tol=1e-9, abs_tol=1e-9
        ):
            raise ValidationException("项目容量、功率与时长不一致")
    elif power_mw is not None and duration_hours is not None:
        capacity_mwh = power_mw * duration_hours
    elif capacity_mwh is not None and duration_hours is not None:
        power_mw = capacity_mwh / duration_hours
    elif duration_hours is not None:
        power_mw = _DEFAULT_POWER_MW
        capacity_mwh = power_mw * duration_hours
    else:
        raise ValidationException("请同时提供项目容量和功率，或补充系统时长")

    return ProjectBasics(
        province=province,
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        node_name=node_name,
        voltage_kv=voltage_kv,
    )
```

The route model enforces each supplied numeric field is greater than zero. The normalizer is responsible only for combination completeness and consistency.

- [ ] **Step 4: Change `TaskCreateReq` without changing the task-service contract**

Replace its two required fields with optional positive fields and add `duration_hours`:

```python
class TaskCreateReq(BaseModel):
    province: str
    capacity_mwh: Optional[float] = Field(default=None, gt=0)
    power_mw: Optional[float] = Field(default=None, gt=0)
    duration_hours: Optional[float] = Field(default=None, gt=0)
    node_name: Optional[str] = None
    voltage_kv: int = 220
    conversation_id: Optional[int] = None
    param_overrides: Optional[dict] = None
```

In `create_task`, replace the inline `ProjectBasics(...)` construction with:

```python
basics=normalize_project_basics(
    province=req.province,
    capacity_mwh=req.capacity_mwh,
    power_mw=req.power_mw,
    duration_hours=req.duration_hours,
    node_name=req.node_name,
    voltage_kv=req.voltage_kv,
),
```

Do not add `duration_hours` to `ProjectBasics`, `ParamAssembler`, `param_dict.json`, snapshots, or Feishu HTTP writing.

- [ ] **Step 5: Add HTTP regression cases and run tests**

Append to `tests/db/test_calc_task_api.py`:

```python
@pytest.mark.asyncio
async def test_task_accepts_duration_only_and_freezes_normalized_basics(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "duration_hours": 2,
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["input"]["power_mw"] == 100
    assert data["input"]["capacity_mwh"] == 200


@pytest.mark.asyncio
async def test_task_rejects_inconsistent_duration_input(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 150, "power_mw": 100,
        "duration_hours": 2,
    })

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert "不一致" in response.json()["msg"]
```

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', 'tests/db/test_calc_task_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. Existing capacity/power request callers remain valid, and duration-only input produces the pre-existing frozen capacity/power fields.

## Task 3: Add Middle-Platform Configuration and Token Client

**Files:**
- Modify: `agent-backend/app/core/config/settings.py:132-218,221-306`
- Modify: `agent-backend/configs/application.yml`
- Create: `agent-backend/app/modules/middle_platform/application/token_cache.py`
- Create: `agent-backend/app/modules/middle_platform/infrastructure/http_client.py`
- Test: `agent-backend/tests/integration/middle_platform/test_http_client.py`

**Interfaces:**
- Produces: `MiddlePlatformConfig(base_url, app_id, app_secret, tool_auth_token)` on `Settings.middle_platform`.
- Produces: `MiddlePlatformTokenCache.get(key)`, `.put(key, token, expires_in)`, and `.delete(key)`.
- Produces: `MiddlePlatformHttpClient.issue_token(user_id, user_name) -> PlatformAccessToken` and `open_chat(access_token, payload) -> httpx.Response`.

- [ ] **Step 1: Write failing configuration and token-cache tests**

Create `tests/integration/middle_platform/test_http_client.py` with an isolated settings reload and a fake clock. Test these exact behaviors:

```python
def test_middle_platform_settings_read_yaml_or_nacos_overrides():
    settings = get_settings()
    assert settings.middle_platform.app_id == "ir-agent"


def test_token_cache_is_scoped_by_app_id_and_user_id():
    cache = MiddlePlatformTokenCache(now=lambda: 1000)
    cache.put(("ir-agent", "u-1"), "token-1", expires_in=60)
    assert cache.get(("ir-agent", "u-1")) == "token-1"
    assert cache.get(("ir-agent", "u-2")) is None


def test_token_cache_does_not_return_token_inside_refresh_window():
    cache = MiddlePlatformTokenCache(now=lambda: 1000, refresh_skew_seconds=30)
    cache.put(("ir-agent", "u-1"), "token-1", expires_in=20)
    assert cache.get(("ir-agent", "u-1")) is None
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/middle_platform/test_http_client.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because the configuration and middle-platform modules do not exist.

- [ ] **Step 3: Add settings and local configuration**

Add this Pydantic model after `CorsConfig`:

```python
class MiddlePlatformConfig(BaseModel):
    base_url: str = ""
    app_id: str = "ir-agent"
    app_secret: str = ""
    tool_auth_token: str = ""
```

Add `middle_platform: MiddlePlatformConfig = MiddlePlatformConfig()` to `Settings`. In `_build_settings`, use `_business_value` for all four values with these environment-variable names:

```python
IR_MIDDLE_PLATFORM_BASE_URL
IR_MIDDLE_PLATFORM_APP_ID
IR_MIDDLE_PLATFORM_APP_SECRET
IR_MIDDLE_PLATFORM_TOOL_AUTH_TOKEN
```

Add the resulting object to the `Settings(...)` return value.

Append this local-only configuration shape to `configs/application.yml`; replace the empty secret values only in the developer's local configuration, never in source-control content:

```yaml
middle_platform:
  base_url: http://internal-2-58.example.invalid
  app_id: ir-agent
  app_secret: ""
  tool_auth_token: ""
```

The first three fields are the middle-platform client contract. `tool_auth_token` exists only to render the platform-required YAML `backend.auth_value`; IR does not validate it in this implementation.

- [ ] **Step 4: Implement cache and HTTP client**

Create `token_cache.py` with a small in-memory dictionary keyed by `(app_id, user_id)`. Store expiry as `now() + expires_in`; return `None` at or inside a 60-second refresh window. Never persist tokens to the database.

Create `http_client.py` with these dataclasses and methods:

```python
@dataclass(frozen=True)
class PlatformAccessToken:
    value: str
    expires_in: int


class MiddlePlatformHttpClient:
    async def issue_token(self, *, user_id: str, user_name: str) -> PlatformAccessToken: ...
    async def open_chat(self, *, access_token: str, payload: dict) -> httpx.Response: ...
```

`issue_token` POSTs JSON to `f"{base_url}/api/v1/auth/token"`:

```python
{
    "app_id": config.app_id,
    "app_secret": config.app_secret,
    "user_id": user_id,
    "user_name": user_name,
}
```

It requires the middle-platform `{code,msg,data}` body to have `code == 200`, a nonempty `data.access_token`, and a positive `data.expires_in`; otherwise raise `ValidationException("中台令牌获取失败")` without logging credentials.

`open_chat` uses `httpx.AsyncClient.send(..., stream=True)` so the caller owns response cleanup. It sends only `Authorization: Bearer <access_token>` and `Content-Type: application/json` as middle-platform transport headers.

- [ ] **Step 5: Add MockTransport tests and run them**

Test an `/auth/token` mock request has exactly `app_id`, `app_secret`, `user_id`, `user_name`; test parsed token/expires values; test a non-200 business `code` raises `ValidationException`; and test `open_chat` supplies the Bearer header but does not put `app_secret` in the chat request.

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/middle_platform/test_http_client.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

## Task 4: Implement Conversation-Aware Middle-Platform SSE Proxy

**Files:**
- Create: `agent-backend/app/modules/middle_platform/application/chat_proxy_service.py`
- Create: `agent-backend/app/modules/middle_platform/interface/router.py`
- Modify: `agent-backend/app/main.py:22-38,75-85`
- Modify: `agent-backend/app/core/config/settings.py:132-137`
- Test: `agent-backend/tests/integration/middle_platform/test_chat_proxy.py`

**Interfaces:**
- Consumes: `ChatDiagRequest(message: str, conversation_id: int | None)`, `CurrentUser`, `AsyncSession`, `MiddlePlatformHttpClient`, and `MiddlePlatformTokenCache`.
- Produces: `POST /ir/chat/diag` as `text/event-stream`, with header `X-IR-Conversation-Id` and original middle-platform frames.
- Produces: session mapping persistence from `session.session_id` in a `session_start` frame.

- [ ] **Step 1: Write failing proxy integration tests with a fake middle-platform client**

Create `tests/integration/middle_platform/test_chat_proxy.py`. Use `httpx.ASGITransport`, the existing `userId`/`username` request headers, an in-memory SQLite database, and a fake client that emits these exact bytes:

```text
event: session_start
id: frame-1
data: {"event":"session_start","session":{"session_id":"mp-42","chat_id":"chat-1","round":1,"state":"processing","domain":null,"phase":"flow"},"data":{}}

event: question
id: frame-2
data: {"event":"question","session":{"session_id":"mp-42","chat_id":"chat-1","round":1,"state":"processing","domain":"energy_storage_calculation","phase":"flow"},"data":{"text":"请补充项目功率"}}

```

Test all of the following:

```python
async def test_first_chat_creates_ir_conversation_relays_bytes_and_persists_session(...):
    response = await client.post("/ir/chat/diag", json={
        "message": "测算甘肃 2H 储能项目", "conversation_id": None,
    })
    assert response.status_code == 200
    conversation_id = int(response.headers["X-IR-Conversation-Id"])
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == PLATFORM_FRAMES
    conversation = await load_conversation(conversation_id)
    assert conversation.title == "测算甘肃 2H 储能项目"
    assert conversation.middle_platform_session_id == "mp-42"


async def test_existing_conversation_reuses_persisted_platform_session(...):
    # Create an owned ConversationORM with middle_platform_session_id="mp-old".
    # Assert fake client receives payload["session_id"] == "mp-old".
    # Assert payload["message"] ends with '<ir_system_context>{"conversation_id":42}</ir_system_context>'.


async def test_token_business_401_evicts_cache_then_retries_chat_once(...):
    # Cached token produces JSON {"code":401,"msg":"expired","data":null}.
    # Assert exactly one fresh issue_token call and exactly two open_chat calls.


async def test_new_different_session_id_does_not_overwrite_existing_mapping(...):
    # Existing session "mp-old", stream starts "mp-new".
    # Assert relay ends with event: error and database still stores "mp-old".
```

- [ ] **Step 2: Run the focused proxy test and confirm it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/middle_platform/test_chat_proxy.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because `/ir/chat/diag` does not exist.

- [ ] **Step 3: Implement the proxy service lifecycle**

Create `ChatProxyService` with a method:

```python
async def start_chat(
    self,
    *,
    session: AsyncSession,
    user: CurrentUser,
    message: str,
    conversation_id: int | None,
) -> ChatStream:
```

`ChatStream` contains `conversation_id: int` and `body_iterator: AsyncIterator[bytes]`.

Implement the sequence exactly:

1. Trim and validate message length 1–2000 before opening the platform connection.
2. When `conversation_id is None`, create `ConversationORM(user_id=user.user_id, username=user.username, title=message[:30])`, commit it, and use its generated ID.
3. When non-null, use `ConversationHistoryService.require_active_conversation`; this produces current-user ownership and soft-delete 404 behavior.
4. Read `conversation.middle_platform_session_id`; send it as `session_id`, or `None` when it is null.
5. Append exactly one internal suffix to the outgoing platform message:

   ```python
   f'{message}\n<ir_system_context>{{"conversation_id":{conversation.id}}}</ir_system_context>'
   ```

6. Build the `/chat/diag` payload:

   ```python
   {
       "app_id": config.app_id,
       "message": augmented_message,
       "session_id": conversation.middle_platform_session_id,
       "end_user_id": user.user_id,
       "end_user_name": user.username,
       "locale": "zh-CN",
       "entry_type": "open_chat",
       "pinned_domain": None,
       "page_context": None,
       "header": {
           "userId": user.user_id,
           "username": quote(user.username, safe=""),
       },
   }
   ```

   Do not add undeclared chat fields: the middle-platform request model rejects extras.
7. Retrieve a token from cache key `(config.app_id, user.user_id)` or call `issue_token`, then open the stream.
8. If the platform returns an HTTP-200 JSON body with `code == 401`, evict the cache, issue one new token, and retry the exact chat request once. Do not retry any other error or an SSE disconnect.
9. Stream middle-platform bytes unchanged. Buffer only enough bytes to identify blank-line-delimited SSE records. For an `event: session_start` record, parse `data`, obtain `payload["session"]["session_id"]`, validate nonblank string length <= 255, and persist it only if the column is null or equal. Commit before yielding that same original record. If persistence fails or the value conflicts, yield this IR error frame and stop without yielding subsequent platform frames:

   ```text
   event: error
   data: {"code":500,"msg":"中台会话映射保存失败","data":null}

   ```

10. In `finally`, close the streamed httpx response and client.

- [ ] **Step 4: Implement the HTTP route and CORS exposure**

Create `interface/router.py`:

```python
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ir/chat", tags=["middle-platform-chat"])


class ChatDiagRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = Field(default=None, gt=0)
```

The endpoint strips whitespace, raises `ValidationException("消息不能为空")` for empty post-strip content, invokes `ChatProxyService.start_chat`, and returns:

```python
StreamingResponse(
    stream.body_iterator,
    media_type="text/event-stream",
    headers={"X-IR-Conversation-Id": str(stream.conversation_id)},
)
```

Register this router in `main.py` alongside calculation and conversation routers.

Extend `CorsConfig` with:

```python
expose_headers: list[str] = ["X-IR-Conversation-Id"]
```

Pass `expose_headers=settings.cors.expose_headers` to `CORSMiddleware`. Keep existing allowed-origin/method/header behavior unchanged.

- [ ] **Step 5: Run proxy, identity, and existing history tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/middle_platform/test_chat_proxy.py', 'tests/e2e/platform_access/test_identity.py', 'tests/db/test_conversation_history_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. The proxy preserves the platform SSE payload, requires existing identity headers, and keeps existing history APIs unchanged.

## Task 5: Produce the Strict Middle-Platform Declaration Package

**Files:**
- Create: `agent-backend/configs/middle-platform/ir-agent.yaml.template`
- Create: `agent-backend/tools/render_middle_platform_yaml.py`
- Test: `agent-backend/tests/unit/middle_platform/test_declaration_renderer.py`

**Interfaces:**
- Consumes: `get_settings().middle_platform.base_url`, `.app_id`, `.app_secret`, `.tool_auth_token`.
- Produces: non-committed upload artifact named `ir-agent.yaml`, containing no placeholder values and matching the middle-platform declaration package schema.
- Produces: `create_calculation_task` mapped to `POST /ir/calc/tasks` with the existing snake_case request fields and nested `param_overrides`.

- [ ] **Step 1: Write the template-rendering test**

Create `tests/unit/middle_platform/test_declaration_renderer.py`:

```python
from app.modules.middle_platform.application.declaration_renderer import render_declaration


def test_renderer_replaces_all_platform_secrets_without_storing_them_in_template():
    rendered = render_declaration(
        template_text=TEMPLATE,
        app_id="ir-agent",
        app_secret="example-value-0090",
        tool_auth_token="tool-token",
    )

    assert "example-value-0090" in rendered
    assert "Bearer tool-token" in rendered
    assert "example-value-0091" not in rendered
    assert "example-value-0089" not in rendered
    assert "example-value-0090" not in TEMPLATE
    assert "tool-token" not in TEMPLATE
```

Include a YAML parse assertion that `body["param_overrides"]["operation_years"] == "{operation_years}"` and that all tool request keys are snake_case.

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/middle_platform/test_declaration_renderer.py', '-q']))"
```

Expected: FAIL because the template and renderer do not exist.

- [ ] **Step 3: Create the declaration template**

Create `configs/middle-platform/ir-agent.yaml.template` with no real secret values:

```yaml
schema_version: '2'
owner_app_id: ir-agent
display_name: 朱雀投研智能体
description: 面向储能项目的经济性测算，支持从自然语言收集项目省份、功率、容量、时长、节点、电压和运营周期后发起权威飞书测算。

backend:
  base_url: http://127.0.0.1:9089
  auth_header: Authorization
  auth_value: "Bearer example-value-0089"

inbound:
  app_secret: "example-value-0091"
  enabled: true

domains:
  - domain_code: energy_storage_calculation
    display_name: 储能项目测算
    description: 收集储能项目省份、功率、容量或系统时长等信息，调用测算服务并返回结构化测算结果。
    executor:
      mode: autonomous
    domain_lexicon:
      primary_terms: [储能测算, 项目测算, 经济性测算, 收益测算]
      secondary_terms: [MW, MWh, 功率, 容量, 时长, 运营期, 电压等级, 节点]
    prompts:
      domain_guard: |
        调用 create_calculation_task 前必须得到 province，且必须提供以下任一规模组合：
        1. power_mw 与 capacity_mwh；
        2. power_mw 与 duration_hours；
        3. capacity_mwh 与 duration_hours；
        4. duration_hours 单独存在时允许调用，后端会采用默认功率。
        用户同时给出容量、功率和时长且三者不一致时，必须追问，不得自行覆盖。
        operation_years 未提及时不填该参数；明确提及时仅接受 15 或 20。
        voltage_kv 未提及时按 220；明确提及时仅接受 110 或 220。
        conversation_id 从消息中的 ir_system_context 提取，必须原样传入工具请求。
    tools:
      - name: create_calculation_task
        description: 发起储能项目飞书经济性测算，返回任务、会话、版本和冻结输入。
        enable_ai_summary: false
        params:
          province: {required: true}
          capacity_mwh: {type: float}
          power_mw: {type: float}
          duration_hours: {type: float}
          node_name: {type: str}
          voltage_kv: {type: int, default: 220, enum: [110, 220]}
          operation_years: {type: int, enum: [15, 20]}
          conversation_id: {type: int, required: true}
        http:
          method: POST
          path: /ir/calc/tasks
          body:
            province: "{province}"
            capacity_mwh: "{capacity_mwh}"
            power_mw: "{power_mw}"
            duration_hours: "{duration_hours}"
            node_name: "{node_name}"
            voltage_kv: "{voltage_kv}"
            conversation_id: "{conversation_id}"
            param_overrides:
              operation_years: "{operation_years}"
        answer_type: energy_storage.calculation_task
        render_hint: 保留后端完整结构化响应，不重算、不改写财务指标。
```

Do not set `sensitive: true`: the user explicitly chose no second confirmation before calculation.

- [ ] **Step 4: Implement a minimal local declaration renderer**

Create `app/modules/middle_platform/application/declaration_renderer.py` with:

```python
def render_declaration(
    *, template_text: str, app_id: str, app_secret: str, tool_auth_token: str
) -> str:
    return (
        template_text
        .replace("owner_app_id: ir-agent", f"owner_app_id: {app_id}")
        .replace("example-value-0091", app_secret)
        .replace("example-value-0089", tool_auth_token)
    )
```

Create `tools/render_middle_platform_yaml.py` with a top-level `OUTPUT_PATH` constant set to `configs/middle-platform/ir-agent.local.yaml`. It loads `get_settings().middle_platform`, rejects blank `app_secret` or `tool_auth_token` with a clear stderr message and non-zero exit, writes the rendered output, and prints the absolute output path. Add `ir-agent.local.yaml` to the repository `.gitignore` if it is not already ignored.

- [ ] **Step 5: Run renderer tests and validate generated YAML locally**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/middle_platform/test_declaration_renderer.py', '-q']))"
.venv\Scripts\python.exe tools\render_middle_platform_yaml.py
```

Expected: the test passes; the second command either prints the generated local YAML path when local secrets are configured or fails without emitting secret values when they are blank. Do not upload the declaration package in this task.

## Task 6: Add Frontend Stream Parsing and Chat API

**Files:**
- Create: `agent-frontend/src/utils/chatSse.js`
- Create: `agent-frontend/src/api/chat.js`
- Test: `agent-frontend/tests/chat-sse.spec.js`

**Interfaces:**
- Produces: `createSseParser(onFrame)` accepting `Uint8Array` chunks and invoking `onFrame({ event, id, data, raw })` only for complete SSE records.
- Produces: `streamChatDiag({ message, conversationId, onConversationId, onFrame, signal })` that calls `/ir/chat/diag` and reads the stream with browser Fetch.

- [ ] **Step 1: Write failing chunk-boundary parser tests**

Create `tests/chat-sse.spec.js`:

```js
import { describe, expect, it } from 'vitest'
import { createSseParser } from '@/utils/chatSse'


describe('chat SSE parser', () => {
  it('emits one parsed frame when UTF-8 SSE data arrives across chunks', () => {
    const frames = []
    const parser = createSseParser((frame) => frames.push(frame))
    const encoder = new TextEncoder()

    parser.push(encoder.encode('event: session_start\nid: f1\ndata: {"event":"session_'))
    parser.push(encoder.encode('start","session":{"session_id":"mp-1"},"data":{}}\n\n'))
    parser.finish()

    expect(frames).toEqual([{
      event: 'session_start',
      id: 'f1',
      data: { event: 'session_start', session: { session_id: 'mp-1' }, data: {} },
      raw: 'event: session_start\nid: f1\ndata: {"event":"session_start","session":{"session_id":"mp-1"},"data":{}}',
    }])
  })

  it('does not emit an incomplete trailing record', () => {
    const frames = []
    const parser = createSseParser((frame) => frames.push(frame))
    parser.push(new TextEncoder().encode('event: thinking\ndata: {"event":"thinking"}'))
    parser.finish()
    expect(frames).toEqual([])
  })
})
```

- [ ] **Step 2: Run the parser test and confirm it fails**

Run:

```bash
npm test -- --run tests/chat-sse.spec.js
```

Expected: FAIL because `chatSse.js` does not exist.

- [ ] **Step 3: Implement the incremental parser**

Create `chatSse.js`. Keep a `TextDecoder`, append decoded text into a buffer, normalize `\r\n` to `\n`, split complete records on `\n\n`, and parse only `event:`, `id:`, and `data:` lines. The parser must JSON-parse `data:` and include the unmodified record body as `raw`; malformed complete JSON must throw an Error so the caller can terminate the active UI request instead of silently using corrupt data.

- [ ] **Step 4: Add the Fetch streaming client**

Create `src/api/chat.js` using `getToken` and `getUserIdentity` from `@/utils/auth`. It must use the same IR API base URL as Axios:

```js
const baseUrl = import.meta.env.VITE_APP_BASE_API || '/gateway/ir-agent/'
```

Build headers using existing conventions:

```js
const { userId, username } = getUserIdentity()
const headers = { 'Content-Type': 'application/json;charset=utf-8' }
const token = getToken()
if (token) headers.Authorization = `Bearer ${token}`
if (userId) headers.userId = userId
if (username) headers.username = encodeURIComponent(username)
```

Call Fetch with `credentials: 'include'`, body:

```js
JSON.stringify({ message, conversation_id: conversationId ?? null })
```

On a successful response, read `X-IR-Conversation-Id`; convert it to `Number`, require a positive finite value, and call `onConversationId(id)` before reading the body. Read `response.body.getReader()` into `createSseParser(onFrame)`. For HTTP error responses, parse `{code,msg,data}` when possible and throw `Error(msg)`.

- [ ] **Step 5: Run the focused frontend parser test**

Run:

```bash
npm test -- --run tests/chat-sse.spec.js
```

Expected: PASS.

## Task 7: Switch the Natural-Language Entry Flow to the Chat Proxy

**Files:**
- Modify: `agent-frontend/src/store/modules/calculation.js:1-13,158-202,251-292`
- Modify: `agent-frontend/src/views/home/index.vue:176-180`
- Modify: `agent-frontend/tests/calc-flow.spec.js`
- Modify: `agent-frontend/tests/conversation-history.spec.js`

**Interfaces:**
- Consumes: `streamChatDiag` and SSE frames from Task 6.
- Produces: `sendAndCalculate(text)` sends the original user message to `/ir/chat/diag`, keeps the returned `conversationId`, handles `question`/`interrupt`/`done` as terminal frames, and applies direct `answer.data.biz` calculation responses using existing `getCalculationResult` and result-card state.

- [ ] **Step 1: Rewrite the natural-language flow test around streamed chat**

In `tests/calc-flow.spec.js`, mock `streamChatDiag` rather than `createCalculationTask`. Add this test:

```js
it('sends natural-language input to chat proxy and applies answer biz through existing result loading', async () => {
  api.streamChatDiag.mockImplementation(async ({ onConversationId, onFrame }) => {
    onConversationId(42)
    onFrame({ event: 'answer', data: {
      event: 'answer',
      session: { session_id: 'mp-42' },
      data: {
        answer: '已完成测算。',
        biz: {
          code: 200,
          msg: 'success',
          data: { conversationId: 42, taskId: 9, version: 'V1', status: 'completed', input: { province: '甘肃' } },
        },
      },
    } })
    onFrame({ event: 'done', data: { event: 'done', session: { session_id: 'mp-42' }, data: {} } })
  })
  api.getCalculationResult.mockResolvedValue({ data: result })
  const store = useCalculationStore()

  await store.sendAndCalculate('测算甘肃 200MW/800MWh')

  expect(api.streamChatDiag).toHaveBeenCalledWith(expect.objectContaining({
    message: '测算甘肃 200MW/800MWh',
    conversationId: null,
  }))
  expect(store.conversationId).toBe(42)
  expect(api.getCalculationResult).toHaveBeenCalledWith(9)
  expect(store.versions[0]).toMatchObject({ conversationId: 42, taskId: 9, version: 'V1', result })
})
```

Add a second test where `question` is the terminal frame: it sets the assistant text from `frame.data.data.text`, leaves `conversationId` at the response-header value, sets `responding` false, and does not call `getCalculationResult`.

- [ ] **Step 2: Run the focused frontend flow test and confirm it fails**

Run:

```bash
npm test -- --run tests/calc-flow.spec.js
```

Expected: FAIL because the store still calls `createCalculationTask` directly for natural-language input.

- [ ] **Step 3: Replace only the natural-language send path**

Keep `recalculate()` and `_submitAndTrack()` unchanged: parameter-panel recalculation remains a direct existing task API workflow.

Replace `sendAndCalculate` so it:

1. Rejects blank input and concurrent calls as today.
2. Pushes the original user text to `messages`.
3. Sets `responding = true` and inserts one pending assistant text message `正在理解测算需求…`.
4. Calls `streamChatDiag({ message: content, conversationId: this.conversationId, ... })`.
5. In `onConversationId`, sets `this.conversationId` exactly once.
6. In `onFrame`:
   - `thinking`: replace the pending text with `frame.data.data?.text || '正在处理…'`.
   - `question` or `interrupt`: replace the pending text with `frame.data.data?.text || '请补充测算信息。'`, mark terminal.
   - `answer`: set pending text to `frame.data.data?.answer || '已收到中台响应。'`; if `frame.data.data?.biz` is a direct IR shell, pass it to a new private `_applyChatCalculationBiz(biz, pending)` method.
   - `done`: mark terminal.
7. `_applyChatCalculationBiz` performs the existing result behavior only for direct IR task shells:

```js
if (biz.code !== 200) {
  pending.text = biz.msg || '测算请求失败'
  return
}
const task = biz.data || {}
if (task.status === 'failed') {
  pending.text = failureText(task.error?.message, task.error?.requestId)
  return
}
if (task.status !== 'completed' || !task.taskId) return
const result = (await getCalculationResult(task.taskId)).data || {}
const entry = {
  conversationId: task.conversationId,
  taskId: task.taskId,
  version: task.version,
  status: 'completed',
  result,
  input: task.input,
}
this.versions.push(entry)
this.selectedVersion = task.version
pending.kind = 'result'
pending.text = undefined
pending.result = result
pending.version = task.version
pending.input = task.input
this.loadHistory().catch(() => {})
if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
```

8. On an exception, replace pending text with `failureText(error.message)`; always clear `responding` when `streamChatDiag` resolves, rejects, or a terminal event arrives.

Do not add client-side MW/MWh/operation-years extraction to this path. Remove `extractMinInput` only after no natural-language caller imports it; retain it if any existing unit test or UI still consumes it.

- [ ] **Step 4: Preserve history replay and update its regression test**

In `tests/conversation-history.spec.js`, replace the “next calculation” assertion that expects `createCalculationTask` with one that expects `streamChatDiag` to receive `conversationId: 7`. Continue asserting `openConversation(7)` itself does not call the chat API: opening historical results must remain a local IR read only.

- [ ] **Step 5: Run focused frontend tests and build**

Run:

```bash
npm test -- --run tests/chat-sse.spec.js tests/calc-flow.spec.js tests/conversation-history.spec.js
npm run build
```

Expected: all focused tests pass and Vite completes the production build.

## Task 8: Run the End-to-End Local Verification Sequence

**Files:**
- Modify only if failures reveal a contract mismatch in files from Tasks 1–7.
- Test: backend and frontend suites listed below.

**Interfaces:**
- Verifies: `conversation_id -> middle_platform_session_id -> /ir/calc/tasks -> existing snapshots/results/reports`.

- [ ] **Step 1: Render but do not commit the local declaration package**

Set local `middle_platform.app_secret` and `middle_platform.tool_auth_token` in `agent-backend/configs/application.yml` or equivalent Nacos override, then run:

```bash
.venv\Scripts\python.exe tools\render_middle_platform_yaml.py
```

Expected: a local ignored `configs/middle-platform/ir-agent.local.yaml` file is generated. Inspect its top-level `schema_version`, `owner_app_id`, `backend`, `inbound`, and `domains` fields before uploading through the platform's documented declaration-package flow.

- [ ] **Step 2: Run backend regression suites**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', 'tests/unit/middle_platform/test_conversation_session_mapping.py', 'tests/unit/middle_platform/test_declaration_renderer.py', 'tests/integration/middle_platform/test_http_client.py', 'tests/integration/middle_platform/test_chat_proxy.py', 'tests/e2e/platform_access/test_identity.py', 'tests/db/test_calc_task_api.py', 'tests/db/test_conversation_history_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

- [ ] **Step 3: Run frontend regression suites**

Run from `agent-frontend/`:

```bash
npm test -- --run tests/chat-sse.spec.js tests/calc-flow.spec.js tests/conversation-history.spec.js tests/request-auth.spec.js tests/session-info.spec.js
npm run build
```

Expected: PASS and successful build.

- [ ] **Step 4: Perform manual platform smoke verification**

1. Start IR backend on port 9089 and frontend with its configured development server.
2. Upload the generated `ir-agent.local.yaml` using the middle platform’s declaration-package upload procedure.
3. Send `测算甘肃 2H 储能项目` from the IR UI. Confirm the IR proxy receives `X-IR-Conversation-Id`, the middle platform asks for any missing field, and subsequent reply continues the same platform session.
4. Complete the required parameters. Confirm the middle platform calls `POST http://127.0.0.1:9089/ir/calc/tasks` with `userId`, encoded `username`, and the IR `conversation_id` in body.
5. Confirm `answer.data.biz` is the complete IR response shell, the existing result card renders, and the version appears in the right-side list.
6. Refresh/open the same IR historical conversation. Confirm historical result/report replay does not call `/chat/diag`.
7. Send a new message in that historical conversation. Confirm IR reads and reuses the persisted `middle_platform_session_id`.

---

## Plan Self-Review

- **Spec coverage:** Tasks 1 and 4 implement IR conversation/session persistence and continuation; Task 2 implements interface-only duration normalization; Task 3 implements configuration and per-user token cache/retry; Task 5 implements strict YAML generation and nested `param_overrides`; Tasks 6–7 implement Fetch/SSE frontend integration and reuse of current result/history/report behavior; Task 8 validates the complete chain.
- **Deliberate exclusions:** No title-edit endpoint and no full user/assistant chat-message persistence are included; both are third-stage scope. No fixed Bearer validation is added because the confirmed first-stage IR boundary only requires `userId` and `username`.
- **Type consistency:** The backend uses snake_case request fields and returns existing camelCase task data. The frontend API receives `conversationId`, while backend request models use `conversation_id`. `duration_hours` stops at `normalize_project_basics` and never enters `ProjectBasics` persistence or Feishu writes.
- **No Git writes:** The plan intentionally omits commits despite generic planning guidance because repository instructions prohibit Git write operations unless the user explicitly requests them.
