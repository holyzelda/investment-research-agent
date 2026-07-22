# 联络线详情紧凑指标布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将联络线详情面板的电压等级并入关键指标区，并压缩功率趋势区域高度，减少图表下方空白。

**Architecture:** 仅调整前端展示层，不改变接口、Store 或后端数据契约。`TieLineDetailPanel.vue` 负责线路档案与指标布局，`TieLinePowerTrend.vue` 负责趋势图高度与状态区域高度；测试分别覆盖布局语义和样式约束。

**Tech Stack:** Vue 3、Vitest、@vue/test-utils、ECharts 5、XC CSS token。

---

### Task 1: 调整详情面板关键指标布局

**Files:**
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`

- [ ] **Step 1: Write the failing test**

在 `agent-frontend/tests/tie-line-detail-panel.spec.js` 的首个用例中，将标题改为“以线路名片、微型线路图和两列关键指标展示线路档案”，并断言：

```js
expect(wrapper.find('.tl-profile__voltage').exists()).toBe(false)
expect(wrapper.findAll('.tl-metric-strip__item')).toHaveLength(4)
expect(wrapper.text()).toContain('电压等级')
expect(wrapper.text()).toContain('±800 kV')
expect(styles).toContain('grid-template-columns:repeat(2, minmax(0, 1fr))')
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:/c/Users/Administrator/AppData/Roaming/npm:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

Expected: FAIL，原因包含仍存在 `.tl-profile__voltage` 或指标项数量不是 4。

- [ ] **Step 3: Write minimal implementation**

在 `TieLineDetailPanel.vue` 中：

```vue
<!-- 删除 header 右侧的电压 badge -->
<!-- <span class="tl-profile__voltage">...</span> -->

<dl class="tl-metric-strip" aria-label="线路关键指标">
  <div class="tl-metric-strip__item"><dt>额定容量</dt><dd class="xc-num">{{ capText }}</dd></div>
  <div class="tl-metric-strip__item"><dt>电压等级</dt><dd class="xc-num">{{ displayLine.voltageText || '—' }}</dd></div>
  <div class="tl-metric-strip__item"><dt>线路长度</dt><dd class="xc-num">{{ displayLine.lengthText || '—' }}</dd></div>
  <div class="tl-metric-strip__item"><dt>投运年份</dt><dd class="xc-num">{{ displayLine.operationYear || '—' }}</dd></div>
</dl>
```

将样式改为两列紧凑卡片：

```css
.tl-metric-strip { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:var(--xc-space-3); margin:var(--xc-space-4) 0 0; }
.tl-metric-strip__item { min-width:0; padding:var(--xc-space-3); background:var(--xc-surface-tinted); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-sm); }
.tl-metric-strip__item + .tl-metric-strip__item::before { display:none; }
```

- [ ] **Step 4: Run test to verify it passes**

Run the same Vitest command. Expected: PASS。

### Task 2: 压缩功率趋势区域高度

**Files:**
- Modify: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Modify: `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`

- [ ] **Step 1: Write the failing test**

在 `agent-frontend/tests/tie-line-power-trend.spec.js` 中新增样式断言：

```js
it('使用更紧凑的图表高度，减少趋势图下方空白', () => {
  expect(styles).toContain('height: 188px')
  expect(styles).toContain('min-height: 188px')
  expect(styles).toContain('height: 128px')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:/c/Users/Administrator/AppData/Roaming/npm:$PATH"
pnpm vitest run tests/tie-line-power-trend.spec.js
```

Expected: FAIL，原因包含找不到 `height: 188px`。

- [ ] **Step 3: Write minimal implementation**

在 `TieLinePowerTrend.vue` 中修改：

```css
.tl-power-trend { margin-top: var(--xc-space-4); padding-top: var(--xc-space-3); border-top: 1px solid var(--xc-border-soft); }
.tl-power-trend__ranges { ... margin-top: var(--xc-space-2); }
.tl-power-trend__canvas { width: 100%; height: 188px; margin-top: var(--xc-space-2); }
.tl-power-trend__skeleton, .tl-power-trend__state { min-height: 188px; ... }
.tl-power-trend__skeleton .xc-skeleton { width: 100%; height: 128px; }
```

- [ ] **Step 4: Run test to verify it passes**

Run the same Vitest command. Expected: PASS。

### Task 3: 回归验证

**Files:**
- Test: `agent-frontend/tests/tie-line-detail-panel.spec.js`
- Test: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Test: `agent-frontend/tests/use-echarts.spec.js`

- [ ] **Step 1: Run focused regression**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:/c/Users/Administrator/AppData/Roaming/npm:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js tests/tie-line-power-trend.spec.js tests/use-echarts.spec.js
```

Expected: PASS。

- [ ] **Step 2: Check git diff**

```bash
git diff -- agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue agent-frontend/tests/tie-line-detail-panel.spec.js agent-frontend/tests/tie-line-power-trend.spec.js
```

Expected: 只包含详情面板指标布局、趋势图高度和对应测试改动；不包含接口、Store、后端或 Git 写操作。

---

## Self Review

- Spec coverage: 覆盖电压移入指标区、指标区两列、间距调整、功率图下方空白压缩。
- Placeholder scan: 无 TBD/TODO/占位项。
- Type consistency: 使用现有字段 `voltageText`、`ratedCapacityMw`、`lengthText`、`operationYear`，不新增数据契约。
