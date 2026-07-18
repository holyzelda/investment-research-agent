# 偿债倍数图安全余量面积 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将蓝色区域改为仅在偿债倍数超过警戒线时出现的安全余量面积，并使首末年份贴合绘图区左右边缘。

**Architecture:** 保持品牌蓝主折线的真实映射数据，增加静默面积辅助 series。辅助 series 在低于或等于警戒线时钳制到显示坐标 2，在超过警戒线时使用显示值，并以 `areaStyle.origin=2` 填充；红色风险区仍用单一 `markArea` 覆盖 0–2。

**Tech Stack:** Vue 3、ECharts、Vitest、Vue Test Utils。

## Global Constraints

- 只修改 `agent-frontend/src/views/home/components/DebtServiceCoverage.vue` 与 `agent-frontend/tests/charts.spec.js`。
- 不改数据契约、分段显示轴、tooltip 真实值、品牌蓝主线和警戒线。
- X 轴必须 `boundaryGap: false`。
- 蓝色安全面积只出现于真实值 `>1`；真实值 `<=1` 时不能有蓝色面积。
- 辅助面积 series 不得显示线、symbol、legend 或 tooltip。
- 红色风险区必须是唯一 `markArea`，显示坐标范围 `0–2`。
- 不新增依赖，不执行 git 操作。

---

### Task 1: Add the conditional safety-margin area series

**Files:**
- Modify: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
- Modify: `agent-frontend/tests/charts.spec.js`

**Interfaces:**
- Consumes: original `data` (`Array<number | null>`) and existing `displayData`.
- Produces: `series[0]` as visible main line and `series[1]` as silent blue safety-margin area.

- [ ] **Step 1: Write failing auxiliary-series assertions**

  In the debt-service chart test, replace `expect(option.series).toHaveLength(1)` with:

  ```js
  expect(option.series).toHaveLength(2)
  expect(option.xAxis.boundaryGap).toBe(false)
  expect(option.series[1]).toMatchObject({
    type: 'line',
    data: [2.6, 2, null, 3.8],
    showSymbol: false,
    lineStyle: { opacity: 0 },
    areaStyle: { origin: 2 },
    tooltip: { show: false },
    silent: true,
  })
  expect(option.series[0].markArea).toMatchObject({
    data: [[{ yAxis: 0 }, { yAxis: 2 }]],
  })
  ```

  Keep the main-series assertions and remove the old expectation that `markArea` has a blue `2–max` range.

- [ ] **Step 2: Run chart test and verify RED**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js
  ```

  Expected: FAIL because there is one series, the category axis still has its default boundary gap, and markArea contains two ranges.

- [ ] **Step 3: Add conditional area data**

  Inside `buildOption`, after `displayData`, add:

  ```js
  const safetyAreaData = data.map((value, index) => {
    if (value === null) return null
    return Math.max(2, displayData[index])
  })
  ```

  This preserves null gaps, holds values `<=1` at the baseline 2, and retains display coordinates above 2 for values `>1`.

- [ ] **Step 4: Replace the two background zones with red risk-only markArea**

  Replace markArea with:

  ```js
  markArea: {
    silent: true,
    data: [[
      { yAxis: 0, itemStyle: { color: dangerSoft } },
      { yAxis: 2 },
    ]],
  },
  ```

  Delete the `accentSoft` constant because it will move to the auxiliary area series.

- [ ] **Step 5: Add the silent area series**

  Replace `series,` in the option with:

  ```js
  series: [
    ...series,
    ...(data.length ? [{
      type: 'line',
      data: safetyAreaData,
      showSymbol: false,
      lineStyle: { opacity: 0 },
      areaStyle: { color: xcVar('--xc-accent-blue-soft'), origin: 2 },
      tooltip: { show: false },
      silent: true,
      z: 0,
    }] : []),
  ],
  ```

  The main series remains first, so it stays above the fill and remains the only tooltip/legend item.

- [ ] **Step 6: Make category endpoints flush with the plot boundary**

  In the X-axis configuration, add:

  ```js
  boundaryGap: false,
  ```

  Leave category labels unchanged.

- [ ] **Step 7: Run focused tests and build**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js tests/result-cards.spec.js
  pnpm build
  ```

  Expected: tests pass and build exits 0.

- [ ] **Step 8: Inspect final visual contract**

  Confirm the auxiliary series only fills above display coordinate 2, red markArea only covers 0–2, main line remains first, and X-axis `boundaryGap` is false. Do not run git commands.
