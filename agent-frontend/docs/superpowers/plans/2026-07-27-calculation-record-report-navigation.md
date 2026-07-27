# 测算记录报告跳转 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将测算记录时间移至 IRR 后，并让已生成报告在右侧栏内定位到对应报告记录卡片。

**Architecture:** 首页组件用报告列表滚动容器 ref 与稳定的 `data-report-id` 锚点完成同栏定位。测算记录根据报告状态渲染统一中性按钮，定位后用短暂响应式高亮标识目标卡片。

**Tech Stack:** Vue 3 Composition API、Vue Test Utils、Vitest、CSS、XC design tokens。

## Global Constraints

- 不新增依赖；保持现有 Vue 3 Composition API 与 npm 工作流。
- 颜色只使用 `var(--xc-*)` token。
- 无报告显示“生成报告”，生成中显示禁用“报告生成中”，失败显示“重新生成报告”，已完成显示“跳转报告记录”。
- 已完成报告仅滚动报告记录列表，不进行路由跳转。
- 不执行 `git add`、`git commit`、`git push` 等 Git 写操作。

---

## File Structure

- Modify: `src/views/home/index.vue` — 调整测算记录元素顺序、报告操作分支、报告卡片锚点、定位/高亮逻辑和样式。
- Modify: `tests/home-records-sidebar.spec.js` — 覆盖时间顺序、已完成报告文案和卡片定位高亮。

### Task 1: 测算记录报告操作与同栏定位

**Files:**
- Modify: `src/views/home/index.vue:127-167, 186-245, 432-510`
- Modify: `tests/home-records-sidebar.spec.js`

**Interfaces:**
- Consumes: 测算版本的 `v.report`（至少含 `status`、`reportId`）和报告记录的 `report.reportId`。
- Produces: `jumpToReportRecord(reportId): Promise<void>`；目标报告卡片带 `data-report-id`，瞬时带 `ir-report-list__item--highlighted` 类。

- [ ] **Step 1: 写出时间顺序与已完成报告定位的失败测试**

在 `tests/home-records-sidebar.spec.js` 的 `calc.versions` 的 V2 条目加入：

```js
report: { reportId: 'new', status: 'completed' },
```

在已有的时间测试中加入：

```js
const versionText = wrapper.findAll('.ir-ver__item')[0].text()
expect(versionText.indexOf('项目全投资IRR')).toBeLessThan(versionText.indexOf('测算时间：—'))
expect(wrapper.findAll('.ir-ver__item')[0].get('.ir-report-list__view').text()).toBe('跳转报告记录')
```

新增定位测试，在 jsdom 中给 `Element.prototype.scrollIntoView` 安装 spy：

```js
it('scrolls and highlights the matching report card from a completed calculation', async () => {
  const scrollIntoView = vi.fn()
  Element.prototype.scrollIntoView = scrollIntoView
  const wrapper = mount(Home)

  await wrapper.findAll('.ir-ver__item')[0].get('.ir-report-list__view').trigger('click')

  const target = wrapper.get('[data-report-id="new"]')
  expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'nearest' })
  expect(target.classes()).toContain('ir-report-list__item--highlighted')
})
```

- [ ] **Step 2: 运行组件测试确认失败**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: FAIL，因为当前测算时间在 IRR 前，已完成报告仍显示“查看报告”并触发页面路由，且报告卡片没有定位锚点或高亮类。

- [ ] **Step 3: 实现最小模板与状态改动**

在 `index.vue`：

1. 将 `.ir-ver__time` 移到 `.ir-ver__metric` 之后。
2. 将测算记录按钮改为 `.ir-report-list__view`，按以下逻辑绑定：

```vue
:disabled="v.report?.status === 'generating'"
@click.stop="v.report?.status === 'completed' ? jumpToReportRecord(v.report.reportId) : calc.generateReport(v.taskId)"
```

文案为：

```vue
{{ v.report?.status === 'completed' ? '跳转报告记录' : v.report?.status === 'generating' ? '报告生成中' : v.report?.status === 'failed' ? '重新生成报告' : '生成报告' }}
```

3. 报告记录滚动容器增加 `ref="reportListEl"`；报告卡片添加 `:data-report-id="report.reportId"` 和条件高亮：

```vue
:class="{ 'ir-report-list__item--highlighted': highlightedReportId === report.reportId }"
```

4. 新增响应式状态与方法：

```js
const reportListEl = ref(null)
const highlightedReportId = ref(null)
let reportHighlightTimer

async function jumpToReportRecord(reportId) {
  await nextTick()
  const target = reportListEl.value?.querySelector(`[data-report-id="${reportId}"]`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  highlightedReportId.value = reportId
  clearTimeout(reportHighlightTimer)
  reportHighlightTimer = setTimeout(() => { highlightedReportId.value = null }, 1600)
}
```

5. 加入 token 化高亮样式：

```css
.ir-report-list__item--highlighted {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
}
```

- [ ] **Step 4: 运行组件测试确认通过**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: PASS，时间顺序、按钮状态、滚动定位和高亮均通过。

### Task 2: 相关回归与构建验证

**Files:**
- Verify: `tests/home-records-sidebar.spec.js`
- Verify: `tests/report-generation-flow.spec.js`
- Verify: `tests/home-welcome.spec.js`
- Verify: `src/views/home/index.vue`

**Interfaces:**
- Consumes: Task 1 的测算记录按钮与报告卡片锚点。
- Produces: 回归验证证据。

- [ ] **Step 1: 运行侧栏与报告生成相关测试**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js tests/report-generation-flow.spec.js tests/home-welcome.spec.js`

Expected: PASS。

- [ ] **Step 2: 构建生产产物**

Run: `npm run build`

Expected: Exit code 0。

- [ ] **Step 3: 检查变更范围和空白**

Run: `git diff --check && git diff -- src/views/home/index.vue tests/home-records-sidebar.spec.js`

Expected: `git diff --check` 无空白错误，改动局限于计划文件和首页/测试文件。不要执行 Git 写操作。
