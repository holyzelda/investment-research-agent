# Policy Ask SDK Startup Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start the backend without synchronously importing `lark_oapi`, warm it in the background, let an unusually early policy-question request await that shared warm-up, and remove `run.py`'s unused FastAPI instance.

**Architecture:** A new infrastructure loader owns one process-wide `asyncio.Task` that imports `tools.policy_ask` via `asyncio.to_thread`. FastAPI starts and stops that task in its lifespan. The policy executor and its domain port become asynchronous so `ConsultationService` can await the shared task without blocking the event loop; `tools.policy_ask.ask()` remains unchanged and synchronous.

**Tech Stack:** Python 3.13, FastAPI lifespan, asyncio, pytest, monkeypatch.

## Global Constraints

- Work in the current `main` workspace; do not create a worktree or use subagents.
- Do not run Git write operations (`git add`, `git commit`, or `git push`).
- Do not modify policy knowledge-base retrieval, LLM behavior, Nacos behavior, health-check semantics, frontend code, or the synchronous implementation of `tools.policy_ask.ask()`.
- Use `.venv\Scripts\python.exe` with the required stdout-to-stderr pytest wrapper.
- Preserve the existing `{code, msg, data}` response behavior; do not introduce a new readiness HTTP response.

---

## File Structure

- **Create** `app/modules/policy_market/infrastructure/policy_ask_loader.py`: owns the single warm-up task, deferred module import, retrieval, and shutdown cleanup.
- **Modify** `app/main.py`: starts the loader after initialization and cancels it at shutdown.
- **Modify** `app/modules/policy_market/domain/ports.py`: declares an asynchronous policy-question executor contract.
- **Modify** `app/modules/policy_market/application/consultation_service.py`: awaits the executor contract while retaining existing failure mapping.
- **Modify** `app/modules/policy_market/infrastructure/policy_ask_executor.py`: removes eager SDK import and uses the loader.
- **Modify** `run.py`: removes its unused FastAPI factory import and application creation.
- **Modify** `tests/unit/policy_market/test_policy_ask_executor.py`: exercises deferred module access and answer mapping through the asynchronous adapter.
- **Create** `tests/unit/policy_market/test_policy_ask_loader.py`: verifies task sharing, waiting, exception propagation, and cleanup.
- **Modify** `tests/unit/policy_market/test_consultation_service.py`: makes executor test doubles asynchronous and verifies the application service awaits them.
- **Create** `tests/unit/test_run_entrypoint.py`: verifies the entrypoint does not create an application itself.

## Task 1: Add the Shared Deferred Loader

**Files:**
- Create: `app/modules/policy_market/infrastructure/policy_ask_loader.py`
- Test: `tests/unit/policy_market/test_policy_ask_loader.py`

**Interfaces:**
- Produces: `start_policy_ask_warmup() -> asyncio.Task[ModuleType]`
- Produces: `get_policy_ask_module() -> Coroutine[Any, Any, ModuleType]`
- Produces: `stop_policy_ask_warmup() -> Coroutine[Any, Any, None]`
- Consumed later by: FastAPI lifespan and `PolicyAskExecutorAdapter`.

- [ ] **Step 1: Write a failing loader test for one shared task and deferred import**

```python
import asyncio
import types

import pytest

from app.modules.policy_market.infrastructure import policy_ask_loader


@pytest.mark.asyncio
async def test_warmup_is_shared_and_getter_waits_for_loaded_module(monkeypatch):
    loaded = types.ModuleType("tools.policy_ask")
    calls = []

    def fake_import(name):
        calls.append(name)
        return loaded

    monkeypatch.setattr(policy_ask_loader.importlib, "import_module", fake_import)

    first = policy_ask_loader.start_policy_ask_warmup()
    second = policy_ask_loader.start_policy_ask_warmup()

    assert first is second
    assert await policy_ask_loader.get_policy_ask_module() is loaded
    assert calls == ["tools.policy_ask"]

    await policy_ask_loader.stop_policy_ask_warmup()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_loader.py::test_warmup_is_shared_and_getter_waits_for_loaded_module', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because `policy_ask_loader` does not exist.

- [ ] **Step 3: Write failing tests for lazy start, propagated import failure, and shutdown cancellation**

```python
@pytest.mark.asyncio
async def test_getter_starts_warmup_when_lifespan_has_not_started_it(monkeypatch):
    loaded = types.ModuleType("tools.policy_ask")
    monkeypatch.setattr(policy_ask_loader.importlib, "import_module", lambda name: loaded)

    assert await policy_ask_loader.get_policy_ask_module() is loaded

    await policy_ask_loader.stop_policy_ask_warmup()


@pytest.mark.asyncio
async def test_getter_propagates_background_import_failure(monkeypatch):
    monkeypatch.setattr(
        policy_ask_loader.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("sdk unavailable")),
    )

    policy_ask_loader.start_policy_ask_warmup()

    with pytest.raises(ImportError, match="sdk unavailable"):
        await policy_ask_loader.get_policy_ask_module()

    await policy_ask_loader.stop_policy_ask_warmup()
```

- [ ] **Step 4: Implement the minimal loader**

```python
"""Deferred loading for the heavy policy knowledge-base SDK."""
from __future__ import annotations

import asyncio
import importlib
from types import ModuleType

_warmup_task: asyncio.Task[ModuleType] | None = None


async def _import_policy_ask() -> ModuleType:
    return await asyncio.to_thread(importlib.import_module, "tools.policy_ask")


def start_policy_ask_warmup() -> asyncio.Task[ModuleType]:
    global _warmup_task
    if _warmup_task is None:
        _warmup_task = asyncio.create_task(_import_policy_ask(), name="policy-ask-sdk-warmup")
    return _warmup_task


async def get_policy_ask_module() -> ModuleType:
    return await start_policy_ask_warmup()


async def stop_policy_ask_warmup() -> None:
    global _warmup_task
    task = _warmup_task
    _warmup_task = None
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

Use an `autouse` test fixture or explicit `await stop_policy_ask_warmup()` cleanup so module-global state does not leak between tests.

- [ ] **Step 5: Run the loader test file**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_loader.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

## Task 2: Make Policy-Question Execution Awaitable

**Files:**
- Modify: `app/modules/policy_market/domain/ports.py`
- Modify: `app/modules/policy_market/application/consultation_service.py`
- Modify: `app/modules/policy_market/infrastructure/policy_ask_executor.py`
- Modify: `tests/unit/policy_market/test_policy_ask_executor.py`
- Modify: `tests/unit/policy_market/test_consultation_service.py`

**Interfaces:**
- Consumes: `get_policy_ask_module() -> Coroutine[Any, Any, ModuleType]` from Task 1.
- Produces: `PolicyAskExecutor.ask(self, question: str) -> Coroutine[Any, Any, ConsultationAnswer]`.
- Produces: `PolicyAskExecutorAdapter.ask(self, question: str) -> Coroutine[Any, Any, ConsultationAnswer]`.
- Produces: `ConsultationService.create()` awaiting `self._executor.ask(question)`.

- [ ] **Step 1: Update the domain contract test double and add a failing await assertion**

Change `FakeExecutor` in `tests/unit/policy_market/test_consultation_service.py`:

```python
class FakeExecutor:
    async def ask(self, question):
        return ConsultationAnswer(
            "结构化回答",
            "宁夏",
            {"sources": ["https://example.test/a"], "timeliness": {}, "reminders": []},
        )
```

Add a test double that raises asynchronously:

```python
class BrokenExecutor:
    async def ask(self, question):
        raise RuntimeError("上游不可用")
```

- [ ] **Step 2: Run the consultation service tests to verify they fail**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_consultation_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because `ConsultationService.create()` does not await the coroutine returned by `ask()`.

- [ ] **Step 3: Replace the eager adapter import with a failing asynchronous adapter test**

Replace `tests/unit/policy_market/test_policy_ask_executor.py` with:

```python
import types

import pytest

from app.modules.policy_market.infrastructure.policy_ask_executor import PolicyAskExecutorAdapter


@pytest.mark.asyncio
async def test_executor_waits_for_loader_and_maps_tools_answer(monkeypatch):
    module = types.SimpleNamespace(
        ask=lambda question: {
            "answer": "宁夏结论",
            "sources": ["https://example.test/source"],
            "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
            "reminders": ["关注更新"],
        }
    )

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    result = await PolicyAskExecutorAdapter().ask("宁夏政策")

    assert result.answer == "宁夏结论"
    assert result.province_code == "宁夏"
    assert result.source_data == {
        "sources": ["https://example.test/source"],
        "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
        "reminders": ["关注更新"],
    }
```

- [ ] **Step 4: Update the port, service, and adapter minimally**

In `app/modules/policy_market/domain/ports.py`, change the protocol method to:

```python
async def ask(self, question: str) -> ConsultationAnswer:
    ...
```

In `app/modules/policy_market/application/consultation_service.py`, change the existing executor invocation to:

```python
answer = await self._executor.ask(question)
```

In `app/modules/policy_market/infrastructure/policy_ask_executor.py`, replace the top-level `from tools import policy_ask` with:

```python
from app.modules.policy_market.infrastructure.policy_ask_loader import get_policy_ask_module
```

and define:

```python
async def ask(self, question: str) -> ConsultationAnswer:
    policy_ask = await get_policy_ask_module()
    result = policy_ask.ask(question)
    # Preserve the existing result-to-ConsultationAnswer mapping below.
```

- [ ] **Step 5: Run policy-market unit tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_executor.py', 'tests/unit/policy_market/test_consultation_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

## Task 3: Start and Stop Warm-Up With the Application Lifecycle

**Files:**
- Modify: `app/main.py:14-63`
- Modify: `tests/e2e/test_app_boot.py`

**Interfaces:**
- Consumes: `start_policy_ask_warmup() -> asyncio.Task[ModuleType]` and `stop_policy_ask_warmup() -> Coroutine[Any, Any, None]` from Task 1.
- Produces: app lifespan that initiates warm-up without awaiting it and cleans it up during shutdown.

- [ ] **Step 1: Add a failing lifecycle order test**

Add this to `tests/e2e/test_app_boot.py`:

```python
@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_policy_ask_warmup(monkeypatch):
    calls = []

    monkeypatch.setattr(main, "start_policy_ask_warmup", lambda: calls.append("start"))

    async def fake_stop():
        calls.append("stop")

    monkeypatch.setattr(main, "stop_policy_ask_warmup", fake_stop)
    monkeypatch.setattr(main, "init_nacos_config", lambda: None)
    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "start_spot_daily_scheduler", lambda: None)
    monkeypatch.setattr(main, "stop_spot_daily_scheduler", lambda: None)
    monkeypatch.setattr(main, "dispose_engine", fake_stop)
    monkeypatch.setattr(main, "cleanup_nacos", fake_stop)

    # Use a focused test app/lifespan fixture that also stubs the recovery DB block.
    # Assert the warm-up start occurs before yield and its cleanup occurs after yield.
```

Implement the fixture with an async sessionmaker stub so the test does not connect to the database. Assert `"start" in calls` and that a distinct `"policy-stop"` marker is appended after exiting the lifespan.

- [ ] **Step 2: Run the focused lifecycle test to verify it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/test_app_boot.py::test_lifespan_starts_and_stops_policy_ask_warmup', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: FAIL because `main` does not import or invoke loader lifecycle functions.

- [ ] **Step 3: Add loader calls to the lifespan**

In `app/main.py`, import:

```python
from app.modules.policy_market.infrastructure.policy_ask_loader import (
    start_policy_ask_warmup,
    stop_policy_ask_warmup,
)
```

Start it after current startup initialization and before the completion log:

```python
start_policy_ask_warmup()
logger.info(f"{settings.app.name} 启动完成")
```

Stop it before the final shutdown log and after the existing scheduler stop:

```python
stop_spot_daily_scheduler()
await stop_policy_ask_warmup()
await dispose_engine()
```

Do not await `start_policy_ask_warmup()`; that is what preserves faster service readiness.

- [ ] **Step 4: Run focused lifecycle and app boot tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/test_app_boot.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

## Task 4: Remove the Redundant Entrypoint Application

**Files:**
- Modify: `run.py:1-14`
- Create: `tests/unit/test_run_entrypoint.py`

**Interfaces:**
- Produces: `run.py` that loads environment settings and runs the existing `app.main:app` application only.

- [ ] **Step 1: Write a failing source-level entrypoint test**

```python
from pathlib import Path


def test_run_entrypoint_does_not_create_an_unused_fastapi_application():
    source = Path("run.py").read_text(encoding="utf-8")

    assert "from app.main import create_app" not in source
    assert "app = create_app()" not in source
    assert 'uvicorn.run(\n        "app.main:app",' in source
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/test_run_entrypoint.py::test_run_entrypoint_does_not_create_an_unused_fastapi_application', '-q']))"
```

Expected: FAIL because `run.py` imports and calls `create_app()`.

- [ ] **Step 3: Remove only the unused application construction**

Delete these lines from `run.py`:

```python
from app.main import create_app  # noqa: E402

# 创建应用实例
app = create_app()
```

Keep `load_dotenv`, the current environment-derived host/port/debug settings, and the existing `uvicorn.run("app.main:app", ...)` call unchanged.

- [ ] **Step 4: Run the entrypoint test**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/test_run_entrypoint.py', '-q']))"
```

Expected: PASS.

## Task 5: Verify Integration and Measure Startup Import Improvement

**Files:**
- Modify only if prior test failures identify a direct compatibility issue; otherwise no code changes.

**Interfaces:**
- Verifies: import of `app.main` no longer imports `tools.policy_ask` or `lark_oapi` during module import.

- [ ] **Step 1: Run all changed test groups**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_loader.py', 'tests/unit/policy_market/test_policy_ask_executor.py', 'tests/unit/policy_market/test_consultation_service.py', 'tests/unit/test_run_entrypoint.py', 'tests/e2e/test_app_boot.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

- [ ] **Step 2: Verify imports remain deferred**

Run:

```bash
.venv\Scripts\python.exe -c "import sys; import app.main; assert 'tools.policy_ask' not in sys.modules; assert 'lark_oapi' not in sys.modules; print('policy SDK import is deferred')"
```

Expected: `policy SDK import is deferred`.

- [ ] **Step 3: Measure cold application import**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, time; sys.stdout = sys.stderr; started = time.perf_counter(); import app.main; print(f'app.main import: {time.perf_counter() - started:.3f}s')"
```

Expected: significantly lower than the pre-change 12.301-second measured import, with environment-dependent variance documented in the completion report.

- [ ] **Step 4: Review the diff without Git writes**

Run:

```bash
git diff --check && git diff -- run.py app/main.py app/modules/policy_market tests/unit tests/e2e
```

Expected: no whitespace errors; diff limited to the planned loader, async contract propagation, lifecycle wiring, tests, and entrypoint cleanup.

## Plan Self-Review

- **Spec coverage:** Task 1 implements a single shared background loader, wait-on-first-request behavior, and failure propagation. Task 2 connects it to the policy-question execution flow. Task 3 owns lifecycle startup/cleanup. Task 4 removes the duplicate `create_app()` call. Task 5 validates no eager SDK import and measures the intended improvement.
- **No placeholders:** Every planned production change supplies exact symbols and code. The lifecycle test intentionally requires a small fixture to avoid external dependencies; it specifies the assertions and stub requirements.
- **Type consistency:** `start_policy_ask_warmup`, `get_policy_ask_module`, and `stop_policy_ask_warmup` use identical names throughout. The async `ask(question: str)` contract is produced in Task 2 and consumed by `ConsultationService.create()`.
