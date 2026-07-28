# 全国储能投资指数地图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建成从数据库只读查询、按期次展示并支持省级详情联动的全国储能投资指数地图。

**Architecture:** 后端新增独立 `index_map` 限界上下文，以 `interface → application → domain` 分层读取两张指数表并暴露期次、概览与省份详情接口。前端新增独立 API、Pinia Store、页面和聚焦组件，复用现有中国 GeoJSON、ECharts 生命周期与 XC token；概览请求和详情请求分别用递增版本号防止竞态覆盖。

**Tech Stack:** FastAPI、SQLAlchemy Async、MySQL 8 / SQLite 测试、Vue 3、Pinia、ECharts 5、Vitest、Vue Test Utils、XC CSS token。

---

## 文件结构

### 后端

- 创建 `agent-backend/app/modules/index_map/domain/models.py`：不可变期次、概览、省份详情领域模型。
- 创建 `agent-backend/app/modules/index_map/infrastructure/persistence/orm.py`：期次和省份指数 ORM。
- 创建 `agent-backend/app/modules/index_map/application/index_map_service.py`：概览聚合、详情查询、排序与未找到处理。
- 创建 `agent-backend/app/modules/index_map/interface/serializers.py`：领域模型到 camelCase JSON 的唯一映射。
- 创建 `agent-backend/app/modules/index_map/interface/router.py`：三个只读 HTTP 路由和 `period` 参数校验。
- 修改 `agent-backend/app/main.py`：注册指数地图路由。
- 修改 `agent-backend/sql/ir_agent_schema.sql`：添加数据表、唯一约束与查询索引。
- 创建 `agent-backend/tests/unit/index_map/test_index_map_orm.py`：ORM 元数据约束测试。
- 创建 `agent-backend/tests/unit/index_map/test_index_map_service.py`：服务排序、空值和不存在资源测试。
- 创建 `agent-backend/tests/e2e/index_map/test_index_map_endpoints.py`：ASGITransport 端点契约测试。

### 前端

- 创建 `agent-frontend/src/api/indexMap.js`：三组只读 API 薄封装。
- 创建 `agent-frontend/src/store/modules/indexMap.js`：期次、概览、选省、详情和竞态控制。
- 创建 `agent-frontend/src/views/index-map/indexMapPresentation.js`：S/A/B/C 规范化、等级文案和地图 option 工厂。
- 创建 `agent-frontend/src/views/index-map/components/ChinaIndexMap.vue`：中国地图、Tooltip、选省、缩放/复位/全屏。
- 创建 `agent-frontend/src/views/index-map/components/IndexMapToolbar.vue`：缩放、复位、全屏工具按钮。
- 创建 `agent-frontend/src/views/index-map/components/IndexPeriodSelect.vue`：期次选择器。
- 创建 `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`：四张全国总览卡。
- 创建 `agent-frontend/src/views/index-map/components/IndexRankingList.vue`：可选省的 Top 5 榜单。
- 创建 `agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`：严格按原型渲染的右侧省份详情与独立状态。
- 创建 `agent-frontend/src/views/index-map/index.vue`：页面编排、加载/错误状态及事件转发。
- 修改 `agent-frontend/src/router/index.js`：注册 `/index-map`。
- 修改 `agent-frontend/src/layout/components/AppRail.vue`：启用全国指数地图入口。
- 修改 `agent-frontend/src/layout/index.vue`：建立 `index` 与 `/index-map` 双向导航映射。
- 创建 `agent-frontend/tests/index-map-store.spec.js`：Store 期次、详情、竞态与重试测试。
- 创建 `agent-frontend/tests/index-map-presentation.spec.js`：等级映射与 ECharts option 测试。
- 创建 `agent-frontend/tests/index-map-detail.spec.js`：详情字段及独立状态测试。
- 创建 `agent-frontend/tests/index-map-page.spec.js`：页面联动测试。
- 修改 `agent-frontend/tests/app-rail.spec.js`：入口启用后的断言。

> 本仓库规则禁止 Git 写操作。本计划中的每项验证完成后只检查工作区状态，**不执行** `git add`、`git commit` 或 `git push`。

### Task 1: 建立后端查询表与领域模型

**Files:**
- Create: `agent-backend/app/modules/index_map/domain/models.py`
- Create: `agent-backend/app/modules/index_map/infrastructure/persistence/orm.py`
- Modify: `agent-backend/sql/ir_agent_schema.sql`
- Test: `agent-backend/tests/unit/index_map/test_index_map_orm.py`

- [ ] **Step 1: 编写 ORM 元数据失败测试**

```python
from app.modules.index_map.infrastructure.persistence.orm import (
    IndexMapPeriodORM,
    IndexMapProvinceORM,
)


def test_index_map_tables_have_period_province_unique_key_and_query_indexes():
    assert IndexMapPeriodORM.__tablename__ == "ir_index_map_period"
    assert IndexMapProvinceORM.__tablename__ == "ir_index_map_province"
    assert {column.name for column in IndexMapProvinceORM.__table__.columns} >= {
        "period", "province_code", "map_name", "index_score", "grade", "opened",
        "rank", "annualized_return", "detail_payload", "updated_at",
    }
    assert any(index.unique and set(index.columns.keys()) == {"period", "province_code"}
               for index in IndexMapProvinceORM.__table__.indexes)
    assert any(set(index.columns.keys()) == {"period", "rank"}
               for index in IndexMapProvinceORM.__table__.indexes)
```

- [ ] **Step 2: 运行测试确认失败**

运行：

```bash
cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/index_map/test_index_map_orm.py', '-q']))"
```

预期：失败，原因是 `app.modules.index_map` 尚不存在。

- [ ] **Step 3: 实现最小领域模型与 ORM**

在 `domain/models.py` 定义 frozen dataclass：`IndexPeriod`、`ProvinceIndexSummary`、`IndexOverview`、`ProvinceIndexDetail`。其中详情的可变结构以不可变 tuple 承载，字段名称与设计规格第 3 节保持一致。

在 `orm.py` 实现：

```python
class IndexMapPeriodORM(Base):
    __tablename__ = "ir_index_map_period"
    period: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class IndexMapProvinceORM(Base):
    __tablename__ = "ir_index_map_province"
    __table_args__ = (
        Index("uk_ir_index_map_province_period_code", "period", "province_code", unique=True),
        Index("ix_ir_index_map_province_period_rank", "period", "rank"),
        Index("ix_ir_index_map_province_period_score", "period", "index_score"),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String(32), ForeignKey("ir_index_map_period.period"), nullable=False)
    province_code: Mapped[str] = mapped_column(String(32), nullable=False)
    province_name: Mapped[str] = mapped_column(String(64), nullable=False)
    map_name: Mapped[str] = mapped_column(String(64), nullable=False)
    index_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    grade: Mapped[str | None] = mapped_column(String(8))
    opened: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    rank: Mapped[int | None] = mapped_column(Integer)
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    detail_payload: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

在 DDL 追加等价的 `ir_index_map_period` 和 `ir_index_map_province` 建表语句、外键、唯一键和两个查询索引；`detail_payload` 使用 MySQL `JSON`。

- [ ] **Step 4: 运行 ORM 测试确认通过**

运行：同 Step 2。

预期：`1 passed`。

### Task 2: 实现后端查询服务与序列化

**Files:**
- Create: `agent-backend/app/modules/index_map/application/index_map_service.py`
- Create: `agent-backend/app/modules/index_map/interface/serializers.py`
- Test: `agent-backend/tests/unit/index_map/test_index_map_service.py`

- [ ] **Step 1: 编写服务失败测试**

```python
@pytest.mark.asyncio
async def test_overview_uses_score_then_code_for_heat_ranking(session):
    session.add_all([
        IndexMapPeriodORM(period="2026-07", label="2026年7月", updated_at=NOW),
        _province("2026-07", "B", "乙", 90, "S", True, 2, 7.1),
        _province("2026-07", "A", "甲", 90, "S", True, 1, 8.1),
        _province("2026-07", "C", "丙", 60, "C", False, 3, 9.1),
    ])
    await session.commit()

    overview = await IndexMapService().get_overview(session, period="2026-07")

    assert [item.province_code for item in overview.investment_heat] == ["A", "B", "C"]
    assert [item.province_code for item in overview.return_stability] == ["C", "A", "B"]
    assert overview.opened_grade_counts == {"S": 2, "A": 0, "B": 0}
    assert overview.high_potential_count == 1
```

同时测试：`list_periods()` 按 `updated_at` 倒序；不存在期次抛出项目既有 `NotFoundException`；不存在省份抛出同一异常；`detail_payload is None` 时详情对象为 `None`。

- [ ] **Step 2: 运行服务测试确认失败**

运行：

```bash
cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/index_map/test_index_map_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：失败，原因是 `IndexMapService` 尚未定义。

- [ ] **Step 3: 实现查询、排序和序列化**

实现 `IndexMapService` 的三个异步方法：

```python
async def list_periods(self, session: AsyncSession) -> list[IndexPeriod]: ...
async def get_overview(self, session: AsyncSession, *, period: str) -> IndexOverview: ...
async def get_province_detail(self, session: AsyncSession, *, period: str, province_code: str) -> ProvinceIndexDetail | None: ...
```

实现约束：

- 通过 `select(IndexMapPeriodORM).order_by(IndexMapPeriodORM.updated_at.desc(), IndexMapPeriodORM.period.desc())` 读取期次；
- `get_overview` 首先验证期次存在，再一次性读取该期所有 `IndexMapProvinceORM`；
- 投资热力榜按 `index_score.desc().nullslast()`、`province_code.asc()` 取前五；收益稳定榜按 `annualized_return.desc().nullslast()`、`province_code.asc()` 取前五；
- `S/A/B` 且 `opened=True` 才计入 `opened_grade_counts`；合法 `C` 计入高潜；非法等级不计入；
- `detail_payload` 只由详情接口读取，不回传至概览；
- 序列化器只输出设计规格定义的 camelCase 字段，将 Decimal 转为 JSON number，将 `datetime` 转 ISO 8601 字符串，将 `None` 保持 `null`。

- [ ] **Step 4: 运行服务测试确认通过**

运行：同 Step 2。

预期：所有 `test_index_map_service.py` 用例通过。

### Task 3: 暴露后端接口并验证端点契约

**Files:**
- Create: `agent-backend/app/modules/index_map/interface/router.py`
- Modify: `agent-backend/app/main.py:34-46`
- Test: `agent-backend/tests/e2e/index_map/test_index_map_endpoints.py`

- [ ] **Step 1: 编写端点失败测试**

沿用联络线端点的内存 SQLite + `StaticPool` fixture，插入一个期次和三条省份记录。测试：

```python
@pytest.mark.asyncio
async def test_index_map_query_contract(seeded_client):
    periods = await seeded_client.get("/ir/index-map/periods")
    assert periods.status_code == 200
    assert periods.json()["data"]["items"][0]["period"] == "2026-07"

    overview = await seeded_client.get("/ir/index-map/overview", params={"period": "2026-07"})
    assert overview.status_code == 200
    item = overview.json()["data"]["provinces"][0]
    assert {"provinceCode", "mapName", "indexScore", "grade", "opened", "rank", "updatedAt"} <= item.keys()

    detail = await seeded_client.get("/ir/index-map/provinces/NMG", params={"period": "2026-07"})
    assert detail.status_code == 200
    assert detail.json()["data"]["maturity"]["scores"][0]["key"] == "spot"
```

另外测试：缺失或空 `period` 返回项目统一的 400；不存在期次或省份返回响应壳 `code == 404`；无 `detail_payload` 的省份成功返回 `data: null`。

- [ ] **Step 2: 运行端点测试确认失败**

运行：

```bash
cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/index_map/test_index_map_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：失败，路由尚未注册。

- [ ] **Step 3: 实现路由并注册**

在 `router.py` 创建：

```python
router = APIRouter(prefix="/ir/index-map", tags=["index-map"])

@router.get("/periods")
async def list_periods(session: AsyncSession = Depends(get_db_session)):
    return ok(serialize_periods(await _service.list_periods(session)))

@router.get("/overview")
async def get_overview(period: str | None = Query(default=None), session: AsyncSession = Depends(get_db_session)):
    return ok(serialize_overview(await _service.get_overview(session, period=_require_period(period))))

@router.get("/provinces/{province_code}")
async def get_province_detail(province_code: str, period: str | None = Query(default=None), session: AsyncSession = Depends(get_db_session)):
    return ok(serialize_province_detail(await _service.get_province_detail(session, period=_require_period(period), province_code=province_code)))
```

`_require_period` 对空白字符串抛 `ValidationException("period 不能为空")`。在 `app/main.py` 导入 `index_map_router` 并在 `register_routers()` 中调用 `app.include_router(index_map_router)`。

- [ ] **Step 4: 运行端点与相关后端测试**

运行：

```bash
cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/index_map', 'tests/e2e/index_map', 'tests/e2e/tie_line_map', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：所有上述测试通过。

### Task 4: 建立前端 API、Store 与竞态保护

**Files:**
- Create: `agent-frontend/src/api/indexMap.js`
- Create: `agent-frontend/src/store/modules/indexMap.js`
- Test: `agent-frontend/tests/index-map-store.spec.js`

- [ ] **Step 1: 编写 Store 失败测试**

mock `@/api/indexMap`，在测试中验证：

```javascript
it('默认选择最新期次，加载概览并选择领跑省份', async () => {
  listIndexMapPeriods.mockResolvedValue({ data: { items: [{ period: '2026-07' }] } })
  getIndexMapOverview.mockResolvedValue({ data: overview })
  getIndexMapProvinceDetail.mockResolvedValue({ data: detail })

  const store = useIndexMapStore()
  await store.initialize()

  expect(store.activePeriod).toBe('2026-07')
  expect(store.selectedProvinceCode).toBe('NMG')
  expect(getIndexMapProvinceDetail).toHaveBeenCalledWith('NMG', '2026-07')
})
```

添加测试：切换期次时优先保留仍存在的已选省；不存在则回退领跑省；后发详情请求完成后旧请求返回不覆盖新详情；概览失败仅设置 `overviewError`；详情失败仅设置 `detailError`；重试调用当前请求。

- [ ] **Step 2: 运行测试确认失败**

运行：

```bash
cd agent-frontend && npm exec vitest -- run tests/index-map-store.spec.js
```

预期：失败，API 与 Store 尚未定义。

- [ ] **Step 3: 实现 API 和 Store**

`src/api/indexMap.js`：

```javascript
export const listIndexMapPeriods = () => request({ url: '/ir/index-map/periods', method: 'get' })
export const getIndexMapOverview = (period) => request({ url: '/ir/index-map/overview', method: 'get', params: { period } })
export const getIndexMapProvinceDetail = (provinceCode, period) => request({ url: `/ir/index-map/provinces/${provinceCode}`, method: 'get', params: { period } })
```

Store state 至少含：`periods`、`activePeriod`、`overview`、`selectedProvinceCode`、`provinceDetail`、`periodsLoading`、`overviewLoading`、`detailLoading`、`periodsError`、`overviewError`、`detailError`、`overviewRequestVersion`、`detailRequestVersion`。

实现 `initialize()`、`selectPeriod(period)`、`selectProvince(provinceCode)`、`retryOverview()`、`retryDetail()`。每次切期次递增两个版本号；详情请求捕获当前 `period` 与 `provinceCode`，仅当版本和当前选择仍相同时写状态。加载成功后用 `overview.summary.leader.provinceCode` 作为回退选择。

- [ ] **Step 4: 运行 Store 测试确认通过**

运行：同 Step 2。

预期：所有 Store 用例通过。

### Task 5: 构建等级映射、地图 option 与地图工具

**Files:**
- Create: `agent-frontend/src/views/index-map/indexMapPresentation.js`
- Create: `agent-frontend/src/views/index-map/components/ChinaIndexMap.vue`
- Create: `agent-frontend/src/views/index-map/components/IndexMapToolbar.vue`
- Test: `agent-frontend/tests/index-map-presentation.spec.js`

- [ ] **Step 1: 编写地图表达失败测试**

```javascript
it('将 S/A/B/C 映射到固定等级，并将非法等级归为未覆盖', () => {
  expect(normalizeIndexGrade('S')).toBe('S')
  expect(normalizeIndexGrade('A')).toBe('A')
  expect(normalizeIndexGrade('C')).toBe('C')
  expect(normalizeIndexGrade('X')).toBeNull()
})

it('option 的 tooltip 只输出省份、指数、等级排名、更新时间', () => {
  const option = buildIndexMapOption({ provinces: [province], selectedProvinceCode: null, theme })
  expect(option.tooltip.formatter({ data: option.series[0].data[0] })).toContain('95')
  expect(option.tooltip.formatter({ data: option.series[0].data[0] })).not.toContain('annualizedReturn')
})
```

同时断言：五个 visualMap/legend 状态中 S/A/B/C 有固定顺序且未覆盖无等级标签；`geo.scaleLimit` 复用联络线默认缩放上下界；选中区域 `emphasis` 有明确高亮；地图点击传出 `provinceCode`。

- [ ] **Step 2: 运行测试确认失败**

运行：

```bash
cd agent-frontend && npm exec vitest -- run tests/index-map-presentation.spec.js
```

预期：失败，表达模块尚未存在。

- [ ] **Step 3: 实现表达模块和地图组件**

表达模块导出 `normalizeIndexGrade`、`INDEX_GRADE_META`、`buildIndexMapOption`。`INDEX_GRADE_META` 固定顺序为 S、A、B、C，label 分别为“ S 类·已开通”“A 类·已开通”“B 类·已开通”“C 类·待开通”。颜色字段仅接收调用方注入的运行时 XC token 值。

`buildIndexMapOption` 用 `geo` 注册的 `china` 地图和 map series 数据；每个数据项携带：

```javascript
{ name: province.mapName, value: province.indexScore, provinceCode: province.provinceCode, info: province }
```

Tooltip formatter 严格只渲染 `provinceName`、`indexScore`、`${grade} 类 · 全国第 ${rank} 名`、`updatedAt`。无 `info` 时返回空字符串。

`ChinaIndexMap.vue` 复用 `china.json` 与 `useEcharts` 的 `xcVar`；挂载时 `echarts.registerMap('china', chinaGeo)`，点击 map series 时 `emit('select', params.data.provinceCode)`。暴露 `zoomIn`、`zoomOut` 和 `resetView` 给工具栏；全屏实现沿用 `ChinaTieLineMap.vue` 的 `fullscreenchange` 生命周期清理模式。所有 CSS 颜色使用 XC token。

- [ ] **Step 4: 运行地图表达测试确认通过**

运行：同 Step 2。

预期：所有表达与地图组件测试通过。

### Task 6: 实现总览、榜单、期次与省份详情组件

**Files:**
- Create: `agent-frontend/src/views/index-map/components/IndexPeriodSelect.vue`
- Create: `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
- Create: `agent-frontend/src/views/index-map/components/IndexRankingList.vue`
- Create: `agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`
- Test: `agent-frontend/tests/index-map-detail.spec.js`

- [ ] **Step 1: 编写详情和组件失败测试**

```javascript
it('完整显示原型定义的省份详情分区', () => {
  const wrapper = mount(ProvinceIndexDetail, { props: { detail, loading: false, error: '' } })
  expect(wrapper.text()).toContain('蒙西')
  expect(wrapper.text()).toContain('强烈推荐·立即布局')
  expect(wrapper.text()).toContain('市场化成熟度')
  expect(wrapper.text()).toContain('因子贡献度')
  expect(wrapper.text()).toContain('装机结构')
  expect(wrapper.text()).toContain('新能源')
  expect(wrapper.text()).toContain('火电')
  expect(wrapper.text()).toContain('储能')
})

it('详情请求失败时仅显示重试操作', async () => {
  const wrapper = mount(ProvinceIndexDetail, { props: { detail: null, loading: false, error: '加载失败' } })
  await wrapper.get('button').trigger('click')
  expect(wrapper.emitted('retry')).toEqual([[]])
})
```

增加对期次选择事件、四张总览卡字段、两张榜单的省份选择事件及“前五项”渲染的断言。

- [ ] **Step 2: 运行测试确认失败**

运行：

```bash
cd agent-frontend && npm exec vitest -- run tests/index-map-detail.spec.js
```

预期：失败，组件尚未存在。

- [ ] **Step 3: 实现展示组件**

- `IndexPeriodSelect.vue` 使用项目现有 Element Plus 下拉控件，props 为 `periods`、`modelValue`、`loading`，只 emit `update:modelValue`；
- `IndexSummaryCards.vue` 接收 `summary`，只渲染全国均值、领跑省份、已开通区域、高潜待挖掘四个卡片；
- `IndexRankingList.vue` 接收 `title`、`items`、`value-key`、`selectedProvinceCode`，每项使用 button 并 emit `select`；
- `ProvinceIndexDetail.vue` 接收 `detail`、`loading`、`error`。按原型章节顺序渲染标题/等级/圆环、推荐和年化收益率、成熟度四项、贡献条、总 GW 与三类装机卡、分析文本。数值格式调用 `formatNumber`，空值显示 `—`；“查看省级区域节点分析”仅 `ElMessage.info('区域节点分析功能将在后续开放')`，不跳路由；错误态按钮 emit `retry`。

不在这四个组件发起 API 请求；所有布局样式和色彩均走 XC token。

- [ ] **Step 4: 运行组件测试确认通过**

运行：同 Step 2。

预期：所有详情和子组件用例通过。

### Task 7: 组装页面并接入路由与导航

**Files:**
- Create: `agent-frontend/src/views/index-map/index.vue`
- Modify: `agent-frontend/src/router/index.js:14-43`
- Modify: `agent-frontend/src/layout/components/AppRail.vue:34-40`
- Modify: `agent-frontend/src/layout/index.vue:93-95`
- Modify: `agent-frontend/tests/app-rail.spec.js`
- Test: `agent-frontend/tests/index-map-page.spec.js`

- [ ] **Step 1: 编写页面和导航失败测试**

```javascript
it('进入页面时初始化数据，地图和榜单选省都转发到 Store', async () => {
  const wrapper = mount(IndexMapPage, { global: { plugins: [createTestingPinia({ stubActions: false })] } })
  const store = useIndexMapStore()
  expect(store.initialize).toHaveBeenCalledOnce()
  await wrapper.findComponent({ name: 'ChinaIndexMap' }).vm.$emit('select', 'NMG')
  expect(store.selectProvince).toHaveBeenCalledWith('NMG')
})
```

修改 `app-rail.spec.js` 为断言第 2 个按钮无 `disabled`、点击后导航事件序列为 `[['home'], ['index'], ['line'], ['policy']]`、tooltip 是“全国指数地图”。

- [ ] **Step 2: 运行测试确认失败**

运行：

```bash
cd agent-frontend && npm exec vitest -- run tests/index-map-page.spec.js tests/app-rail.spec.js
```

预期：失败，页面、路由与导航映射尚未更新。

- [ ] **Step 3: 组装页面与更新导航**

`index.vue` 在 `onMounted` 调用 `store.initialize()`；渲染顺序为：顶部标题和期次选择、地图及全局概览加载/失败遮罩、地图下方总览卡、两个榜单、右侧详情。事件连接必须为：

```vue
<ChinaIndexMap
  :provinces="store.overview?.provinces || []"
  :selected-province-code="store.selectedProvinceCode"
  @select="store.selectProvince"
/>
<IndexRankingList @select="store.selectProvince" />
<ProvinceIndexDetail
  :detail="store.provinceDetail"
  :loading="store.detailLoading"
  :error="store.detailError"
  @retry="store.retryDetail"
/>
```

地图工作区只依据 `overviewLoading`、`overviewError` 显示加载/失败态；右侧只依据 `detailLoading`、`detailError` 显示详情状态。

路由增加：

```javascript
{ path: 'index-map', name: 'IndexMap', component: () => import('@/views/index-map/index.vue'), meta: { title: '全国储能投资指数', collapseSidebar: true } }
```

将 `AppRail.vue` fallback 第 2 项更新为 `{ key: 'index', label: '全国指数地图', icon: ICON.index, disabled: false }`。在 `layout/index.vue` 中更新：

```javascript
const RAIL_TO_PATH = { home: '/home', index: '/index-map', line: '/tie-line', policy: '/policy-market' }
const PATH_TO_RAIL = { '/home': 'home', '/index-map': 'index', '/tie-line': 'line', '/policy-market': 'policy' }
```

- [ ] **Step 4: 运行页面与导航测试确认通过**

运行：同 Step 2。

预期：所有页面与导航用例通过。

### Task 8: 执行完整验证并同步项目开发指南

**Files:**
- Modify: `my_projects/investment-research-agent-项目开发指南.md`（前端视图、后端模块、API 和验证章节中新增全国指数地图说明）

- [ ] **Step 1: 更新项目开发指南的可维护性说明**

在对应前端/后端/API 章节补充：全国指数地图路由 `/index-map`；前端 `api/indexMap.js` 和 `store/modules/indexMap.js`；后端 `app/modules/index_map`；三个只读接口；数据只读数据库，写入与飞书不属于该模块。不得写入任何凭据或生产地址。

- [ ] **Step 2: 运行后端全量测试**

运行：

```bash
cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"
```

预期：退出码 0，全部后端测试通过。

- [ ] **Step 3: 运行前端全量测试和构建**

运行：

```bash
cd agent-frontend && npm test && npm run build
```

预期：Vitest 全部通过，Vite 成功生成生产构建产物。

- [ ] **Step 4: 执行最终静态检查**

运行：

```bash
git diff --check && git status --short
```

预期：`git diff --check` 无输出；状态仅包含本功能的源码、测试、DDL、开发指南、设计规格和实施计划文件，不执行任何 Git 写操作。

## 计划自检

- 规格覆盖：任务 1-3 实现数据库只读模型、DDL 和三组 API；任务 4-7 实现期次、地图分级、Tooltip、选省、原型详情、导航和竞态；任务 8 覆盖文档与完整验证。
- 范围控制：没有数据导入、写入、定时同步、飞书访问、多指标、报告导出或区域节点分析的实现任务。
- 类型一致性：前端 `provinceCode`、`period`、`activePeriod` 与三组接口契约一致；后端 ORM 的 `detail_payload` 只用于详情接口。
- 占位扫描：计划不包含未决实现项；“占位”仅指已明确约束为信息提示、不可执行业务功能的两个原型按钮。
