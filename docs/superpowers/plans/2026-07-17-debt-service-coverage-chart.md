# 偿债能力折线图替换 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用飞书“画图数据”接口 Sheet 的 `C3:Q3` 偿债倍数数据替换原四条 15 年现金流折线，并在前端呈现绿色偿债倍数曲线及红色 `y=1` 阈值虚线。

**Architecture:** 参数字典新增一项来自 `画图数据!C3:Q3` 的只读范围输出，飞书网关沿用按参数字典批量读取与范围展平的机制。领域结果由四条现金流 DTO 改为单一 `DebtServiceCoverage` DTO，映射层只裁剪尾部空值、保留中间缺失为 `None`；报告快照通过新的 camelCase 契约直接供前端图表使用。

**Tech Stack:** Python 3.13、FastAPI、异步 SQLAlchemy、httpx、pytest；Vue 3、Vite、Vitest、Vue Test Utils、ECharts。

## Global Constraints

- 飞书只允许通过接口 Sheet 读取；本需求允许的读取接口 Sheet 为 `API_OUTPUT` 与 `画图数据`。
- 新数据源固定为 `画图数据!C3:Q3`，含义为“现金流口径下偿债倍数”。
- 数据值 `0` 是有效点；`None` 或空字符串是空点；裁剪最后一个非空点后的尾部空格，保留中间空点作为断线。
- 新图横轴标题为“贷款年限”，标签为“第1年”至最后一个有效位置；纵轴标题为“偿债倍数”。
- 业务线为绿色；固定阈值线为 `y=1` 的红色水平虚线。
- 旧四条现金流结果契约、旧图组件与旧历史快照兼容均不保留；用户会自行清理旧数据。
- 不新增依赖，不在后端重写任何财务计算公式。
- 执行 Python 命令时使用 `agent-backend/.venv/Scripts/python.exe`，不得使用 `python` 或 `python3`。
- 不执行 `git add`、`git commit`、`git push` 或任何其他 git 写操作；由用户自行处理版本控制。

---

## File Structure

### Backend

- Modify: `agent-backend/app/modules/calculation/domain/result.py`
  - 移除 `CashflowLines`，新增 `DebtServiceCoverage`；`AdvancedResult` 仅持有环形图和偿债倍数结果。
- Modify: `agent-backend/app/modules/calculation/application/output_mapper.py`
  - 读取新的参数 id，规整空值并裁剪尾部空值，映射到新 DTO。
- Modify: `agent-backend/app/modules/calculation/application/result_view.py`
  - 输出新的 `advanced.debtServiceCoverage.cashflowRatio` camelCase 报告契约。
- Modify: `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json`
  - 删除四条旧现金流 output 定义，增加 `画图数据!C3:Q3` 的偿债倍数 output 定义。
- Modify: `agent-backend/app/modules/calculation/infrastructure/feishu_sample.py`
  - Mock 输出使用新参数 id 的偿债倍数序列。
- Modify: `agent-backend/tests/unit/calculation/test_output_mapper.py`
  - 覆盖新 DTO、`0`、中间空值、尾部空值裁剪和全空序列。
- Modify: `agent-backend/tests/integration/calculation/test_feishu_http_client.py`
  - 覆盖“画图数据”Sheet 的范围寻址与二维范围读取展平。
- Modify: `agent-backend/tests/integration/calculation/test_calculation_service.py`
  - 将旧现金流长度断言替换为新偿债倍数序列断言。
- Modify: `agent-backend/tests/db/test_snapshot_service.py`
- Modify: `agent-backend/tests/db/test_calc_task_api.py`
- Modify: `agent-backend/tests/e2e/calculation/test_calc_endpoints.py`
  - 将 `advanced.lines.mainBusinessCost` 的快照/API 回归断言改为新 camelCase 载荷。

### Frontend

- Delete: `agent-frontend/src/views/home/components/CashflowLines.vue`
  - 删除旧四条现金流图组件。
- Create: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
  - 单一偿债倍数图：绿色业务线、红色 `y=1` 虚线、动态贷款年限横轴。
- Modify: `agent-frontend/src/views/home/components/ResultCard.vue`
  - 用 `DebtServiceCoverage` 替换 `CashflowLines`，传递新报告载荷对象。
- Modify: `agent-frontend/tests/charts.spec.js`
  - 覆盖新图的单一序列、断点、坐标轴、配色和阈值线。

### Design/Plan Artifacts

- Existing design: `docs/superpowers/specs/2026-07-17-debt-service-coverage-chart-design.md`
- This plan: `docs/superpowers/plans/2026-07-17-debt-service-coverage-chart.md`

## Interface Contract

### Parameter dictionary entry

Use exactly this parameter id and metadata shape:

```json
{
  "id": "cashflow_debt_service_coverage_ratio",
  "cn": "现金流口径下偿债倍数(贷款期序列)",
  "category": "输出-偿债能力(折线图)",
  "source": "output",
  "model_cell": "画图数据!C3:Q3",
  "f": 1,
  "g": 0,
  "writable": false,
  "direction": "output",
  "api_cell": "画图数据!C3:Q3",
  "default": null,
  "unit": "倍",
  "dtype": "float[]"
}
```

### Domain DTO

```python
@dataclass(frozen=True)
class DebtServiceCoverage:
    """现金流口径下偿债倍数；元素对应第 1..N 年，None 表示断点。"""
    cashflow_ratio: list[float | None] = field(default_factory=list)

@dataclass(frozen=True)
class AdvancedResult:
    donut: RevenueDonut = field(default_factory=RevenueDonut)
    debt_service_coverage: DebtServiceCoverage = field(default_factory=DebtServiceCoverage)
```

### Report payload

```json
{
  "advanced": {
    "donut": {},
    "debtServiceCoverage": {
      "cashflowRatio": [1.3, 1.4, null, 1.2]
    }
  }
}
```

## Task 1: Replace the backend result contract and output mapping

**Files:**
- Modify: `agent-backend/app/modules/calculation/domain/result.py:50-63`
- Modify: `agent-backend/app/modules/calculation/application/output_mapper.py:23-31,68-78`
- Modify: `agent-backend/app/modules/calculation/application/result_view.py:10-50`
- Modify: `agent-backend/tests/unit/calculation/test_output_mapper.py`

**Interfaces:**
- Consumes: `api_output["cashflow_debt_service_coverage_ratio"]`, a list or tuple whose entries are numbers, numeric strings, `None`, or empty strings.
- Produces: `DebtServiceCoverage.cashflow_ratio: list[float | None]` and report payload field `advanced.debtServiceCoverage.cashflowRatio`.

- [ ] **Step 1: Replace old mapping test fixtures with a failing new-contract test**

  In `agent-backend/tests/unit/calculation/test_output_mapper.py`, replace the old `main_business_cost` sample with this field and add these tests:

  ```python
  def test_maps_cashflow_debt_service_coverage_and_trims_trailing_blanks():
      result = map_output_to_result(
          _basics(),
          _assembled(),
          {"cashflow_debt_service_coverage_ratio": [1.2, 0, None, "1.5", "", None]},
      )

      assert result.advanced.debt_service_coverage.cashflow_ratio == [1.2, 0.0, None, 1.5]


  def test_maps_all_blank_cashflow_debt_service_coverage_to_empty_list():
      result = map_output_to_result(
          _basics(),
          _assembled(),
          {"cashflow_debt_service_coverage_ratio": [None, "", None]},
      )

      assert result.advanced.debt_service_coverage.cashflow_ratio == []
  ```

  Add a report-payload test using `to_report_payload`:

  ```python
  from app.modules.calculation.application.result_view import to_report_payload


  def test_report_payload_uses_debt_service_coverage_camel_case_contract():
      result = map_output_to_result(
          _basics(),
          _assembled(),
          {"cashflow_debt_service_coverage_ratio": [1.2, None, 1.4]},
      )

      assert to_report_payload(result)["advanced"]["debtServiceCoverage"] == {
          "cashflowRatio": [1.2, None, 1.4],
      }
  ```

- [ ] **Step 2: Run the unit test file to verify it fails under the old contract**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/unit/calculation/test_output_mapper.py -q
  ```

  Expected: FAIL because `AdvancedResult` has no `debt_service_coverage`, the mapper does not read `cashflow_debt_service_coverage_ratio`, and the report payload has no `debtServiceCoverage` field.

- [ ] **Step 3: Replace the domain DTO**

  In `agent-backend/app/modules/calculation/domain/result.py`, remove the complete `CashflowLines` class. Add this class in its place:

  ```python
  @dataclass(frozen=True)
  class DebtServiceCoverage:
      """现金流口径下偿债倍数；元素对应第 1..N 年，None 表示断点。"""
      cashflow_ratio: list[float | None] = field(default_factory=list)
  ```

  Replace the `AdvancedResult` declaration with:

  ```python
  @dataclass(frozen=True)
  class AdvancedResult:
      """③ 进阶图形结果。"""
      donut: RevenueDonut = field(default_factory=RevenueDonut)
      debt_service_coverage: DebtServiceCoverage = field(default_factory=DebtServiceCoverage)
  ```

  Update the top module docstring’s final bullet so it describes a single “现金流口径下偿债倍数折线图” rather than “4条15年序列”。

- [ ] **Step 4: Implement sequence normalization and map the new DTO**

  In `agent-backend/app/modules/calculation/application/output_mapper.py`:

  1. Replace the `CashflowLines` import with `DebtServiceCoverage`.
  2. Replace `_seq` with this function:

  ```python
  def _ratio_sequence(out: dict, key: str) -> list[float | None]:
      raw = out.get(key)
      if not isinstance(raw, (list, tuple)):
          return []

      values: list[float | None] = [
          None if value is None or value == "" else float(value)
          for value in raw
      ]
      last_value_index = next(
          (index for index in range(len(values) - 1, -1, -1) if values[index] is not None),
          None,
      )
      return [] if last_value_index is None else values[:last_value_index + 1]
  ```

  3. Replace the `lines = CashflowLines(...)` construction with:

  ```python
  debt_service_coverage = DebtServiceCoverage(
      cashflow_ratio=_ratio_sequence(api_output, "cashflow_debt_service_coverage_ratio"),
  )
  ```

  4. Replace the `AdvancedResult` argument in the return statement with:

  ```python
  advanced=AdvancedResult(
      donut=donut,
      debt_service_coverage=debt_service_coverage,
  ),
  ```

- [ ] **Step 5: Serialize the new report payload structure**

  In `agent-backend/app/modules/calculation/application/result_view.py`:

  1. Change `d, li = adv.donut, adv.lines` to:

     ```python
     d, coverage = adv.donut, adv.debt_service_coverage
     ```

  2. Replace the old `"lines"` dictionary with:

     ```python
     "debtServiceCoverage": {
         "cashflowRatio": coverage.cashflow_ratio,
     },
     ```

- [ ] **Step 6: Run the mapper tests and affected import checks**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/unit/calculation/test_output_mapper.py tests/unit/test_architecture_layout.py -q
  ```

  Expected: PASS. The coverage sequence retains `0.0`, retains the middle `None`, casts numeric strings, and removes only trailing blanks.

- [ ] **Step 7: Review the task deliverable without git operations**

  Confirm all of the following by reading the changed files:

  ```text
  result.py contains no CashflowLines class.
  output_mapper.py contains no old four cashflow parameter ids.
  result_view.py contains advanced.debtServiceCoverage.cashflowRatio and no advanced.lines.
  ```

  Do not run `git add` or `git commit`.

## Task 2: Move the Feishu output contract to “画图数据”

**Files:**
- Modify: `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json:101-104`
- Modify: `agent-backend/app/modules/calculation/infrastructure/feishu_sample.py:7-38`
- Modify: `agent-backend/tests/integration/calculation/test_feishu_http_client.py:24-36,43,120-133`
- Modify: `agent-backend/tests/integration/calculation/test_calculation_service.py:17-24`

**Interfaces:**
- Consumes: new `ParamSpec` id `cashflow_debt_service_coverage_ratio` and `api_cell="画图数据!C3:Q3"`.
- Produces: `HttpFeishuGateway.read_output()` result `{"cashflow_debt_service_coverage_ratio": list}`; the gateway must resolve the Chinese Sheet title through the same title-to-sheet-id map used for `API_OUTPUT`.

- [ ] **Step 1: Add failing dictionary and HTTP gateway tests**

  In `agent-backend/tests/integration/calculation/test_feishu_http_client.py`, replace the old `main_business_cost` output parameter in `_param_dict()` with:

  ```python
  {
      "id": "cashflow_debt_service_coverage_ratio",
      "cn": "现金流口径下偿债倍数(贷款期序列)",
      "source": "output",
      "direction": "output",
      "api_cell": "画图数据!C3:Q3",
  },
  ```

  Add the new read interface to `FakeFeishu.__init__`:

  ```python
  self.sheets = {
      "API_INPUT": "shtI",
      "API_OUTPUT": "shtO",
      "API_META": "shtM",
      "画图数据": "shtChart",
  }
  ```

  Update `test_read_output_maps_cells_to_param_ids()` to set the third mocked range to a 15-cell-like row that includes a blank:

  ```python
  fake = FakeFeishu(get_values=[[[8.5]], [[8600]], [[1.1, 0, None, 1.3]]])
  ```

  Assert:

  ```python
  assert out == {
      "project_irr": 8.5,
      "first_year_total_revenue": 8600,
      "cashflow_debt_service_coverage_ratio": [1.1, 0, None, 1.3],
  }
  assert "shtChart!C3:Q3" in fake.get_params["ranges"]
  ```

  In `agent-backend/tests/integration/calculation/test_calculation_service.py`, replace the old length assertion with:

  ```python
  assert r.advanced.debt_service_coverage.cashflow_ratio == SAMPLE_API_OUTPUT[
      "cashflow_debt_service_coverage_ratio"
  ]
  ```

- [ ] **Step 2: Run targeted tests to verify the old dictionary and sample fail**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/integration/calculation/test_feishu_http_client.py tests/integration/calculation/test_calculation_service.py -q
  ```

  Expected: FAIL because the real parameter dictionary and sample output do not expose `cashflow_debt_service_coverage_ratio` yet.

- [ ] **Step 3: Replace the four old parameter dictionary entries**

  In `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json`, remove the four entries with ids:

  ```text
  main_business_cost
  current_principal_interest
  capital_net_cashflow
  total_invest_net_cashflow_after_tax
  ```

  Insert the exact entry below at the same output section location:

  ```json
  { "id": "cashflow_debt_service_coverage_ratio", "cn": "现金流口径下偿债倍数(贷款期序列)", "category": "输出-偿债能力(折线图)", "source": "output", "model_cell": "画图数据!C3:Q3", "f": 1, "g": 0, "writable": false, "direction": "output", "api_cell": "画图数据!C3:Q3", "default": null, "unit": "倍", "dtype": "float[]" }
  ```

  Keep the JSON array valid and do not change unrelated parameter definitions.

- [ ] **Step 4: Replace the mock output data**

  In `agent-backend/app/modules/calculation/infrastructure/feishu_sample.py`:

  1. Update the module comments to describe a loan-period debt-service-coverage sequence, not four 15-year cashflow sequences.
  2. Remove the four old keys from `SAMPLE_API_OUTPUT`.
  3. Add one explicit sample that proves `0` and a middle break are retained:

     ```python
     "cashflow_debt_service_coverage_ratio": [1.12, 1.24, 0.0, None, 1.36, 1.48],
     ```

  Do not retain `_YEARS` or `_ramp` if nothing else in this file uses them.

- [ ] **Step 5: Run targeted gateway and service tests**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/integration/calculation/test_feishu_http_client.py tests/integration/calculation/test_calculation_service.py tests/unit/calculation/test_param_dictionary.py -q
  ```

  Expected: PASS. The gateway reads the `画图数据` Sheet title, returns its flattened row under the new id, and the service maps the sample result to the new DTO.

- [ ] **Step 6: Review the task deliverable without git operations**

  Confirm:

  ```text
  param_dict.json has exactly one output row for cashflow_debt_service_coverage_ratio.
  Its api_cell is exactly 画图数据!C3:Q3.
  No four old cashflow output ids remain in the parameter dictionary or sample output.
  ```

  Do not run `git add` or `git commit`.

## Task 3: Update snapshot and result API regression coverage

**Files:**
- Modify: `agent-backend/tests/db/test_snapshot_service.py:83-96`
- Modify: `agent-backend/tests/db/test_calc_task_api.py:48-54`
- Modify: `agent-backend/tests/e2e/calculation/test_calc_endpoints.py:124-135`

**Interfaces:**
- Consumes: report payload `advanced.debtServiceCoverage.cashflowRatio` generated in Task 1 and mock output generated in Task 2.
- Produces: regression coverage proving snapshots and task result APIs return the new frontend-ready contract rather than the removed `advanced.lines` contract.

- [ ] **Step 1: Replace old backend API/snapshot assertions with failing new-contract assertions**

  In `agent-backend/tests/db/test_snapshot_service.py`, replace the old main-business-cost length assertion with:

  ```python
  assert p["advanced"]["debtServiceCoverage"]["cashflowRatio"] == SAMPLE_API_OUTPUT[
      "cashflow_debt_service_coverage_ratio"
  ]
  ```

  In `agent-backend/tests/db/test_calc_task_api.py`, replace the result assertion with:

  ```python
  assert rep["advanced"]["debtServiceCoverage"]["cashflowRatio"] == [
      1.12, 1.24, 0.0, None, 1.36, 1.48,
  ]
  ```

  In `agent-backend/tests/e2e/calculation/test_calc_endpoints.py`, replace the old `mainBusinessCost` length assertion with the same list assertion against `data["advanced"]["debtServiceCoverage"]["cashflowRatio"]`.

- [ ] **Step 2: Run the three regression targets**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/db/test_snapshot_service.py tests/db/test_calc_task_api.py tests/e2e/calculation/test_calc_endpoints.py -q
  ```

  Expected: PASS after Tasks 1 and 2. If a database integration test cannot connect to the configured test database, report that environment blockage exactly and still run the E2E target separately.

- [ ] **Step 3: Check contract removal explicitly**

  Run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/unit/calculation/test_output_mapper.py tests/integration/calculation/test_calculation_service.py tests/e2e/calculation/test_calc_endpoints.py -q
  ```

  Expected: PASS. Confirm no assertion in the changed test files references `advanced.lines` or `mainBusinessCost`.

- [ ] **Step 4: Review the task deliverable without git operations**

  Confirm that a persisted report snapshot contains `advanced.debtServiceCoverage.cashflowRatio`, and the task-result endpoint returns this stored payload without re-reading flybook data.

  Do not run `git add` or `git commit`.

## Task 4: Replace the frontend chart component and its contract test

**Files:**
- Delete: `agent-frontend/src/views/home/components/CashflowLines.vue`
- Create: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
- Modify: `agent-frontend/src/views/home/components/ResultCard.vue:21-22,55-62,75`
- Modify: `agent-frontend/tests/charts.spec.js`

**Interfaces:**
- Consumes: `coverage` prop shaped as `{ cashflowRatio?: Array<number | null> }` from `result.advanced.debtServiceCoverage`.
- Produces: an ECharts option with one green line series named `现金流口径下偿债倍数`, a category X axis titled `贷款年限`, a value Y axis titled `偿债倍数`, and a red dashed `markLine` at y=1.

- [ ] **Step 1: Replace the existing chart test with failing debt-service-coverage expectations**

  In `agent-frontend/tests/charts.spec.js`:

  1. Replace the import:

     ```js
     import CashflowLines from '@/views/home/components/CashflowLines.vue'
     ```

     with:

     ```js
     import DebtServiceCoverage from '@/views/home/components/DebtServiceCoverage.vue'
     ```

  2. Replace `builds four 15-year cashflow series` with:

     ```js
     it('builds a debt-service-coverage line with a threshold and a middle break', () => {
       mount(DebtServiceCoverage, {
         props: {
           coverage: { cashflowRatio: [1.12, 0, null, 1.36] },
         },
       })
       const option = captured.factories[0]()

       expect(option.series).toHaveLength(1)
       expect(option.series[0]).toMatchObject({
         name: '现金流口径下偿债倍数',
         type: 'line',
         data: [1.12, 0, null, 1.36],
         connectNulls: false,
         color: '#22c55e',
       })
       expect(option.xAxis.name).toBe('贷款年限')
       expect(option.xAxis.data).toEqual(['第1年', '第2年', '第3年', '第4年'])
       expect(option.yAxis.name).toBe('偿债倍数')
       expect(option.series[0].markLine).toMatchObject({
         symbol: 'none',
         lineStyle: { color: '#ef4444', type: 'dashed' },
         data: [{ yAxis: 1 }],
       })
     })
     ```

  3. Add an empty sequence test:

     ```js
     it('does not create a business series for an empty coverage sequence', () => {
       mount(DebtServiceCoverage, { props: { coverage: { cashflowRatio: [] } } })
       const option = captured.factories[0]()

       expect(option.series).toEqual([])
       expect(option.xAxis.data).toEqual([])
     })
     ```

- [ ] **Step 2: Run the frontend chart test to verify it fails**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js
  ```

  Expected: FAIL because `DebtServiceCoverage.vue` does not yet exist and the old chart contract is still mounted by `ResultCard`.

- [ ] **Step 3: Create the replacement ECharts component**

  Create `agent-frontend/src/views/home/components/DebtServiceCoverage.vue` with this implementation:

  ```vue
  <template>
    <div class="ir-chart">
      <div class="ir-chart__head">
        <span class="ir-chart__title">偿债能力｜现金流口径下偿债倍数</span>
      </div>
      <div ref="el" class="ir-chart__canvas" />
    </div>
  </template>

  <script setup>
  import { computed } from 'vue'
  import { formatNumber } from '@/utils/formatNumber'
  import { useEcharts, xcVar } from '../composables/useEcharts'

  const props = defineProps({ coverage: { type: Object, default: () => ({}) } })
  const ratios = computed(() => (
    Array.isArray(props.coverage?.cashflowRatio) ? props.coverage.cashflowRatio : []
  ))

  const buildOption = () => {
    const data = ratios.value
    const xAxis = Array.from({ length: data.length }, (_, index) => `第${index + 1}年`)
    const series = data.length
      ? [{
          name: '现金流口径下偿债倍数',
          type: 'line',
          smooth: true,
          showSymbol: false,
          connectNulls: false,
          color: '#22c55e',
          data,
          markLine: {
            symbol: 'none',
            lineStyle: { color: '#ef4444', type: 'dashed' },
            data: [{ yAxis: 1 }],
          },
        }]
      : []

    return {
      tooltip: { trigger: 'axis' },
      legend: {
        top: 0,
        textStyle: { color: xcVar('--xc-text-soft'), fontSize: 12 },
      },
      grid: { left: 8, right: 16, bottom: 8, top: 36, containLabel: true },
      xAxis: {
        type: 'category',
        name: '贷款年限',
        data: xAxis,
        axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 11 },
        axisLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
      },
      yAxis: {
        type: 'value',
        name: '偿债倍数',
        nameTextStyle: { color: xcVar('--xc-text-mute'), fontSize: 11 },
        axisLabel: {
          color: xcVar('--xc-text-mute'),
          fontSize: 11,
          formatter: (value) => formatNumber(value),
        },
        splitLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
      },
      series,
    }
  }

  const { el } = useEcharts(buildOption)
  </script>

  <style scoped>
  .ir-chart { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: var(--xc-radius-md); background: rgba(255, 255, 255, 0.04); padding: var(--xc-space-5); margin-top: var(--xc-space-4); }
  .ir-chart__head { margin-bottom: var(--xc-space-2); }
  .ir-chart__title { font-size: var(--xc-fs-sm); color: var(--xc-text-strong); }
  .ir-chart__canvas { width: 100%; height: 260px; }
  </style>
  ```

- [ ] **Step 4: Wire the result card to the new report field**

  In `agent-frontend/src/views/home/components/ResultCard.vue`:

  1. Replace the template line:

     ```vue
     <CashflowLines :lines="advanced.lines" />
     ```

     with:

     ```vue
     <DebtServiceCoverage :coverage="advanced.debtServiceCoverage" />
     ```

  2. Replace the import:

     ```js
     import CashflowLines from './CashflowLines.vue'
     ```

     with:

     ```js
     import DebtServiceCoverage from './DebtServiceCoverage.vue'
     ```

  3. Keep the fallback `advanced` object as `{ donut: {}, debtServiceCoverage: {} }`:

     ```js
     const advanced = computed(() => props.result.advanced || { donut: {}, debtServiceCoverage: {} })
     ```

  4. Delete `agent-frontend/src/views/home/components/CashflowLines.vue` only after the new component is imported and the component test passes.

- [ ] **Step 5: Run chart and result-card test targets**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js tests/result-cards.spec.js
  ```

  Expected: PASS. The chart option has one green line, a `null` gap remains unconnected, the X axis follows sequence length, and the red dashed `y=1` mark line is present.

- [ ] **Step 6: Build the frontend**

  From `agent-frontend/`, run:

  ```bash
  pnpm build
  ```

  Expected: exit code 0 and a generated production build. If the build fails due to pre-existing unrelated working-tree changes, report the exact output and do not modify unrelated files.

- [ ] **Step 7: Review the task deliverable without git operations**

  Confirm:

  ```text
  CashflowLines.vue is deleted.
  ResultCard.vue has no advanced.lines reference.
  DebtServiceCoverage.vue is the sole result-card line-chart component.
  The chart uses literal green #22c55e and red #ef4444 as required.
  ```

  Do not run `git add` or `git commit`.

## Task 5: Full focused regression and manual contract verification

**Files:**
- No production code changes expected.
- Verify: all files modified by Tasks 1–4.

**Interfaces:**
- Consumes: completed backend result, Feishu interface, snapshot, API, and frontend chart contracts.
- Produces: evidence that the new graph data travels end-to-end from `画图数据!C3:Q3` configuration to ECharts without any old cashflow contract remaining.

- [ ] **Step 1: Run the complete relevant backend test set**

  From `agent-backend/`, run:

  ```bash
  .venv/Scripts/python.exe -m pytest tests/unit/calculation/test_output_mapper.py tests/unit/calculation/test_param_dictionary.py tests/integration/calculation/test_feishu_http_client.py tests/integration/calculation/test_calculation_service.py tests/e2e/calculation/test_calc_endpoints.py -q
  ```

  Expected: PASS.

- [ ] **Step 2: Run the complete frontend test suite**

  From `agent-frontend/`, run:

  ```bash
  pnpm test
  ```

  Expected: PASS. If pre-existing changes cause failures unrelated to the new chart, record each failing test and its evidence rather than changing unrelated code.

- [ ] **Step 3: Inspect the backend and frontend source for retired contract references**

  Search the production source directories for these retired names:

  ```text
  main_business_cost
  current_principal_interest
  capital_net_cashflow
  total_invest_net_cashflow_after_tax
  advanced.lines
  CashflowLines
  ```

  Expected: no matches under `agent-backend/app/` and `agent-frontend/src/`; test fixtures or historical non-production artifacts should be updated or deliberately excluded only if outside the new graph behavior.

- [ ] **Step 4: Manually validate the data interpretation**

  Using the sample sequence `[1.12, 1.24, 0.0, None, 1.36, 1.48]`, confirm:

  ```text
  report payload: advanced.debtServiceCoverage.cashflowRatio exactly preserves the sequence
  horizontal labels: 第1年 through 第6年
  y-axis label: 偿债倍数
  business line: green
  fourth point: a visible break rather than a connection between year 3 and year 5
  threshold: horizontal red dashed line at y=1
  ```

- [ ] **Step 5: Report completion without git operations**

  Summarize modified/deleted/created files and every command result. Explicitly state whether each backend test group, frontend test suite, and build passed. Do not run `git status`, `git add`, `git commit`, or `git push`.
