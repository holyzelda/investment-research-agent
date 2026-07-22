# 联络线功率趋势 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为联络线地图右侧已选线路提供以自然日昨天为边界、固定 96 个 15 分钟点的真实功率趋势查询、聚合与展示能力。

**Architecture:** 后端在既有 `tie_line_map` 模块中新增一个只读趋势用例：按 `line_id` 查询功率宽表，固定遍历 96 个时段，单日返回原值、多日逐时刻忽略空值求算术平均。前端由 Pinia 统一维护趋势范围与异步状态，使用请求版本号阻止切线或切换范围时的旧响应覆盖最新选择；详情面板只在真实选中线路时渲染独立 ECharts 趋势组件。

**Tech Stack:** FastAPI、Pydantic、异步 SQLAlchemy、pytest/httpx ASGITransport、Vue 3、Pinia、Vitest、Element Plus、ECharts、XC CSS token。

---

## 文件结构与职责

| 文件 | 变更 | 职责 |
|---|---|---|
| `agent-backend/app/modules/tie_line_map/domain/models.py` | 修改 | 声明功率趋势与趋势点领域值对象。 |
| `agent-backend/app/modules/tie_line_map/application/tie_line_service.py` | 修改 | 验证线路、查询功率宽表、以固定 96 时段聚合。 |
| `agent-backend/app/modules/tie_line_map/interface/serializers.py` | 修改 | 趋势领域值对象转 camelCase API 数据。 |
| `agent-backend/app/modules/tie_line_map/interface/router.py` | 修改 | 日期参数、昨天上限校验和只读趋势端点。 |
| `agent-backend/tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py` | 新建 | 端点聚合、空值、空数据、404、400 契约测试。 |
| `agent-frontend/src/api/tieLine.js` | 修改 | 新增趋势 API 薄封装。 |
| `agent-frontend/src/store/modules/tieLine.js` | 修改 | 日期范围计算、趋势请求状态、竞态保护和重试。 |
| `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue` | 新建 | 范围控制、自定义日期、图表和趋势局部状态。 |
| `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue` | 修改 | 保留静态详情，嵌入已选线路趋势组件。 |
| `agent-frontend/src/views/tie-line/index.vue` | 修改 | 向详情面板传递趋势状态和事件。 |
| `agent-frontend/tests/tie-line-power-trend.spec.js` | 新建 | 趋势组件的日期、图表、空态、错误态测试。 |
| `agent-frontend/tests/tie-line-store.spec.js` | 修改 | 日期范围、默认请求、竞态与清空选择测试。 |
| `agent-frontend/tests/tie-line-detail-panel.spec.js` | 修改 | 替换旧占位断言并验证已选/推荐线路边界。 |
| `my_projects/联络线地图模块-功能与开发文档.md` | 修改 | 记录已落地趋势能力、契约、口径、边界与验证方式。 |

### Task 1：建立后端趋势领域契约与失败端点测试

**Files:**
- Modify: `agent-backend/app/modules/tie_line_map/domain/models.py:1-31`
- Create: `agent-backend/tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py`

- [ ] **Step 1: 写出趋势端点的失败测试与内存数据库夹具**

新建测试文件，沿用 `test_tie_line_endpoints.py` 的 `StaticPool + ASGITransport` 模式；种入两条线路及 `TieLinePowerORM` 记录。必须使用固定完整的 96 时段字典，避免测试数据自身遗漏时段：

```python
"""e2e：联络线功率趋势查询接口。"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.tie_line_map.application.power_import_service import POWER_TIME_COLUMNS
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM, TieLinePowerORM


def _powers(**overrides):
    return {
        f"power_{time.replace(':', '')}_mw": overrides.get(time, Decimal("10.000"))
        for time in POWER_TIME_COLUMNS
    }


@pytest.fixture
async def seeded_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yesterday = date.today() - timedelta(days=1)
    async with maker() as session:
        line = TieLineMapORM(
            name="甲乙线", start_point="甲站", end_point="乙站",
            start_region="西北", end_region="华南",
            start_longitude=100, start_latitude=30, end_longitude=110, end_latitude=25,
        )
        other = TieLineMapORM(
            name="丙丁线", start_point="丙站", end_point="丁站",
            start_region="华北", end_region="华东",
            start_longitude=115, start_latitude=35, end_longitude=120, end_latitude=31,
        )
        session.add_all([line, other])
        await session.flush()
        session.add_all([
            TieLinePowerORM(
                line_id=line.id, data_date=yesterday, line_name="甲乙线", voltage_text="±800 kV",
                **_powers(**{"00:15": Decimal("100.000"), "00:30": None}),
            ),
            TieLinePowerORM(
                line_id=line.id, data_date=yesterday - timedelta(days=1), line_name="甲乙线", voltage_text="±800 kV",
                **_powers(**{"00:15": Decimal("200.000"), "00:30": None}),
            ),
            TieLinePowerORM(
                line_id=other.id, data_date=yesterday, line_name="丙丁线", voltage_text="±500 kV",
                **_powers(**{"00:15": Decimal("999.000")} ),
            ),
        ])
        await session.commit()

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()
```

在同文件中新增以下测试。将其中的 `line_id = 1` 替换为从 `GET /ir/tie-lines` 取得的“甲乙线”实际 ID，以避免依赖 SQLite 自增细节：

```python
async def _line_id(client: AsyncClient, name: str) -> int:
    data = (await client.get("/ir/tie-lines")).json()["data"]
    return next(item["id"] for item in data["items"] if item["name"] == name)


@pytest.mark.asyncio
async def test_single_day_power_returns_all_96_original_points(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")
    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={"startDate": yesterday.isoformat(), "endDate": yesterday.isoformat()},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["lineId"] == line_id
    assert data["startDate"] == yesterday.isoformat()
    assert data["endDate"] == yesterday.isoformat()
    assert data["dataDateCount"] == 1
    assert len(data["points"]) == 96
    assert data["points"][0] == {"time": "00:15", "powerMw": 100.0}
    assert data["points"][1] == {"time": "00:30", "powerMw": None}
    assert data["points"][-1]["time"] == "24:00"


@pytest.mark.asyncio
async def test_multi_day_power_averages_each_time_and_ignores_nulls(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")
    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={
            "startDate": (yesterday - timedelta(days=1)).isoformat(),
            "endDate": yesterday.isoformat(),
        },
    )

    data = response.json()["data"]
    assert data["dataDateCount"] == 2
    assert data["points"][0] == {"time": "00:15", "powerMw": 150.0}
    assert data["points"][1] == {"time": "00:30", "powerMw": None}


@pytest.mark.asyncio
async def test_power_returns_null_points_when_range_has_no_records(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    line_id = await _line_id(seeded_client, "甲乙线")
    response = await seeded_client.get(
        f"/ir/tie-lines/{line_id}/power",
        params={
            "startDate": (yesterday - timedelta(days=10)).isoformat(),
            "endDate": (yesterday - timedelta(days=9)).isoformat(),
        },
    )

    data = response.json()["data"]
    assert data["dataDateCount"] == 0
    assert len(data["points"]) == 96
    assert all(point["powerMw"] is None for point in data["points"])


@pytest.mark.asyncio
async def test_power_returns_404_for_unknown_line(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    response = await seeded_client.get(
        "/ir/tie-lines/999999/power",
        params={"startDate": yesterday.isoformat(), "endDate": yesterday.isoformat()},
    )
    assert response.status_code == 404
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_power_rejects_invalid_or_unfinished_dates(seeded_client):
    yesterday = date.today() - timedelta(days=1)
    today = date.today()
    line_id = await _line_id(seeded_client, "甲乙线")

    cases = [
        {"startDate": yesterday.isoformat(), "endDate": (yesterday - timedelta(days=1)).isoformat()},
        {"startDate": today.isoformat(), "endDate": today.isoformat()},
        {"startDate": "not-a-date", "endDate": yesterday.isoformat()},
        {"endDate": yesterday.isoformat()},
    ]
    for params in cases:
        response = await seeded_client.get(f"/ir/tie-lines/{line_id}/power", params=params)
        assert response.status_code == 400
        assert response.json()["code"] == 400
```

- [ ] **Step 2: 运行目标后端测试，确认路由尚不存在时失败**

在 `agent-backend/` 执行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：测试失败，原因是 `GET /ir/tie-lines/{lineId}/power` 尚未实现（404 或错误响应），而不是夹具创建失败。

- [ ] **Step 3: 添加不依赖框架的趋势领域值对象**

在 `agent-backend/app/modules/tie_line_map/domain/models.py` 的 `TieLine` 定义之后追加：

```python
@dataclass(frozen=True)
class TieLinePowerPoint:
    """一条联络线在固定 15 分钟时刻的功率值。"""

    time: str
    power_mw: Optional[float]


@dataclass(frozen=True)
class TieLinePowerTrend:
    """联络线在闭合自然日范围内的 96 时刻功率趋势。"""

    line_id: int
    start_date: date
    end_date: date
    data_date_count: int
    points: tuple[TieLinePowerPoint, ...]
```

同时在文件顶部添加：

```python
from datetime import date
```

- [ ] **Step 4: 暂不实现服务，重新运行测试确保仍失败**

重复 Step 2 的命令。

预期：仍失败于端点不存在；领域模型本身不应引起架构测试或导入错误。

- [ ] **Step 5: 提交领域模型与失败测试**

```bash
git add agent-backend/app/modules/tie_line_map/domain/models.py agent-backend/tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py
git commit -m "test: define tie line power trend contract"
```

### Task 2：实现固定 96 点聚合、端点校验与序列化

**Files:**
- Modify: `agent-backend/app/modules/tie_line_map/application/tie_line_service.py:7-57`
- Modify: `agent-backend/app/modules/tie_line_map/interface/serializers.py:10-82`
- Modify: `agent-backend/app/modules/tie_line_map/interface/router.py:1-120`
- Test: `agent-backend/tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py`

- [ ] **Step 1: 在应用服务实现宽表到固定 96 点趋势的聚合**

将 `tie_line_service.py` 的 import 区调整为：

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.tie_line_map.application.power_import_service import POWER_TIME_COLUMNS
from app.modules.tie_line_map.domain.models import TieLine, TieLinePowerPoint, TieLinePowerTrend
from app.modules.tie_line_map.infrastructure.persistence.orm import TieLineMapORM, TieLinePowerORM
```

在 `_to_domain()` 后增加两个纯函数：

```python
def _power_attribute_name(time_column: str) -> str:
    return f"power_{time_column.replace(':', '')}_mw"


def _average_power(rows: list[TieLinePowerORM], time_column: str) -> float | None:
    values = [
        value
        for row in rows
        if (value := getattr(row, _power_attribute_name(time_column))) is not None
    ]
    if not values:
        return None
    return float(sum(values, Decimal("0")) / len(values))
```

在 `TieLineService` 中追加：

```python
    async def get_power_trend(
        self,
        session: AsyncSession,
        *,
        line_id: int,
        start_date: date,
        end_date: date,
    ) -> TieLinePowerTrend:
        line = await session.get(TieLineMapORM, line_id)
        if line is None:
            raise NotFoundException("联络线不存在")

        rows = (await session.execute(
            select(TieLinePowerORM)
            .where(
                TieLinePowerORM.line_id == line_id,
                TieLinePowerORM.data_date >= start_date,
                TieLinePowerORM.data_date <= end_date,
            )
            .order_by(TieLinePowerORM.data_date.asc())
        )).scalars().all()
        return TieLinePowerTrend(
            line_id=line_id,
            start_date=start_date,
            end_date=end_date,
            data_date_count=len(rows),
            points=tuple(
                TieLinePowerPoint(
                    time=time_column,
                    power_mw=_average_power(rows, time_column),
                )
                for time_column in POWER_TIME_COLUMNS
            ),
        )
```

说明：统一用 `_average_power` 聚合，单日时自然得到原值；空行或字段全空时返回 `None`。查询条件只有 `line_id` 和闭区间日期，绝不退回到 `line_name` 或 `voltage_text`。

- [ ] **Step 2: 在 serializer 增加趋势 camelCase 映射**

在 `agent-backend/app/modules/tie_line_map/interface/serializers.py` 的 import 改为：

```python
from app.modules.tie_line_map.domain.models import TieLine, TieLinePowerTrend
```

在文件末尾追加：

```python
def serialize_power_trend(trend: TieLinePowerTrend) -> dict:
    """功率趋势值对象转为前端消费的 camelCase 数据。"""
    return {
        "lineId": trend.line_id,
        "startDate": trend.start_date.isoformat(),
        "endDate": trend.end_date.isoformat(),
        "dataDateCount": trend.data_date_count,
        "points": [
            {"time": point.time, "powerMw": point.power_mw}
            for point in trend.points
        ],
    }
```

并将文件顶部描述里的“故此处不产出任何 MW 时序”改为“静态列表/详情不产出 MW 时序；功率趋势由专用序列化函数输出”。

- [ ] **Step 3: 在动态详情路由之前添加日期验证和趋势端点**

在 `agent-backend/app/modules/tie_line_map/interface/router.py`：

1. 将日期 import 改为：

```python
from datetime import date, timedelta
```

2. 将 serializer import 改为：

```python
from app.modules.tie_line_map.interface.serializers import (
    serialize_line_detail,
    serialize_lines,
    serialize_power_trend,
)
```

3. 在 `@router.get("/{line_id}")` **之前**增加：

```python
@router.get("/{line_id}/power")
async def get_tie_line_power_trend(
    line_id: int,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db_session),
):
    """返回联络线在已完整自然日范围内的 96 时刻功率趋势。"""
    yesterday = date.today() - timedelta(days=1)
    if start_date > end_date:
        raise ValidationException("开始日期不能晚于结束日期")
    if start_date > yesterday or end_date > yesterday:
        raise ValidationException("功率趋势仅支持查询自然日昨天及更早日期")
    trend = await _service.get_power_trend(
        session,
        line_id=line_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ok(serialize_power_trend(trend))
```

FastAPI 对缺少或格式无效的 `date` 参数默认会产生 422；项目铁律要求参数校验统一为 400。因此在该路由上不要直接依赖 FastAPI 的必填 query 参数校验。改用字符串 query 参数并显式转换：

```python
from fastapi import APIRouter, Depends, Query, Request, UploadFile


def _parse_power_date(value: str | None, field_name: str) -> date:
    if not value:
        raise ValidationException(f"{field_name} 不能为空")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValidationException(f"{field_name} 格式必须为 YYYY-MM-DD") from error


@router.get("/{line_id}/power")
async def get_tie_line_power_trend(
    line_id: int,
    start_date_text: str | None = Query(default=None, alias="startDate"),
    end_date_text: str | None = Query(default=None, alias="endDate"),
    session: AsyncSession = Depends(get_db_session),
):
    start_date = _parse_power_date(start_date_text, "startDate")
    end_date = _parse_power_date(end_date_text, "endDate")
    yesterday = date.today() - timedelta(days=1)
    if start_date > end_date:
        raise ValidationException("开始日期不能晚于结束日期")
    if start_date > yesterday or end_date > yesterday:
        raise ValidationException("功率趋势仅支持查询自然日昨天及更早日期")
    trend = await _service.get_power_trend(
        session,
        line_id=line_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ok(serialize_power_trend(trend))
```

`Query` 必须加入 FastAPI import；端点路径必须在 `/{line_id}` 详情路由前。

- [ ] **Step 4: 运行趋势端点测试，确认全部通过**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：5 个测试全部 PASS，且测试响应含 `dataDateCount`、96 个 camelCase 点、空值 `null`、HTTP 400/404。

- [ ] **Step 5: 运行联络线后端回归**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/', 'tests/unit/tie_line_map/', 'tests/unit/test_architecture_layout.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：PASS。若架构测试报告 domain 依赖框架，确认 `domain/models.py` 只依赖 `dataclasses`、`datetime` 和 `typing`。

- [ ] **Step 6: 提交后端实现**

```bash
git add agent-backend/app/modules/tie_line_map/application/tie_line_service.py agent-backend/app/modules/tie_line_map/interface/serializers.py agent-backend/app/modules/tie_line_map/interface/router.py agent-backend/tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py
git commit -m "feat: add tie line power trend endpoint"
```

### Task 3：扩展前端 API 与 Store，并用测试锁定日期、竞态和清理规则

**Files:**
- Modify: `agent-frontend/src/api/tieLine.js:1-16`
- Modify: `agent-frontend/src/store/modules/tieLine.js:1-141`
- Modify: `agent-frontend/tests/tie-line-store.spec.js:1-158`

- [ ] **Step 1: 为 Store 测试建立 API mock 并添加日期工具的失败用例**

将 `tests/tie-line-store.spec.js` 的 Vitest import 改为：

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'
```

在 Pinia imports 之前追加：

```js
const api = vi.hoisted(() => ({
  getTieLines: vi.fn(),
  getTieLineDetail: vi.fn(),
  getTieLinePower: vi.fn(),
}))

vi.mock('@/api/tieLine', () => api)
```

将 store import 改为：

```js
import {
  getRollingDateRange,
  isValidCustomPowerRange,
  normalizeCapacityMw,
  parseLengthKm,
  useTieLineStore,
} from '@/store/modules/tieLine'
```

在现有 `describe` 之后新增：

```js
describe('联络线功率趋势状态', () => {
  const now = new Date(2026, 6, 21, 12, 0, 0)

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('以自然日昨天生成昨日、7日、30日和90日闭区间', () => {
    expect(getRollingDateRange(1, now)).toEqual({ startDate: '2026-07-20', endDate: '2026-07-20' })
    expect(getRollingDateRange(7, now)).toEqual({ startDate: '2026-07-14', endDate: '2026-07-20' })
    expect(getRollingDateRange(30, now)).toEqual({ startDate: '2026-06-21', endDate: '2026-07-20' })
    expect(getRollingDateRange(90, now)).toEqual({ startDate: '2026-04-22', endDate: '2026-07-20' })
  })

  it('拒绝结束日期为当天或日期倒置的自定义范围', () => {
    expect(isValidCustomPowerRange('2026-07-19', '2026-07-20', now)).toBe(true)
    expect(isValidCustomPowerRange('2026-07-20', '2026-07-21', now)).toBe(false)
    expect(isValidCustomPowerRange('2026-07-20', '2026-07-19', now)).toBe(false)
  })

  it('选择线路时默认请求昨日趋势', async () => {
    api.getTieLineDetail.mockResolvedValue({ data: { id: 1, name: '甲乙线' } })
    api.getTieLinePower.mockResolvedValue({ data: { lineId: 1, points: [] } })
    const store = useTieLineStore()

    await store.selectLine(1)

    expect(api.getTieLinePower).toHaveBeenCalledWith(1, {
      startDate: '2026-07-20', endDate: '2026-07-20',
    })
    expect(store.powerTrend).toEqual({ lineId: 1, points: [] })
  })

  it('后发线路请求完成后，先发线路响应不得覆盖当前详情或趋势', async () => {
    let resolveDetailA
    let resolvePowerA
    api.getTieLineDetail
      .mockImplementationOnce(() => new Promise((resolve) => { resolveDetailA = resolve }))
      .mockResolvedValueOnce({ data: { id: 2, name: '乙丙线' } })
    api.getTieLinePower
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePowerA = resolve }))
      .mockResolvedValueOnce({ data: { lineId: 2, points: [{ time: '00:15', powerMw: 200 }] } })
    const store = useTieLineStore()

    const selectA = store.selectLine(1)
    const selectB = store.selectLine(2)
    await selectB
    resolveDetailA({ data: { id: 1, name: '甲乙线' } })
    resolvePowerA({ data: { lineId: 1, points: [{ time: '00:15', powerMw: 100 }] } })
    await selectA

    expect(store.selectedId).toBe(2)
    expect(store.detail).toEqual({ id: 2, name: '乙丙线' })
    expect(store.powerTrend.lineId).toBe(2)
  })

  it('清空选择后，滞后趋势响应不得恢复数据', async () => {
    let resolvePower
    api.getTieLineDetail.mockResolvedValue({ data: { id: 1 } })
    api.getTieLinePower.mockImplementationOnce(() => new Promise((resolve) => { resolvePower = resolve }))
    const store = useTieLineStore()

    const selection = store.selectLine(1)
    store.clearSelection()
    resolvePower({ data: { lineId: 1, points: [] } })
    await selection

    expect(store.selectedId).toBeNull()
    expect(store.powerTrend).toBeNull()
  })
})
```

为了让“默认昨天”可测，Store 的范围工具必须支持可选 `now`。`selectLine()` 中调用不传 `now` 的函数；测试可以仅断言 API 参数与 `getRollingDateRange(1)` 一致，或在实现中为 Store 增加一个只在测试传入的 `setPowerRange(range)`。选择前者：将“选择线路默认昨日”测试里两处硬编码日期改为：

```js
const expectedRange = getRollingDateRange(1)
expect(api.getTieLinePower).toHaveBeenCalledWith(1, expectedRange)
```

- [ ] **Step 2: 运行 Store 测试，确认新增导出和状态尚未实现而失败**

```bash
pnpm vitest run tests/tie-line-store.spec.js
```

预期：失败并报告 `getRollingDateRange` / `isValidCustomPowerRange` 未导出或 `getTieLinePower` 不存在。

- [ ] **Step 3: 添加 API 薄封装**

在 `agent-frontend/src/api/tieLine.js` 的末尾添加：

```js
export function getTieLinePower(lineId, { startDate, endDate }) {
  return request({
    url: `/ir/tie-lines/${lineId}/power`,
    method: 'get',
    params: { startDate, endDate },
  })
}
```

- [ ] **Step 4: 实现本地日期工具、趋势状态与请求版本号**

在 `agent-frontend/src/store/modules/tieLine.js`：

1. 将 API import 改为：

```js
import { getTieLineDetail, getTieLinePower, getTieLines } from '@/api/tieLine'
```

2. 在 `normalizeCapacityMw` 后加入以下导出工具。禁止使用 `toISOString()`，防止东八区等本地时区偏移日期：

```js
function formatLocalDate(value) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function yesterdayDate(now = new Date()) {
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  return yesterday
}

export function getRollingDateRange(days, now = new Date()) {
  const end = yesterdayDate(now)
  const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - (days - 1))
  return { startDate: formatLocalDate(start), endDate: formatLocalDate(end) }
}

export function isValidCustomPowerRange(startDate, endDate, now = new Date()) {
  if (!startDate || !endDate || startDate > endDate) return false
  return endDate <= formatLocalDate(yesterdayDate(now))
}
```

3. 在 `state` 的 `detail` 之后加入：

```js
    powerTrend: null,
    powerTrendLoading: false,
    powerTrendError: '',
    powerRange: { key: 'yesterday', ...getRollingDateRange(1) },
    powerRequestVersion: 0,
```

4. 在 `actions` 最前加入：

```js
    _invalidatePowerRequests() {
      this.powerRequestVersion += 1
    },
    _clearPowerTrend() {
      this.powerTrend = null
      this.powerTrendLoading = false
      this.powerTrendError = ''
    },
    async loadPowerTrend(range = this.powerRange) {
      if (this.selectedId == null) return
      const lineId = this.selectedId
      const requestVersion = this.powerRequestVersion + 1
      this.powerRequestVersion = requestVersion
      this.powerRange = range
      this.powerTrend = null
      this.powerTrendLoading = true
      this.powerTrendError = ''
      try {
        const res = await getTieLinePower(lineId, range)
        if (requestVersion === this.powerRequestVersion && this.selectedId === lineId) {
          this.powerTrend = res?.data || null
        }
      } catch (e) {
        if (requestVersion === this.powerRequestVersion && this.selectedId === lineId) {
          this.powerTrendError = '功率趋势加载失败，请稍后重试'
        }
      } finally {
        if (requestVersion === this.powerRequestVersion && this.selectedId === lineId) {
          this.powerTrendLoading = false
        }
      }
    },
    async setPowerRange(key, range) {
      if (!range || !isValidCustomPowerRange(range.startDate, range.endDate)) return false
      await this.loadPowerTrend({ key, ...range })
      return true
    },
```

5. 用以下实现替换既有 `selectLine(id)`：

```js
    async selectLine(id) {
      this._invalidatePowerRequests()
      this.selectedId = id
      this.detail = null
      this._clearPowerTrend()
      const requestVersion = this.powerRequestVersion
      const defaultRange = { key: 'yesterday', ...getRollingDateRange(1) }
      const detailRequest = getTieLineDetail(id)
        .then((res) => {
          if (requestVersion === this.powerRequestVersion && this.selectedId === id) {
            this.detail = res?.data || null
          }
        })
        .catch(() => {
          if (requestVersion === this.powerRequestVersion && this.selectedId === id) {
            this.detail = this.selectedLine
          }
        })
      const trendRequest = this.loadPowerTrend(defaultRange)
      await Promise.all([detailRequest, trendRequest])
    },
```

6. 用以下实现替换 `clearSelection()`：

```js
    clearSelection() {
      this._invalidatePowerRequests()
      this.selectedId = null
      this.detail = null
      this._clearPowerTrend()
    },
```

该版本号是所有趋势请求的单调令牌：选择新线路、清空选择、切换范围都会使先前请求不可写回。详情请求捕获的是选择时版本号，避免现有静态详情也发生旧响应覆盖新选线。

- [ ] **Step 5: 运行 Store 测试并修正异步断言**

```bash
pnpm vitest run tests/tie-line-store.spec.js
```

预期：PASS。若“默认昨天”断言因实际日期不同失败，测试必须调用 `getRollingDateRange(1)` 比较而非硬编码当前日期。

- [ ] **Step 6: 提交前端 Store 与 API 基础能力**

```bash
git add agent-frontend/src/api/tieLine.js agent-frontend/src/store/modules/tieLine.js agent-frontend/tests/tie-line-store.spec.js
git commit -m "feat: add tie line power trend state"
```

### Task 4：创建趋势组件并接入右侧详情面板

**Files:**
- Create: `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue:1-92`
- Modify: `agent-frontend/src/views/tie-line/index.vue:49-55`
- Create: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js:17-79`

- [ ] **Step 1: 写出趋势组件和详情面板的失败测试**

新建 `agent-frontend/tests/tie-line-power-trend.spec.js`。Mock `useEcharts`，使测试无需初始化 canvas：

```js
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const chart = vi.hoisted(() => ({ optionFactory: null }))
vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: (optionFactory) => {
    chart.optionFactory = optionFactory
    return { el: ref(null) }
  },
  xcVar: (token) => token,
}))

import TieLinePowerTrend from '@/views/tie-line/components/TieLinePowerTrend.vue'

const points = Array.from({ length: 96 }, (_, index) => ({
  time: index === 95 ? '24:00' : `${String(Math.floor((index + 1) / 4)).padStart(2, '0')}:${['15', '30', '45', '00'][(index + 1) % 4]}`,
  powerMw: index === 1 ? null : index + 100,
}))

describe('联络线功率趋势', () => {
  it('显示五种范围入口，并以 96 点和断点配置渲染图表', () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 1, points },
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
    })

    expect(wrapper.text()).toContain('昨日')
    expect(wrapper.text()).toContain('7日')
    expect(wrapper.text()).toContain('30日')
    expect(wrapper.text()).toContain('90日')
    expect(wrapper.text()).toContain('自定义')
    const option = chart.optionFactory()
    expect(option.xAxis.data).toHaveLength(96)
    expect(option.series[0].data).toHaveLength(96)
    expect(option.series[0].data[1]).toBeNull()
    expect(option.series[0].connectNulls).toBe(false)
    expect(wrapper.text()).toContain('2026-07-20 · 单日功率')
  })

  it('无日期记录时显示空态，不绘制零值线', () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-14', endDate: '2026-07-20', dataDateCount: 0, points: points.map((point) => ({ ...point, powerMw: null })) },
        range: { key: 'sevenDays', startDate: '2026-07-14', endDate: '2026-07-20' },
      },
    })

    expect(wrapper.text()).toContain('该线路在所选日期范围内暂无功率数据')
    expect(wrapper.find('.tl-power-trend__canvas').exists()).toBe(false)
  })

  it('加载失败时触发重试事件', async () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        error: '功率趋势加载失败，请稍后重试',
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
    })

    await wrapper.get('button[data-test="retry-power-trend"]').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
```

修改 `tests/tie-line-detail-panel.spec.js`：

1. mock 新组件，避免详情测试被 ECharts 影响：

```js
const TieLinePowerTrendStub = {
  template: '<section data-test="power-trend">功率趋势组件</section>',
}
```

2. 首个测试挂载时为 `global.stubs` 加入：

```js
global: { stubs: { TieLinePowerTrend: TieLinePowerTrendStub } },
```

3. 删除两处 `功率时序数据未接入` 断言，替换为：

```js
expect(wrapper.find('[data-test="power-trend"]').exists()).toBe(true)
```

4. 在“无线路时直接展示最长线路详情”测试中加入：

```js
expect(wrapper.find('[data-test="power-trend"]').exists()).toBe(false)
```

这锁定“趋势仅针对已选线路，不对默认推荐线路请求或展示”的边界。

- [ ] **Step 2: 运行前端组件测试，确认组件未创建时失败**

```bash
pnpm vitest run tests/tie-line-power-trend.spec.js tests/tie-line-detail-panel.spec.js
```

预期：失败并报告 `TieLinePowerTrend.vue` 不存在或详情仍输出旧占位。

- [ ] **Step 3: 实现独立趋势组件**

新建 `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`，写入：

```vue
<template>
  <section class="tl-power-trend" aria-label="功率趋势">
    <div class="tl-power-trend__head">
      <div>
        <span class="tl-power-trend__eyebrow">功率趋势</span>
        <strong class="tl-power-trend__caption">{{ rangeCaption }}</strong>
      </div>
    </div>

    <div class="tl-power-trend__ranges" role="group" aria-label="功率趋势日期范围">
      <button
        v-for="item in presetRanges"
        :key="item.key"
        class="tl-power-trend__range"
        :class="{ 'tl-power-trend__range--active': range?.key === item.key }"
        type="button"
        @click="selectPreset(item)"
      >{{ item.label }}</button>
      <button
        class="tl-power-trend__range"
        :class="{ 'tl-power-trend__range--active': range?.key === 'custom' }"
        type="button"
        @click="customVisible = true"
      >自定义</button>
    </div>

    <div v-if="loading" class="tl-power-trend__skeleton" aria-live="polite">
      <span class="xc-skeleton xc-skeleton-rect" aria-hidden="true" />
      <span>正在加载功率趋势</span>
    </div>
    <div v-else-if="error" class="tl-power-trend__state" role="alert">
      <span>{{ error }}</span>
      <button class="xc-btn xc-btn--ghost" type="button" data-test="retry-power-trend" @click="$emit('retry')">重试</button>
    </div>
    <div v-else-if="isEmpty" class="tl-power-trend__state">该线路在所选日期范围内暂无功率数据</div>
    <div v-else-if="trend" ref="el" class="tl-power-trend__canvas" />

    <ElDialog v-model="customVisible" title="自定义功率趋势日期" width="min(520px, calc(100vw - 32px))" append-to-body>
      <ElDatePicker
        v-model="customDates"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        :disabled-date="disableAfterYesterday"
      />
      <template #footer>
        <button class="xc-btn xc-btn--ghost" type="button" @click="customVisible = false">取消</button>
        <button class="xc-btn xc-btn--primary" type="button" :disabled="!isCustomRangeValid" @click="confirmCustom">确认</button>
      </template>
    </ElDialog>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { getRollingDateRange, isValidCustomPowerRange } from '@/store/modules/tieLine'
import { useEcharts, xcVar } from '@/views/home/composables/useEcharts'

const props = defineProps({
  trend: { type: Object, default: null },
  range: { type: Object, default: () => ({ key: 'yesterday', ...getRollingDateRange(1) }) },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['range-change', 'retry'])

const presetRanges = [
  { key: 'yesterday', label: '昨日', days: 1 },
  { key: 'sevenDays', label: '7日', days: 7 },
  { key: 'thirtyDays', label: '30日', days: 30 },
  { key: 'ninetyDays', label: '90日', days: 90 },
]
const customVisible = ref(false)
const customDates = ref([])
const yesterday = () => getRollingDateRange(1).endDate
const isEmpty = computed(() => props.trend?.dataDateCount === 0)
const isCustomRangeValid = computed(() => isValidCustomPowerRange(customDates.value?.[0], customDates.value?.[1]))
const rangeCaption = computed(() => {
  if (!props.trend) return '等待选择线路'
  const { startDate, endDate } = props.trend
  if (startDate === endDate) return `${startDate} · 单日功率`
  const dayCount = Math.round((new Date(`${endDate}T00:00:00`) - new Date(`${startDate}T00:00:00`)) / 86400000) + 1
  return `${startDate} 至 ${endDate} · 各时刻平均功率（${dayCount}日）`
})

function selectPreset(item) {
  emit('range-change', { key: item.key, ...getRollingDateRange(item.days) })
}
function disableAfterYesterday(value) {
  return value.getTime() > new Date(`${yesterday()}T23:59:59`).getTime()
}
function confirmCustom() {
  if (!isCustomRangeValid.value) return
  emit('range-change', { key: 'custom', startDate: customDates.value[0], endDate: customDates.value[1] })
  customVisible.value = false
}

const buildOption = () => {
  const points = props.trend?.points || []
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (items) => {
        const item = items?.[0]
        if (!item) return ''
        return `${item.axisValue}<br/>功率：${formatNumber(item.data, 3)} MW`
      },
    },
    grid: { left: 8, right: 12, top: 20, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.time),
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 10, interval: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    yAxis: {
      type: 'value',
      name: 'MW',
      nameTextStyle: { color: xcVar('--xc-text-mute'), fontSize: 10 },
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 10 },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    series: [{
      name: '功率', type: 'line', smooth: false, showSymbol: false, connectNulls: false,
      lineStyle: { width: 2, color: xcVar('--xc-chart-1') },
      itemStyle: { color: xcVar('--xc-chart-1') },
      data: points.map((point) => point.powerMw),
    }],
  }
}
const { el } = useEcharts(buildOption)
</script>

<style scoped>
.tl-power-trend { margin-top: var(--xc-space-5); padding-top: var(--xc-space-4); border-top: 1px solid var(--xc-border-soft); }
.tl-power-trend__head { display: flex; align-items: start; justify-content: space-between; gap: var(--xc-space-3); }
.tl-power-trend__eyebrow { display: block; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-power-trend__caption { display: block; margin-top: var(--xc-space-1); color: var(--xc-text-strong); font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-semi); }
.tl-power-trend__ranges { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: var(--xc-space-1); margin-top: var(--xc-space-3); }
.tl-power-trend__range { min-width: 0; padding: var(--xc-space-1); color: var(--xc-text-mute); background: var(--xc-surface-tinted); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); font-size: var(--xc-fs-2xs); cursor: pointer; }
.tl-power-trend__range--active { color: var(--xc-text-strong); border-color: var(--xc-accent-blue); background: var(--xc-surface-raised); }
.tl-power-trend__canvas { width: 100%; height: 220px; margin-top: var(--xc-space-3); }
.tl-power-trend__skeleton, .tl-power-trend__state { display: grid; place-content: center; min-height: 220px; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); text-align: center; }
.tl-power-trend__skeleton .xc-skeleton { width: 100%; height: 160px; }
</style>
```

注意：这里复用 `useEcharts`，而不是在组件内另建 ECharts 生命周期；单序列不使用 legend；`formatNumber(null, 3)` 已统一返回 `—`；颜色均为运行时读取的 XC token。

- [ ] **Step 4: 以趋势组件替换详情中的旧占位，并只给已选线路渲染**

在 `TieLineDetailPanel.vue`：

1. 删除当前第 28–32 行的 `.tl-detail__data-state` 占位区。
2. 在相同位置加入：

```vue
<TieLinePowerTrend
  v-if="line"
  :trend="powerTrend"
  :range="powerRange"
  :loading="powerTrendLoading"
  :error="powerTrendError"
  @range-change="$emit('power-range-change', $event)"
  @retry="$emit('retry-power-trend')"
/>
```

3. 在 `<script setup>` import 后加入：

```js
import TieLinePowerTrend from './TieLinePowerTrend.vue'
```

4. 扩展 `defineProps`：

```js
  powerTrend: { type: Object, default: null },
  powerRange: { type: Object, default: () => ({}) },
  powerTrendLoading: { type: Boolean, default: false },
  powerTrendError: { type: String, default: '' },
```

5. 在 `defineProps` 之后加入：

```js
const emit = defineEmits(['power-range-change', 'retry-power-trend'])
```

模板中直接 `$emit` 即可；若 ESLint 强制未使用 `emit`，删除该常量并保留 `defineEmits([...])` 调用。

6. 删除 `.tl-detail__data-state`、`.tl-detail__data-state-label` 以及相关 `strong/p` CSS；保留其余静态详情样式。

- [ ] **Step 5: 从页面将 Store 趋势状态与事件传给详情面板**

在 `agent-frontend/src/views/tie-line/index.vue` 的 `<TieLineDetailPanel>` 上补充：

```vue
        :power-trend="store.powerTrend"
        :power-range="store.powerRange"
        :power-trend-loading="store.powerTrendLoading"
        :power-trend-error="store.powerTrendError"
        @power-range-change="({ key, ...range }) => store.setPowerRange(key, range)"
        @retry-power-trend="store.loadPowerTrend()"
```

不在页面中增加新的请求逻辑；请求与竞态仍全部在 Store 内。

- [ ] **Step 6: 运行组件与 Store 定向测试，确认通过**

```bash
pnpm vitest run tests/tie-line-power-trend.spec.js tests/tie-line-detail-panel.spec.js tests/tie-line-store.spec.js
```

预期：PASS。若 `ElDialog` / `ElDatePicker` 未被自动解析，在测试挂载配置中通过 `global.stubs: { ElDialog: true, ElDatePicker: true }` stub 它们，而不修改组件生产逻辑。

- [ ] **Step 7: 提交趋势组件接线**

```bash
git add agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue agent-frontend/src/views/tie-line/index.vue agent-frontend/tests/tie-line-power-trend.spec.js agent-frontend/tests/tie-line-detail-panel.spec.js
git commit -m "feat: show tie line power trend in detail panel"
```

### Task 5：完善自定义日期交互回归、全量验证与模块文档

**Files:**
- Modify: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Modify: `agent-frontend/tests/tie-line-store.spec.js`
- Modify: `my_projects/联络线地图模块-功能与开发文档.md:29-33,136-156,174-189`

- [ ] **Step 1: 增加自定义日期确认、取消与范围竞态的失败测试**

在 `tests/tie-line-power-trend.spec.js` 追加：

```js
it('自定义日期仅在确认后触发范围变更，且当天不可确认', async () => {
  const wrapper = mount(TieLinePowerTrend, {
    props: { range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' } },
    global: { stubs: { ElDialog: false, ElDatePicker: true } },
  })

  await wrapper.get('button').trigger('click')
  expect(wrapper.emitted('range-change')).toBeUndefined()
  await wrapper.get('button').trigger('click')
  expect(wrapper.emitted('range-change')).toBeUndefined()
})
```

将这个粗略测试替换为可精确控制日期选择器的实现：给 `ElDatePicker` 使用可交互 stub，`modelValue` 使用 `update:modelValue` 事件传入 `['2026-07-18', '2026-07-20']`，点击“确认”后断言：

```js
expect(wrapper.emitted('range-change')[0][0]).toEqual({
  key: 'custom', startDate: '2026-07-18', endDate: '2026-07-20',
})
```

再用 `['2026-07-20', formatLocalToday]`（从 `getRollingDateRange(1)` 推导今天而非硬编码）验证确认按钮 disabled 且没有 `range-change`。

在 `tests/tie-line-store.spec.js` 追加同线路范围竞态：

```js
it('同一线路快速切换范围时，只保留后发范围的趋势结果', async () => {
  let resolveYesterday
  let resolveSevenDays
  api.getTieLineDetail.mockResolvedValue({ data: { id: 1 } })
  api.getTieLinePower
    .mockImplementationOnce(() => new Promise((resolve) => { resolveYesterday = resolve }))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveSevenDays = resolve }))
  const store = useTieLineStore()

  const initial = store.selectLine(1)
  const sevenDays = getRollingDateRange(7)
  const change = store.setPowerRange('sevenDays', sevenDays)
  resolveSevenDays({ data: { lineId: 1, startDate: sevenDays.startDate, points: [{ time: '00:15', powerMw: 200 }] } })
  await change
  resolveYesterday({ data: { lineId: 1, points: [{ time: '00:15', powerMw: 100 }] } })
  await initial

  expect(store.powerRange).toEqual({ key: 'sevenDays', ...sevenDays })
  expect(store.powerTrend.points[0].powerMw).toBe(200)
})
```

- [ ] **Step 2: 运行新增测试并确认失败后，修正生产实现**

```bash
pnpm vitest run tests/tie-line-power-trend.spec.js tests/tie-line-store.spec.js
```

预期：若自定义日期测试暴露 `customDates` 未在打开时初始化，则在自定义按钮 click handler 中增加：

```js
function openCustom() {
  customDates.value = props.range?.startDate && props.range?.endDate
    ? [props.range.startDate, props.range.endDate]
    : []
  customVisible.value = true
}
```

并将自定义按钮的 `@click="customVisible = true"` 改为 `@click="openCustom"`。若“结束日为今天”在跨时区测试中未被阻止，使用 `isValidCustomPowerRange()` 的实际 `yesterday` 结果推导非法结束日：

```js
const tomorrowOfYesterday = new Date(`${getRollingDateRange(1).endDate}T00:00:00`)
tomorrowOfYesterday.setDate(tomorrowOfYesterday.getDate() + 1)
```

然后以本地格式传入，禁止在测试或实现中使用 `toISOString()`。

- [ ] **Step 3: 更新联络线模块文档**

修改 `my_projects/联络线地图模块-功能与开发文档.md`：

1. 在第 29–33 行的首版占位列表中移除“功率趋势”；保留“自动刷新、基于真实功率时序的潮流方向/强度/动画”等未实现项，并删除“底表无任何 MW 时序”的过期断言。
2. 在第 31 节能力表增加“功率趋势”：右侧已选线路可查询昨天、7/30/90 日或自定义范围；固定 96 个 15 分钟点，区间按同一时刻非空值求平均。
3. 将第 5.1 的标题由“功率时序数据导入（已具备）”改为“功率时序数据导入与趋势查询（已具备）”，补充：

```text
GET /ir/tie-lines/{id}/power?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```

并明确：日期最大为自然日昨天；单日返回原始时刻值，区间返回逐时刻非空均值；无数据时 96 个值都为 `null`；趋势只在右侧已选线路展示，不改变地图静态箭头或潮流表达。

4. 将第 5.2 未来展示说明改为仅保留尚未实现的“真实潮流方向/强度/动画、自动刷新、顶部最高最低/数据条数指标”；禁止再描述趋势图为“待实现”。
5. 在第 6 节验证方式新增：

```bash
# 后端趋势端点
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/test_tie_line_power_trend_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"

# 前端趋势组件与 Store
pnpm vitest run tests/tie-line-power-trend.spec.js tests/tie-line-store.spec.js tests/tie-line-detail-panel.spec.js
```

- [ ] **Step 4: 运行前端全量测试与生产构建**

在 `agent-frontend/` 执行：

```bash
pnpm test
pnpm build
```

预期：两个命令均以退出码 0 完成。若 Node 未在 PATH，先执行：

```bash
export PATH="/c/Program Files/nodejs:$PATH"
```

- [ ] **Step 5: 运行后端完整联络线回归并检查工作树**

在 `agent-backend/` 执行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/tie_line_map/', 'tests/unit/tie_line_map/', 'tests/unit/test_architecture_layout.py', '-q', '-o', 'asyncio_mode=auto']))"
```

随后在仓库根执行：

```bash
git diff --check
git status --short
```

预期：测试通过，`git diff --check` 无空白错误，状态只包含本计划中的源文件、测试和文档；不执行 `git add`/`git commit`，除非当前用户明确授权。

- [ ] **Step 6: 在获授权后提交文档和最终修订**

```bash
git add agent-frontend/tests/tie-line-power-trend.spec.js agent-frontend/tests/tie-line-store.spec.js my_projects/联络线地图模块-功能与开发文档.md
git commit -m "docs: document tie line power trend"
```

## 覆盖自检

- **自然日昨天边界与自定义禁用当天：** Task 2 路由校验、Task 3 本地日期工具、Task 4 `disabledDate`、Task 5 回归测试。
- **固定 96 点与分时平均：** Task 1 端点失败测试、Task 2 `POWER_TIME_COLUMNS` 驱动聚合、Task 4 ECharts 数据映射。
- **忽略空值、全空断点、不补零：** Task 1 测试、Task 2 `_average_power`、Task 4 `connectNulls: false` 与空态。
- **仅已选线路展示与切线重查：** Task 3 `selectLine()`、Task 4 `v-if="line"`、详情回归测试。
- **旧请求不覆盖新选择：** Task 3 请求版本号和竞态测试、Task 5 同线路范围竞态测试。
- **错误、骨架、重试：** Task 3 状态、Task 4 局部 UI、Task 4 测试。
- **不改变地图潮流语义与数据表结构：** 文件结构和 Task 5 模块文档明确限定；实现任务不修改地图组件、ORM 或 DDL。

## 实施前注意事项

1. 本计划包含提交命令仅用于独立执行环境的细粒度检查点；仓库根规则禁止未经用户明确要求的 Git 写操作，执行者必须遵守该更高优先级规则。
2. 现有历史 `ir_tie_line_power` 记录如 `line_id` 为空，趋势接口将按已确认口径返回空数据；上线前应由数据维护流程回填，不在读取接口增加名称回退。
3. 服务端 `date.today()` 按部署进程本地时区计算；生产部署必须使用业务自然日时区（中国业务场景通常为 Asia/Shanghai），否则“昨天”边界会偏移。
