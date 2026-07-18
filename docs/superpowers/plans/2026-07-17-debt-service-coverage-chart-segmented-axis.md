# 偿债倍数图分段刻度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以等高网格展示 `0–1` 每 0.5 倍、`>1` 每 0.2 倍的偿债倍数分段刻度轴。

**Architecture:** 组件内部把真实偿债倍数映射为 ECharts 显示坐标，Y 轴标签和 tooltip 反向显示真实值。数据契约不变；警戒线和红蓝背景区改用显示坐标 `2`，对应真实值 `1.0`。

**Tech Stack:** Vue 3、ECharts、Vitest、Vue Test Utils。

## Global Constraints

- 只修改 `agent-frontend/src/views/home/components/DebtServiceCoverage.vue` 和 `agent-frontend/tests/charts.spec.js`。
- 真实数据、tooltip 和 `coverage.cashflowRatio` 契约不变。
- `0–1` 每 0.5 倍为一个等高网格；`>1` 每 0.2 倍为一个等高网格。
- `null` 保持断点，`0` 保持有效点。
- 警戒线、红色风险区和蓝色安全区边界必须位于显示坐标 `2`。
- 保持品牌蓝主线、红色警戒线与无常驻数据标签。
- 不新增依赖，不执行 git 操作。

---

### Task 1: Implement the segmented display axis

**Files:**
- Modify: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
- Modify: `agent-frontend/tests/charts.spec.js`

**Interfaces:**
- Consumes: real ratio series `Array<number | null>`.
- Produces: mapped ECharts series data, but tooltip text always uses real ratio values.

- [ ] **Step 1: Add failing segmented-axis assertions**

  In `tests/charts.spec.js`, use the existing input `[1.12, 0, null, 1.36]` and assert:

  ```js
  expect(option.series[0].data).toEqual([2.6, 0, null, 3.8])
  expect(option.yAxis.interval).toBe(1)
  expect(option.yAxis.axisLabel.formatter(0)).toBe('0.0')
  expect(option.yAxis.axisLabel.formatter(1)).toBe('0.5')
  expect(option.yAxis.axisLabel.formatter(2)).toBe('1.0')
  expect(option.yAxis.axisLabel.formatter(3)).toBe('1.2')
  expect(option.yAxis.axisLabel.formatter(4)).toBe('1.4')
  expect(option.series[0].markLine.data).toEqual([{ yAxis: 2 }])
  expect(option.series[0].markArea.data).toEqual([
    [{ yAxis: 0 }, { yAxis: 2 }],
    [{ yAxis: 2 }, { yAxis: 'max' }],
  ])
  expect(option.tooltip.formatter([{ axisValue: '第1年', dataIndex: 0 }])).toContain('1.12 倍')
  ```

- [ ] **Step 2: Run the chart test and verify RED**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js
  ```

  Expected: FAIL because current series and threshold use real linear values and no mapping helpers exist.

- [ ] **Step 3: Add real-value mapping helpers**

  Above `buildOption` in `DebtServiceCoverage.vue`, add:

  ```js
  const toDisplayValue = (value) => (value <= 1 ? value / 0.5 : 2 + (value - 1) / 0.2)
  const toRatioValue = (value) => (value <= 2 ? value * 0.5 : 1 + (value - 2) * 0.2)
  ```

  Inside `buildOption`, derive mapped series data and display maximum:

  ```js
  const displayData = data.map((value) => (value === null ? null : toDisplayValue(value)))
  const maxRatio = Math.max(1, ...data.filter((value) => value !== null))
  const displayMax = Math.max(2, Math.ceil((maxRatio - 1) / 0.2) + 2)
  ```

- [ ] **Step 4: Use mapped coordinates while preserving true tooltip values**

  Change series `data` to `displayData`. Replace tooltip formatter with:

  ```js
  const tooltipFormatter = (params) => {
    const point = params.find((item) => data[item.dataIndex] !== null)
    if (!point) return ''
    return `${point.axisValue}<br/>偿债倍数：${formatNumber(data[point.dataIndex])} 倍`
  }
  ```

  Change `markLine.data` to `[{ yAxis: 2 }]` and `markArea.data` to:

  ```js
  [
    [{ yAxis: 0, itemStyle: { color: dangerSoft } }, { yAxis: 2 }],
    [{ yAxis: 2, itemStyle: { color: accentSoft } }, { yAxis: 'max' }],
  ]
  ```

- [ ] **Step 5: Configure the mapped Y axis**

  Replace the Y-axis value configuration with these additions:

  ```js
  min: 0,
  max: displayMax,
  interval: 1,
  splitNumber: undefined,
  axisLabel: {
    color: xcVar('--xc-text-mute'),
    fontSize: 11,
    formatter: (value) => toRatioValue(value).toFixed(1),
  },
  ```

  Keep the existing name, grid, border, and tick settings.

- [ ] **Step 6: Run focused tests and production build**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js tests/result-cards.spec.js
  pnpm build
  ```

  Expected: all tests pass and build exits 0.

- [ ] **Step 7: Inspect the display contract**

  Confirm source uses `2` exclusively as the mapped location of true `1.0`, tooltip reads original data, and no real value is lost before formatting. Do not run git commands.
