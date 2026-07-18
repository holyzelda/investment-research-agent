# 偿债倍数图对齐分区 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用玄策品牌蓝作为偿债倍数业务线，并以完整对齐的蓝色安全区和红色风险区替换错误的绿色面积填充。

**Architecture:** 保持现有 ECharts 单序列、警戒线、数据点、tooltip 和数据契约。删除 series 级 `areaStyle`，通过同一个 `markArea` 声明 `0–1` 风险区与 `1–max` 安全区，消除两侧不对齐及低于阈值仍显示安全面积的问题。

**Tech Stack:** Vue 3、ECharts、Vitest、Vue Test Utils、玄策 CSS tokens。

## Global Constraints

- 只修改 `agent-frontend/src/views/home/components/DebtServiceCoverage.vue` 和 `agent-frontend/tests/charts.spec.js`。
- 不修改 `coverage.cashflowRatio`、后端、飞书、快照或报告载荷。
- 主线/点必须使用 `--xc-accent-blue`；不使用 `--xc-status-ok`。
- 删除 series `areaStyle`；业务值低于 1 时不得出现安全余量面积。
- `markArea` 必须同时定义 `0–1` 红色风险区和 `1–max` 蓝色安全区；两个分区共用绘图区，左右严格对齐。
- `y=1` 保留 `--xc-status-danger` 红色虚线与“警戒线 1.0”标签。
- 保留 `0` 为有效值、`null` 断点、circle 数据点和 tooltip；不添加常驻数值标签。
- 不新增依赖，不执行 git 操作。

---

### Task 1: Replace unsafe area fill with aligned XuanCe zones

**Files:**
- Modify: `agent-frontend/src/views/home/components/DebtServiceCoverage.vue`
- Modify: `agent-frontend/tests/charts.spec.js`

**Interfaces:**
- Consumes: unchanged `{ cashflowRatio?: Array<number | null> }` coverage prop.
- Produces: a brand-blue line series with no series-level area fill, and a `markArea` configuration containing two full-width vertical-value zones.

- [ ] **Step 1: Write failing zone and color assertions**

  In the debt-service chart test, replace the existing `areaStyle` assertion:

  ```js
  areaStyle: { origin: 1 },
  ```

  with:

  ```js
  color: '#888',
  itemStyle: { color: '#888', borderWidth: 2 },
  ```

  The test mock returns `'#888'` from `xcVar`, so this proves component colors are token-derived. Add:

  ```js
  expect(option.series[0].areaStyle).toBeUndefined()
  expect(option.series[0].markArea).toMatchObject({
    silent: true,
    data: [
      [{ yAxis: 0 }, { yAxis: 1 }],
      [{ yAxis: 1 }, { yAxis: 'max' }],
    ],
  })
  ```

  Keep all existing assertions for the red dashed `markLine`, `null` break, circle points, and tooltip.

- [ ] **Step 2: Run the focused chart test and verify RED**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js
  ```

  Expected: FAIL because the current line still has `areaStyle`, uses `--xc-status-ok`, and defines only one `markArea` range.

- [ ] **Step 3: Replace the green semantic token with the brand-blue token**

  In `DebtServiceCoverage.vue`, replace:

  ```js
  const success = xcVar('--xc-status-ok')
  const successSoft = xcVar('--xc-status-ok-soft')
  ```

  with:

  ```js
  const accent = xcVar('--xc-accent-blue')
  const accentSoft = xcVar('--xc-accent-blue-soft')
  ```

  In the line series, replace `color: success` and `itemStyle.color: success` with `accent`.

- [ ] **Step 4: Remove the series-level safety fill and define both aligned background zones**

  Delete this series property completely:

  ```js
  areaStyle: { color: successSoft, origin: 1 },
  ```

  Replace the `markArea` object with:

  ```js
  markArea: {
    silent: true,
    data: [
      [
        { yAxis: 0, itemStyle: { color: dangerSoft } },
        { yAxis: 1 },
      ],
      [
        { yAxis: 1, itemStyle: { color: accentSoft } },
        { yAxis: 'max' },
      ],
    ],
  },
  ```

  Keep `markLine` unchanged. The two `markArea` ranges must remain in this order so their common `y=1` boundary exactly matches the threshold.

- [ ] **Step 5: Run tests and build**

  From `agent-frontend/`, run:

  ```bash
  pnpm vitest run tests/charts.spec.js tests/result-cards.spec.js
  pnpm build
  ```

  Expected: all focused tests pass and build exits 0. Existing Vue mock warnings or dependency chunk-size warnings may be reported but must not be changed as part of this task.

- [ ] **Step 6: Source-level visual contract inspection**

  Confirm in `DebtServiceCoverage.vue`:

  ```text
  --xc-accent-blue is the only main line/data-point semantic token.
  No --xc-status-ok token and no areaStyle property remain.
  markArea has exactly two data ranges: 0–1 and 1–max.
  The red threshold label and tooltip behavior remain present.
  ```

  Do not run git commands.
