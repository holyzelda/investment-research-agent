# Task Input Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing `POST /ir/calc/tasks` request boundary to accept valid capacity/power/duration combinations while preserving all existing calculation-domain, Feishu, snapshot, result, report, and conversation contracts.

**Architecture:** Add one pure input-normalization function at the calculation interface/application boundary. `TaskCreateReq` accepts optional positive capacity, power, and duration values; the router normalizes them to the unchanged `ProjectBasics` before invoking the existing `CalculationTaskService`. `duration_hours` is discarded after normalization and never reaches the parameter dictionary, frozen input, snapshots, or Feishu.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async, pytest.

## Global Constraints

- Do not create a new calculation URL; modify only `POST /ir/calc/tasks`.
- Do not perform `git add`, `git commit`, `git push`, or any Git write operation.
- Keep the `{code,msg,data}` response shell; validation errors are HTTP 400.
- Keep `ProjectBasics`, `CalculationTaskService`, `ParamAssembler`, parameter dictionary, Feishu `API_INPUT`, `api_input`, input snapshots, report snapshots, and task/result/report response structures unchanged.
- `duration_hours` is interface-only: it is not a parameter-dictionary field and must not be persisted or sent to Feishu.
- `conversation_id` remains an optional top-level field for backward compatibility; supplied IDs retain existing owner and non-deleted validation semantics.
- `operation_years` remains only in `param_overrides.operation_years`; omission preserves the existing dictionary default of 15, and existing 15/20 template validation remains authoritative.
- Use `.venv\Scripts\python.exe` and the required pytest wrapper; do not call `python` or `python3`.

---

## File Structure

- Create: `agent-backend/app/modules/calculation/application/input_normalizer.py` — pure conversion from optional request values into unchanged `ProjectBasics`.
- Modify: `agent-backend/app/modules/calculation/interface/router.py` — make capacity/power conditional request inputs, add duration, call the normalizer.
- Create: `agent-backend/tests/unit/calculation/test_input_normalizer.py` — exhaustive pure normalization tests.
- Modify: `agent-backend/tests/db/test_calc_task_api.py` — verify HTTP boundary normalization and absence of duration from frozen input.

### Task 1: Create and Verify Pure Size-Input Normalization

**Files:**
- Create: `agent-backend/app/modules/calculation/application/input_normalizer.py`
- Create: `agent-backend/tests/unit/calculation/test_input_normalizer.py`

**Interfaces:**
- Consumes: `normalize_project_basics(*, province: str, capacity_mwh: float | None, power_mw: float | None, duration_hours: float | None, node_name: str | None, voltage_kv: int) -> ProjectBasics`.
- Produces: unchanged `ProjectBasics` for valid combinations, or raises `ValidationException` for incomplete/conflicting combinations.

- [ ] **Step 1: Write the failing unit tests**

Create `tests/unit/calculation/test_input_normalizer.py`:

```python
import pytest

from app.core.exceptions import ValidationException
from app.modules.calculation.application.input_normalizer import normalize_project_basics


def normalize(*, capacity_mwh=None, power_mw=None, duration_hours=None):
    return normalize_project_basics(
        province="甘肃",
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        duration_hours=duration_hours,
        node_name="兰州东",
        voltage_kv=220,
    )


def test_keeps_explicit_capacity_and_power():
    basics = normalize(capacity_mwh=800, power_mw=200)

    assert basics.province == "甘肃"
    assert basics.capacity_mwh == 800
    assert basics.power_mw == 200
    assert basics.node_name == "兰州东"
    assert basics.voltage_kv == 220


def test_derives_capacity_from_power_and_duration():
    basics = normalize(power_mw=100, duration_hours=2)

    assert basics.power_mw == 100
    assert basics.capacity_mwh == 200


def test_derives_power_from_capacity_and_duration():
    basics = normalize(capacity_mwh=400, duration_hours=4)

    assert basics.capacity_mwh == 400
    assert basics.power_mw == 100


def test_uses_default_power_for_duration_only():
    basics = normalize(duration_hours=2)

    assert basics.power_mw == 100
    assert basics.capacity_mwh == 200


def test_accepts_all_three_when_consistent():
    basics = normalize(capacity_mwh=200, power_mw=100, duration_hours=2)

    assert basics.capacity_mwh == 200
    assert basics.power_mw == 100


@pytest.mark.parametrize(
    ("capacity_mwh", "power_mw", "duration_hours", "message"),
    [
        (150, 100, 2, "不一致"),
        (None, 100, None, "容量和功率"),
        (200, None, None, "容量和功率"),
        (None, None, None, "容量和功率"),
    ],
)
def test_rejects_invalid_size_combinations(
    capacity_mwh, power_mw, duration_hours, message
):
    with pytest.raises(ValidationException, match=message):
        normalize(
            capacity_mwh=capacity_mwh,
            power_mw=power_mw,
            duration_hours=duration_hours,
        )
```

- [ ] **Step 2: Run the unit test and verify it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', '-q']))"
```

Expected: collection fails because `input_normalizer.py` does not exist.

- [ ] **Step 3: Implement the smallest pure normalizer**

Create `app/modules/calculation/application/input_normalizer.py`:

```python
"""HTTP 测算规模输入归一化；领域层只接收容量与功率。"""
from __future__ import annotations

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
            capacity_mwh,
            power_mw * duration_hours,
            rel_tol=1e-9,
            abs_tol=1e-9,
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

Do not import FastAPI, SQLAlchemy, parameter dictionary, or Feishu infrastructure into this module.

- [ ] **Step 4: Run the unit test and verify it passes**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', '-q']))"
```

Expected: PASS.

### Task 2: Integrate Normalization into the Existing Task Endpoint

**Files:**
- Modify: `agent-backend/app/modules/calculation/interface/router.py:6-10,116-145`
- Modify: `agent-backend/tests/db/test_calc_task_api.py`

**Interfaces:**
- Consumes: `normalize_project_basics` from Task 1.
- Produces: `TaskCreateReq` where `capacity_mwh`, `power_mw`, and `duration_hours` are optional positive floats; route passes normalized `ProjectBasics` to unchanged `CalculationTaskService.create_and_run`.

- [ ] **Step 1: Add failing HTTP regression tests**

Append these tests to `tests/db/test_calc_task_api.py`:

```python
@pytest.mark.asyncio
async def test_task_accepts_duration_only_and_freezes_normalized_basics(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "duration_hours": 2,
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["input"]["power_mw"] == 100
    assert data["input"]["capacity_mwh"] == 200
    assert "duration_hours" not in data["input"]


@pytest.mark.asyncio
async def test_task_accepts_power_and_duration(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "power_mw": 100,
        "duration_hours": 2,
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["input"]["power_mw"] == 100
    assert data["input"]["capacity_mwh"] == 200


@pytest.mark.asyncio
async def test_task_rejects_inconsistent_capacity_power_and_duration(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "capacity_mwh": 150,
        "power_mw": 100,
        "duration_hours": 2,
    })

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert "不一致" in response.json()["msg"]
```

- [ ] **Step 2: Run the endpoint test and verify it fails**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/db/test_calc_task_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: duration-only and power-plus-duration requests return HTTP 400 because the current Pydantic model requires both capacity and power.

- [ ] **Step 3: Change only the request model and route construction**

In `app/modules/calculation/interface/router.py` import the normalizer:

```python
from app.modules.calculation.application.input_normalizer import normalize_project_basics
```

Replace `TaskCreateReq` with:

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

In `create_task`, replace the inline `ProjectBasics(...)` with:

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

Leave `conversation_id=req.conversation_id` and `param_overrides=req.param_overrides` exactly as they are.

- [ ] **Step 4: Run focused regression tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_input_normalizer.py', 'tests/db/test_calc_task_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. Existing capacity/power requests continue to create V1/V2; duration-derived requests freeze only normalized capacity/power.

### Task 3: Verify Existing Operation-Years and Broader Calculation Contracts

**Files:**
- No production code changes expected.
- Test: `agent-backend/tests/integration/calculation/test_task_service_overrides.py`
- Test: `agent-backend/tests/integration/calculation/test_feishu_http_client.py`
- Test: `agent-backend/tests/unit/calculation/test_param_dictionary.py`

**Interfaces:**
- Verifies: `param_overrides.operation_years` remains the sole operation-years entry point, selecting 15/20-year templates without an `API_INPUT` write.

- [ ] **Step 1: Run operation-years and Feishu regression tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/calculation/test_task_service_overrides.py', 'tests/integration/calculation/test_feishu_http_client.py', 'tests/unit/calculation/test_param_dictionary.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS. This confirms the new request-only `duration_hours` path has not altered the established operation-years dictionary/template or Feishu interface contract.

- [ ] **Step 2: Run the full calculation test subset**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation', 'tests/integration/calculation', 'tests/db/test_calc_task_api.py', '-q', '-o', 'asyncio_mode=auto']))"
```

Expected: PASS.

---

## Plan Self-Review

- **Spec coverage:** Task 1 implements each accepted/rejected duration combination as a pure function. Task 2 integrates it solely at the existing task HTTP boundary and verifies snapshot-facing inputs contain no duration field. Task 3 protects operation-years, Feishu, parameter dictionary, and calculation regression behavior.
- **Scope:** The plan does not create a new endpoint, add middle-platform proxy behavior, alter title/session persistence, edit YAML, or modify frontend code.
- **Type consistency:** `TaskCreateReq` is the only object that contains `duration_hours`; `ProjectBasics` remains unchanged and therefore downstream assemblies cannot persist or write it.
- **No Git writes:** No commit steps appear because repository instructions prohibit Git writes without an explicit user request.
