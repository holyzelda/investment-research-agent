# Report AI Parallel Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Subagents and worktrees are prohibited for this repository session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate all five independent report AI sections with configurable five-way concurrency while issuing at most one middle-platform Token request for a cold-cache batch.

**Architecture:** `ReportGenerationService` will run one isolated coroutine per AI rule behind an `asyncio.Semaphore`, collect every generated/fallback result, and rebuild `aiSections` in rule order. `ModelPoolReportAiClient` will coalesce concurrent Token cache misses by `(app_id, user_id)` into one shared in-flight `asyncio.Task`; model calls remain independent and concurrent.

**Tech Stack:** Python 3.13, asyncio, FastAPI application services, Pydantic settings, httpx, async SQLAlchemy, pytest/pytest-asyncio.

## Global Constraints

- Work in the current `main` workspace; do not create a worktree or use subagents.
- Do not execute `git add`, `git commit`, `git push`, or any other Git write operation.
- Use `.venv\Scripts\python.exe`; never invoke `python` or `python3`.
- Run pytest through the required stdout wrapper because `sys.stdout` starts as `None`.
- Default report-model concurrency is exactly `5`; it must remain configurable as a positive integer.
- Five sections are independent; `investment_conclusion` must continue to use frozen structured facts rather than other AI section text.
- Do not perform concurrent operations on a shared SQLAlchemy `AsyncSession`.
- Preserve single-section fallback behavior and existing stable AI failure codes.
- Do not add automatic model retries or per-section database progress writes.
- Historical report reads and PDF export must remain snapshot-only.

---

## File Map

- Modify `agent-backend/app/core/config/settings.py`: define and load `report_model_concurrency`.
- Modify `agent-backend/configs/application.yml`: set the local default concurrency to 5.
- Modify `agent-backend/app/modules/report/application/factory.py`: inject configured concurrency into the report service.
- Modify `agent-backend/app/modules/report/application/report_generation_service.py`: execute section workers with bounded concurrency and stable result ordering.
- Modify `agent-backend/app/modules/report/infrastructure/model_pool_ai_client.py`: coalesce cold-cache Token acquisition.
- Modify `agent-backend/tests/integration/report/test_report_generation_service.py`: verify overlap, configured bounds, ordering, and failure isolation.
- Create `agent-backend/tests/unit/report/test_model_pool_ai_client.py`: verify Token single-flight success/failure and warm-cache behavior.
- Modify `agent-backend/tests/unit/report/test_model_pool_http_client.py`: align fixtures with the actual nested `data.content` model-pool response contract so the relevant suite is runnable.

### Task 1: Add Configurable Report AI Concurrency

**Files:**
- Modify: `agent-backend/app/core/config/settings.py:140-150,280-298`
- Modify: `agent-backend/configs/application.yml:36-43`
- Modify: `agent-backend/app/modules/report/application/factory.py:1-7`
- Test: `agent-backend/tests/unit/report/test_report_generation_config.py`

**Interfaces:**
- Produces: `MiddlePlatformConfig.report_model_concurrency: int`, validated with `ge=1` and default `5`.
- Produces: `ReportGenerationService(ai_client, *, ai_concurrency: int = 5)` construction used by Tasks 2 and 3.
- Consumes: existing `_business_value()` precedence: Nacos → environment → YAML → model default.

- [ ] **Step 1: Write configuration tests that fail before the field exists**

Create `tests/unit/report/test_report_generation_config.py`:

```python
import pytest
from pydantic import ValidationError

from app.core.config.settings import MiddlePlatformConfig


def test_report_model_concurrency_defaults_to_five():
    assert MiddlePlatformConfig().report_model_concurrency == 5


def test_report_model_concurrency_must_be_positive():
    with pytest.raises(ValidationError):
        MiddlePlatformConfig(report_model_concurrency=0)
```

- [ ] **Step 2: Run the focused test and verify red state**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/report/test_report_generation_config.py', '-q']))"
```

Expected: the default-field test fails with `AttributeError` or the constructor rejects the unknown behavior expectation.

- [ ] **Step 3: Add the typed config field and loading precedence**

In `MiddlePlatformConfig`, add:

```python
report_model_concurrency: int = Field(default=5, ge=1)
```

In `_build_settings()` where `MiddlePlatformConfig(...)` is assembled, add:

```python
report_model_concurrency=int(_business_value(
    "IR_MIDDLE_PLATFORM_REPORT_MODEL_CONCURRENCY",
    y,
    ["middle_platform", "report_model_concurrency"],
    _mpd.report_model_concurrency,
)),
```

In `configs/application.yml`, add directly after `report_model_timeout_seconds`:

```yaml
  report_model_concurrency: 5
```

- [ ] **Step 4: Extend the service constructor and wire the factory**

Change the report service constructor to validate its direct-test/default input too:

```python
def __init__(self, ai_client, *, ai_concurrency: int = 5):
    if ai_concurrency < 1:
        raise ValueError("报告 AI 并发数必须大于 0")
    self._ai_client = ai_client
    self._ai_concurrency = ai_concurrency
    self._history = ConversationHistoryService()
```

Change the factory to reuse one settings value consistently:

```python
def build_report_generation_service():
    config = get_settings().middle_platform
    return ReportGenerationService(
        ai_client=ModelPoolReportAiClient(config),
        ai_concurrency=config.report_model_concurrency,
    )
```

- [ ] **Step 5: Run configuration tests and existing settings tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/report/test_report_generation_config.py', 'tests/unit/test_settings.py', '-q']))"
```

Expected: new tests pass. If `tests/unit/test_settings.py` does not exist, run only the new test and report that the optional existing path was absent rather than substituting an unrelated suite.

---

### Task 2: Coalesce Concurrent Token Acquisition

**Files:**
- Modify: `agent-backend/app/modules/report/infrastructure/model_pool_ai_client.py:1-41`
- Create: `agent-backend/tests/unit/report/test_model_pool_ai_client.py`
- Modify: `agent-backend/tests/unit/report/test_model_pool_http_client.py:11-54`

**Interfaces:**
- Produces: `ModelPoolReportAiClient._get_access_token(*, user_id: str, username: str) -> str`.
- Produces: per-client `_token_tasks: dict[tuple[str, str], asyncio.Task[str]]` containing only currently running Token requests.
- Consumes: `MiddlePlatformTokenCache.get/put` and `MiddlePlatformHttpClient.issue_token`.
- Preserves: public `generate_section(rule, context, *, user_id="", username="") -> str`.

- [ ] **Step 1: Write a controllable low-level fake and cold-cache single-flight test**

Create `tests/unit/report/test_model_pool_ai_client.py` with imports and helpers:

```python
import asyncio
from collections import defaultdict

import pytest

from app.core.config.settings import MiddlePlatformConfig
from app.modules.middle_platform.application.token_cache import MiddlePlatformTokenCache
from app.modules.middle_platform.infrastructure.http_client import PlatformAccessToken
from app.modules.report.infrastructure.model_pool_ai_client import ModelPoolReportAiClient


RULE = {
    "key": "debt_service_coverage",
    "title": "偿债能力",
    "prompt": "仅根据冻结资料生成正文。",
    "maxWords": 200,
    "forbiddenMetrics": [],
}


class BlockingMiddlePlatformClient:
    def __init__(self):
        self.issue_calls = 0
        self.model_calls = 0
        self.issue_started = asyncio.Event()
        self.release_issue = asyncio.Event()
        self.fail_issue = False

    async def issue_token(self, *, user_id, user_name):
        self.issue_calls += 1
        self.issue_started.set()
        await self.release_issue.wait()
        if self.fail_issue:
            raise RuntimeError("鉴权不可用")
        return PlatformAccessToken(value="shared-token", expires_in=3600)

    async def chat_report_model(self, *, access_token, payload):
        self.model_calls += 1
        assert access_token == "shared-token"
        return "冻结正文"


async def _five_calls(client):
    return await asyncio.gather(*[
        client.generate_section(RULE, {"index": index}, user_id="u1", username="用户")
        for index in range(5)
    ])


@pytest.mark.asyncio
async def test_concurrent_sections_issue_one_token_and_call_model_five_times():
    http_client = BlockingMiddlePlatformClient()
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(),
        client=http_client,
        token_cache=MiddlePlatformTokenCache(),
    )

    pending = asyncio.create_task(_five_calls(client))
    await asyncio.wait_for(http_client.issue_started.wait(), timeout=1)
    await asyncio.sleep(0)
    assert http_client.issue_calls == 1
    http_client.release_issue.set()

    assert await pending == ["冻结正文"] * 5
    assert http_client.issue_calls == 1
    assert http_client.model_calls == 5
```

- [ ] **Step 2: Add warm-cache and shared-failure tests**

Append:

```python
@pytest.mark.asyncio
async def test_cached_token_skips_token_issue():
    cache = MiddlePlatformTokenCache()
    cache.put(("ir_agent", "u1"), "shared-token", 3600)
    http_client = BlockingMiddlePlatformClient()
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(), client=http_client, token_cache=cache
    )

    assert await _five_calls(client) == ["冻结正文"] * 5
    assert http_client.issue_calls == 0
    assert http_client.model_calls == 5


@pytest.mark.asyncio
async def test_concurrent_sections_share_token_issue_failure_once():
    http_client = BlockingMiddlePlatformClient()
    http_client.fail_issue = True
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(),
        client=http_client,
        token_cache=MiddlePlatformTokenCache(),
    )

    pending = asyncio.create_task(asyncio.gather(*[
        client.generate_section(RULE, {}, user_id="u1", username="用户")
        for _ in range(5)
    ], return_exceptions=True))
    await asyncio.wait_for(http_client.issue_started.wait(), timeout=1)
    await asyncio.sleep(0)
    assert http_client.issue_calls == 1
    http_client.release_issue.set()

    results = await pending
    assert http_client.issue_calls == 1
    assert http_client.model_calls == 0
    assert all(isinstance(result, RuntimeError) for result in results)
```

During implementation, construct the failure gather as a coroutine helper rather than passing the `_GatheringFuture` directly to `create_task` if the local Python runtime rejects it:

```python
async def _five_failed_calls(client):
    return await asyncio.gather(*[
        client.generate_section(RULE, {}, user_id="u1", username="用户")
        for _ in range(5)
    ], return_exceptions=True)
```

Then use `pending = asyncio.create_task(_five_failed_calls(client))`.

- [ ] **Step 3: Run the single-flight tests and verify red state**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/report/test_model_pool_ai_client.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: the cold-cache tests observe `issue_calls > 1` before the release or otherwise fail because concurrent cache misses are not coalesced.

- [ ] **Step 4: Implement shared in-flight Token tasks**

Update `model_pool_ai_client.py`:

```python
import asyncio
```

Initialize the in-flight registry:

```python
self._token_tasks: dict[tuple[str, str], asyncio.Task[str]] = {}
```

Extract Token acquisition:

```python
async def _issue_and_cache_token(
    self, token_key: tuple[str, str], *, user_id: str, username: str
) -> str:
    issued = await self._client.issue_token(user_id=user_id, user_name=username)
    self._token_cache.put(token_key, issued.value, issued.expires_in)
    return issued.value

async def _get_access_token(self, *, user_id: str, username: str) -> str:
    token_key = (self._config.app_id, user_id)
    token = self._token_cache.get(token_key)
    if token is not None:
        return token

    task = self._token_tasks.get(token_key)
    if task is None:
        task = asyncio.create_task(self._issue_and_cache_token(
            token_key, user_id=user_id, username=username
        ))
        self._token_tasks[token_key] = task

    try:
        return await asyncio.shield(task)
    finally:
        if task.done() and self._token_tasks.get(token_key) is task:
            self._token_tasks.pop(token_key, None)
```

Replace the inline cache-miss block in `generate_section()` with:

```python
token = await self._get_access_token(user_id=user_id, username=username)
```

There is no `await` between checking `_token_tasks` and assigning the new task, so same-event-loop section coroutines cannot create duplicate in-flight tasks. `asyncio.shield()` prevents cancellation of one waiter from cancelling the shared Token request.

- [ ] **Step 5: Align HTTP-client fixtures with the actual response shape**

In `test_model_pool_http_client.py`, change the success response to:

```python
return httpx.Response(200, json={
    "code": 200,
    "msg": "操作成功",
    "data": {"content": "  冻结正文  "},
})
```

Change the invalid response fixture to:

```python
httpx.Response(200, json={"code": 200, "data": {"content": " "}})
```

This matches `MiddlePlatformHttpClient.chat_report_model()` reading `body["data"]["content"]` and avoids an unrelated stale-test failure.

- [ ] **Step 6: Run the Token and HTTP adapter tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/report/test_model_pool_ai_client.py', 'tests/unit/report/test_model_pool_http_client.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: all tests pass; cold-cache success and failure each report exactly one Token issue call.

---

### Task 3: Execute AI Sections with Stable Bounded Concurrency

**Files:**
- Modify: `agent-backend/app/modules/report/application/report_generation_service.py:1-202`
- Modify: `agent-backend/tests/integration/report/test_report_generation_service.py:1-143`

**Interfaces:**
- Consumes: `ReportGenerationService(ai_client, *, ai_concurrency: int = 5)` from Task 1.
- Produces: `_generate_one_ai_section(rule, payload, *, user_id, username, semaphore) -> tuple[str, dict]`.
- Preserves: `_generate_ai_sections(payload, *, user_id, username) -> dict` and its final rule-ordered mapping.
- Preserves: `_validate_ai_text`, `_ai_failure_code`, `_fallback`, report snapshot transaction, and whole-step progress behavior.

- [ ] **Step 1: Add a blocking AI client that proves all five calls overlap**

At the top of `test_report_generation_service.py`, add `import asyncio`. Add this helper below `_completed_task`:

```python
class BlockingAiClient:
    def __init__(self, expected_active):
        self.expected_active = expected_active
        self.active = 0
        self.max_active = 0
        self.started = 0
        self.batch_started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_section(self, rule, context, *, user_id="", username=""):
        self.active += 1
        self.started += 1
        self.max_active = max(self.max_active, self.active)
        if self.active == self.expected_active:
            self.batch_started.set()
        try:
            await self.release.wait()
            return f"{rule['key']} 正文"
        finally:
            self.active -= 1
```

Add a direct application-service test, avoiding database setup because `_generate_ai_sections()` performs no I/O:

```python
@pytest.mark.asyncio
async def test_generates_all_five_ai_sections_concurrently():
    client = BlockingAiClient(expected_active=5)
    service = ReportGenerationService(ai_client=client, ai_concurrency=5)

    pending = asyncio.create_task(service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    ))
    await asyncio.wait_for(client.batch_started.wait(), timeout=1)
    assert client.started == 5
    assert client.max_active == 5
    client.release.set()

    sections = await pending
    assert list(sections) == [rule["key"] for rule in AI_SECTION_RULES]
    assert all(section["status"] == "generated" for section in sections.values())
```

Also import `AI_SECTION_RULES` alongside `AI_FALLBACK_TEXT`.

- [ ] **Step 2: Add a configured-bound test**

Add a client that releases each call after one event-loop turn so all batches can finish while recording the peak:

```python
class YieldingAiClient:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def generate_section(self, rule, context, *, user_id="", username=""):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            return f"{rule['key']} 正文"
        finally:
            self.active -= 1


@pytest.mark.asyncio
async def test_report_ai_concurrency_respects_configured_limit():
    client = YieldingAiClient()
    service = ReportGenerationService(ai_client=client, ai_concurrency=2)

    sections = await service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    )

    assert client.max_active == 2
    assert len(sections) == 5
```

- [ ] **Step 3: Add completion-order and failure-isolation coverage**

Add:

```python
class OutOfOrderAiClient:
    async def generate_section(self, rule, context, *, user_id="", username=""):
        key = rule["key"]
        if key == "debt_service_coverage":
            await asyncio.sleep(0.02)
        if key == "sensitivity":
            raise RuntimeError("单节失败")
        return f"{key} 正文"


@pytest.mark.asyncio
async def test_parallel_results_keep_rule_order_and_isolate_failure():
    service = ReportGenerationService(
        ai_client=OutOfOrderAiClient(), ai_concurrency=5
    )

    sections = await service._generate_ai_sections(
        {}, user_id="report-user", username="报告用户"
    )

    assert list(sections) == [rule["key"] for rule in AI_SECTION_RULES]
    assert sections["sensitivity"]["status"] == "fallback"
    assert sections["sensitivity"]["failureCode"] == "ai_output_validation_failed"
    assert all(
        section["status"] == "generated"
        for key, section in sections.items()
        if key != "sensitivity"
    )
```

- [ ] **Step 4: Run the new concurrency tests and verify red state**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/report/test_report_generation_service.py::test_generates_all_five_ai_sections_concurrently', 'tests/integration/report/test_report_generation_service.py::test_report_ai_concurrency_respects_configured_limit', 'tests/integration/report/test_report_generation_service.py::test_parallel_results_keep_rule_order_and_isolate_failure', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: the five-way overlap test times out or fails because the current loop waits for the first blocked section before starting the second.

- [ ] **Step 5: Extract one-section execution with existing fallback behavior**

Add `import asyncio` to the service. Extract the loop body into:

```python
async def _generate_one_ai_section(
    self,
    rule: dict,
    payload: dict,
    *,
    user_id: str,
    username: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict]:
    key = rule["key"]
    context = build_section_context(rule, payload)
    try:
        async with semaphore:
            logger.info("报告 AI 调用开始：section={}", key)
            text = await self._ai_client.generate_section(
                rule, context, user_id=user_id, username=username
            )
        text = self._validate_ai_text(text, rule)
        logger.info("报告 AI 调用成功：section={}", key)
        return key, {
            "status": "generated",
            "attempts": 1,
            "usedFallback": False,
            "text": text,
        }
    except Exception as exc:
        code = self._ai_failure_code(exc)
        logger.warning(
            "报告 AI 调用降级：section={} reason={} error={} detail={}",
            key, code, type(exc).__name__, str(exc),
        )
        return key, self._fallback(code, attempts=1)
```

The semaphore covers only the external model call. Context construction and validation are local operations; no ORM access is added.

- [ ] **Step 6: Replace the serial loop with bounded gather and stable assembly**

Implement `_generate_ai_sections()` as:

```python
async def _generate_ai_sections(
    self, payload: dict, *, user_id: str, username: str
) -> dict:
    semaphore = asyncio.Semaphore(self._ai_concurrency)
    results = await asyncio.gather(*[
        self._generate_one_ai_section(
            rule,
            payload,
            user_id=user_id,
            username=username,
            semaphore=semaphore,
        )
        for rule in AI_SECTION_RULES
    ])
    by_key = dict(results)
    return {rule["key"]: by_key[rule["key"]] for rule in AI_SECTION_RULES}
```

Do not pass `return_exceptions=True`: `_generate_one_ai_section()` converts all ordinary `Exception` failures to section fallback results. Cancellation remains able to stop the whole report-generation task.

- [ ] **Step 7: Run all report-generation integration tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/report/test_report_generation_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: all tests pass, including existing snapshot freeze/reuse behavior and new concurrency checks.

---

### Task 4: Run Focused Regression Verification

**Files:**
- Verify only; no planned source changes.

**Interfaces:**
- Verifies the combined behavior from Tasks 1-3 through the public and application-level test suites.

- [ ] **Step 1: Run all report unit and integration tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/report', 'tests/integration/report', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: all report tests pass. Record exact failures rather than claiming success if an unrelated pre-existing failure remains.

- [ ] **Step 2: Run middle-platform integration tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/middle_platform', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: tests relevant to Token and chat/model-pool transport pass. If the known pre-existing `<ir_system_context>` assertion still fails, report it separately and do not alter unrelated chat behavior as part of this feature.

- [ ] **Step 3: Run architecture guard tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/test_architecture_layout.py', '-q']))"
```

Expected: PASS; concurrency remains in application/infrastructure layers and adds no forbidden domain dependency.

- [ ] **Step 4: Inspect the final working-tree diff without modifying Git state**

Use read-only inspection only. Confirm the change set contains:

- concurrency config default and env/Nacos/YAML loading;
- factory injection;
- semaphore-bounded five-section execution;
- stable rule-order assembly;
- Token single-flight registry and cleanup;
- focused tests and nested `data.content` fixture correction;
- no prompt, snapshot schema, report-read, PDF, or frontend changes.

Do not stage or commit any file.
