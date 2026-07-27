# 报告记录定位视觉强化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一两类记录中的报告操作按钮尺寸，并增强报告记录定位后的可见反馈。

**Architecture:** 保持既有 `.ir-report-list__view` 作为统一按钮语义类，通过上下文选择器让测算记录和报告记录内的按钮全宽。保持既有目标卡片高亮状态，并在该状态补充 token 化阴影与短暂动画。

**Tech Stack:** Vue 3、Vitest、Vue Test Utils、CSS、XC design tokens。

## Global Constraints

- 不新增依赖，不修改 Store 或路由行为。
- 按钮均使用 `.ir-report-list__view`，在两类记录中占满对应卡片内容宽度。
- 定位高亮保持约 1.6 秒，并使用 XC tokens；禁止写入 hex/rgb 色值。
- 不执行 Git 写操作。

---

## File Structure

- Modify: `src/views/home/index.vue` — 按钮全宽规则及增强的卡片定位高亮视觉。
- Modify: `tests/home-records-sidebar.spec.js` — 验证两类卡片的按钮均带统一样式类。

### Task 1: 统一按钮与强化目标卡片

**Files:**
- Modify: `src/views/home/index.vue:127-168, 480-510`
- Modify: `tests/home-records-sidebar.spec.js`

**Interfaces:**
- Consumes: 测算记录和报告记录已使用的 `.ir-report-list__view` 与 `ir-report-list__item--highlighted`。
- Produces: 两个上下文中的按钮均为全宽；目标卡片高亮类包含动画和 token 化外发光。

- [ ] **Step 1: 写出统一按钮样式类的失败测试**

在 `tests/home-records-sidebar.spec.js` 的结构测试中追加：

```js
expect(wrapper.findAll('.ir-ver__item > .ir-report-list__view')).toHaveLength(2)
expect(wrapper.findAll('.ir-report-list__item > .ir-report-list__view')).toHaveLength(3)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: FAIL，因为当前结构中的按钮不是测算卡片的直接子元素（或测试需要根据实际结构调整为精准、可观察的统一按钮选择器）。

- [ ] **Step 3: 实施最小视觉样式**

确认实际按钮均具有 `.ir-report-list__view` 后，在 `index.vue` 的 scoped style 增加：

```css
.ir-ver__item > .ir-report-list__view,
.ir-report-list__item > .ir-report-list__view { width: 100%; }

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

替换旧的 `.ir-report-list__item--highlighted` 单行规则，避免重复选择器覆盖。保留 `min-height`、padding、灰色边框等既有 `.ir-report-list__view` 基础样式。

- [ ] **Step 4: 运行组件测试确认通过**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: PASS，包含按钮结构、时间/排序与卡片定位高亮测试。

### Task 2: 回归与构建验证

**Files:**
- Verify: `tests/home-records-sidebar.spec.js`
- Verify: `tests/report-generation-flow.spec.js`
- Verify: `tests/home-welcome.spec.js`
- Verify: `src/views/home/index.vue`

- [ ] **Step 1: 运行侧栏回归测试**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js tests/report-generation-flow.spec.js tests/home-welcome.spec.js`

Expected: PASS。

- [ ] **Step 2: 构建生产产物**

Run: `npm run build`

Expected: Exit code 0。

- [ ] **Step 3: 检查变更**

Run: `git diff --check && git diff -- src/views/home/index.vue tests/home-records-sidebar.spec.js`

Expected: 无空白错误。不要执行 Git 写操作。
