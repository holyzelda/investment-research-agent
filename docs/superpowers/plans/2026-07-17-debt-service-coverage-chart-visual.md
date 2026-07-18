# 偿债倍数图玄策化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前玄策深色主题中，为偿债倍数图增加风险区、警戒线、安全余量面积、数据点与悬浮提示。

**Architecture:** 保持现有 `coverage.cashflowRatio` 数据契约不变，仅调整 ECharts option 和对应 Vitest 断言。所有颜色从现有玄策 CSS token 读取，避免复用参考报告的白底和固定色值；`markArea` 表达风险区、`markLine` 表达警戒线、series area 表达相对阈值的安全余量。

**Tech Stack:** Vue 3、ECharts、Vitest、Vue Test Utils、玄策 CSS tokens。

## Global Constraints

- 只修改 `agent-frontend/src/views/home/components/DebtServiceCoverage.vue` 与 `agent-frontend/tests/charts.spec.js`。
- 不修改后端、飞书读取、快照、报告载荷或 `coverage.cashflowRatio` 数据契约。
- 保留 `0` 为有效值、`null` 为断点，必须 `connectNulls: false`。
- 不显示首年、末年或其他常驻数值标签；仅 tooltip 在 hover 时显示年份和偿债倍数。
- 所有界面和语义色使用玄策 token；不得复刻参考报告的白底、海军蓝或固定青绿色。
- `y < 1` 是淡红风险区；`y=1` 是红色虚线并显示“警戒线 1.0”；折线与警戒线之间显示低透明绿色安全余量面积。
- 不新增依赖，不执行 `git add`、`git commit`、`git push` 或任何 git 写操作。

---

## File Structure

- Modify: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
  - 从 `xcVar()` 获取玄策语义色，配置折线点、阈值、风险区、面积、安全 tooltip 和坐标视觉。
- Modify: `agent-frontend/tests/charts.spec.js`
  - 断言新版 ECharts option 的 token 色、风险区、阈值、数据点、断点与 tooltip。

### Task 1: Implement the XuanCe debt-service-coverage visual treatment

**Files:**
- Modify: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
- Modify: `agent-frontend/tests/charts.spec.js`

**Interfaces:**
- Consumes: `coverage` prop `{ cashflowRatio?: Array<number | null> }`.
- Produces: a single ECharts line series named `现金流口径下偿债倍数`, with `connectNulls: false`, X axis labels `第N年`, and a tooltip that reports the hovered year and ratio in `倍`.

- [ ] **Step 1: Write failing visual-contract assertions**

  Replace the current debt-service test assertion in `agent-frontend/tests/charts.spec.js` with the following additional checks after `const option = captured.factories[0]()`:

  ```js
  expect(option.series[0]).toMatchObject({
    showSymbol: true,
    symbol: 'circle',
    symbolSize: 8,
    connectNulls: false,
    lineStyle: { width: 2 },
    itemStyle: { borderWidth: 2 },
    areaStyle: { origin: 1 },
  })
  expect(option.series[0].markLine).toMatchObject({
    symbol: 'none',
    lineStyle: { type: 'dashed', width: 1.5 },
    label: { show: true, formatter: '警戒线 1.0', position: 'insideEndTop' },
    data: [{ yAxis: 1 }],
  })
  expect(option.series[0].markArea).toMatchObject({
    silent: true,
    data: [[{ yAxis: 0 }, { yAxis: 1 }]],
  })
  expect(option.tooltip.axisPointer).toEqual({ type: 'cross' })
  expect(option.tooltip.formatter([{ axisValue: '第2年', value: 0 }])).toContain('第2年')
  expect(option.tooltip.formatter([{ axisValue: '第2年', value: 0 }])).toContain('0.00 倍')
  ```

  Retain the existing assertions that confirm `data: [1.12, 0, null, 1.36]`, green series identity, and `connectNulls: false`.

- [ ] **Step 2: Run the chart test and verify RED**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js
  ```

  Expected: FAIL because the current series has `showSymbol: false`, lacks `areaStyle`, `markArea`, detailed `markLine.label`, axis crosshair, and the formatter.

- [ ] **Step 3: Add token-derived chart colors and tooltip formatting**

  In `DebtServiceCoverage.vue`, keep `xcVar` imported and add these local constants above `buildOption`:

  ```js
  const success = xcVar('--xc-status-ok')
  const successSoft = xcVar('--xc-status-ok-soft')
  const danger = xcVar('--xc-status-danger')
  const dangerSoft = xcVar('--xc-status-danger-soft')
  const surface = xcVar('--xc-surface-raised')
  ```

  Inside `buildOption`, add a formatter function:

  ```js
  const tooltipFormatter = (params) => {
    const point = params.find((item) => item.value !== null && item.value !== undefined)
    if (!point) return ''
    return `${point.axisValue}<br/>偿债倍数：${formatNumber(point.value)} 倍`
  }
  ```

  Replace the tooltip declaration with:

  ```js
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
    formatter: tooltipFormatter,
  },
  ```

- [ ] **Step 4: Add points, risk area, threshold label, and safety-margin fill**

  Replace the current non-empty `series` object with:

  ```js
  {
    name: '现金流口径下偿债倍数',
    type: 'line',
    smooth: true,
    showSymbol: true,
    symbol: 'circle',
    symbolSize: 8,
    connectNulls: false,
    color: success,
    lineStyle: { width: 2 },
    itemStyle: { color: success, borderColor: surface, borderWidth: 2 },
    areaStyle: { color: successSoft, origin: 1 },
    data,
    markLine: {
      symbol: 'none',
      lineStyle: { color: danger, type: 'dashed', width: 1.5 },
      label: {
        show: true,
        formatter: '警戒线 1.0',
        position: 'insideEndTop',
        color: danger,
        fontSize: 11,
      },
      data: [{ yAxis: 1 }],
    },
    markArea: {
      silent: true,
      itemStyle: { color: dangerSoft },
      data: [[{ yAxis: 0 }, { yAxis: 1 }]],
    },
  }
  ```

  Keep the existing dynamic X-axis and empty-series behavior. Do not add data labels.

- [ ] **Step 5: Tune axes for the existing dark XuanCe surface**

  Retain `xcVar('--xc-text-mute')` for axis labels and `xcVar('--xc-border-soft')` for grid and axis lines. Add these axis-label settings:

  ```js
  xAxis: {
    ...,
    axisTick: { show: false },
  },
  yAxis: {
    ...,
    min: 0,
    splitNumber: 4,
    axisTick: { show: false },
  },
  ```

  Do not set hard-coded palette colors anywhere in the component.

- [ ] **Step 6: Run focused tests and verify GREEN**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js tests/result-cards.spec.js
  ```

  Expected: PASS. The line retains its `null` break and zero, has 8px circle points, a token-driven risk region, a labeled token-driven `y=1` threshold, and tooltip-based values only.

- [ ] **Step 7: Run production build**

  From `agent-frontend/`, run:

  ```bash
  pnpm build
  ```

  Expected: exit code 0. Report dependency warnings separately if emitted; do not alter unrelated code.

- [ ] **Step 8: Inspect final source and report without git operations**

  Confirm:

  ```text
  No hard-coded report-reference colors appear in DebtServiceCoverage.vue.
  showSymbol is true and data labels are absent.
  markArea covers y=0 through y=1.
  markLine uses y=1 and “警戒线 1.0”.
  Tooltip is the only value-display path.
  ```

  Do not run git commands.
