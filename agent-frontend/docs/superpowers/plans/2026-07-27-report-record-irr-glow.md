# 报告记录 IRR 同款发光 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除报告记录定位时的上浮动画，复用核心 IRR 指标的 XC 蓝色发光效果。

**Architecture:** 保持现有 `ir-report-list__item--highlighted` 的响应式状态和 1.6 秒自动清除逻辑，只替换其 CSS 外观，避免改变定位数据流或组件接口。

**Tech Stack:** Vue 3、Vitest、CSS、XC design tokens。

## Global Constraints

- 不新增依赖、不修改 Store、路由或定位逻辑。
- 高亮使用 `inset 0 1px 0 var(--xc-border-card), var(--xc-glow-blue)`，与 `FinancialBlock.vue` 的项目全投资 IRR 相同。
- 删除上浮 keyframes 与动画属性；禁止 hardcode 色值。
- 不执行 Git 写操作。

---

## File Structure

- Modify: `src/views/home/index.vue` — 将报告卡片高亮从动画阴影改为 IRR 同款静态 glow。
- Verify: `tests/home-records-sidebar.spec.js` — 目标高亮类仍由定位行为正确施加。

### Task 1: 替换报告卡片定位高亮

**Files:**
- Modify: `src/views/home/index.vue:500-515`
- Verify: `tests/home-records-sidebar.spec.js`

**Interfaces:**
- Consumes: `ir-report-list__item--highlighted` 高亮类。
- Produces: 无位移动画、使用 `--xc-glow-blue` 的静态定位高亮。

- [ ] **Step 1: 运行既有定位测试确认基线**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: PASS，现有测试证明点击跳转按钮会给目标卡片加 `ir-report-list__item--highlighted`。

- [ ] **Step 2: 实施最小样式替换**

在 `index.vue` 中将：

```css
.ir-report-list__item--highlighted {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
  box-shadow: 0 0 0 1px var(--xc-border-accent), 0 0 16px var(--xc-border-accent);
  animation: ir-report-record-highlight 1.6s ease-out;
}
@keyframes ir-report-record-highlight {
  0%, 100% { transform: translateY(0); }
  35% { transform: translateY(-2px); }
}
```

替换为：

```css
.ir-report-list__item--highlighted {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
  box-shadow: inset 0 1px 0 var(--xc-border-card), var(--xc-glow-blue);
}
```

- [ ] **Step 3: 运行定位测试确认通过**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: PASS，定位与高亮状态不受样式替换影响。

### Task 2: 回归与构建验证

**Files:**
- Verify: `tests/home-records-sidebar.spec.js`
- Verify: `tests/report-generation-flow.spec.js`
- Verify: `tests/home-welcome.spec.js`
- Verify: `src/views/home/index.vue`

- [ ] **Step 1: 运行侧栏相关回归测试**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js tests/report-generation-flow.spec.js tests/home-welcome.spec.js`

Expected: PASS。

- [ ] **Step 2: 构建生产产物**

Run: `npm run build`

Expected: Exit code 0。

- [ ] **Step 3: 检查变更**

Run: `git diff --check && git diff -- src/views/home/index.vue`

Expected: 无空白错误。不要执行 Git 写操作。
