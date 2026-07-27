# 侧栏测算与报告记录 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让测算页面右侧的测算记录和报告记录具备秒级时间、可靠的报告完成刷新、倒序展示与可用的自适应滚动布局。

**Architecture:** 在 `Home` 组件中集中格式化并排序侧栏展示数据，将每个分区拆成固定标题和可滚动列表。Store 在报告 SSE 完成后通过已存在的会话详情 API 同步权威的 `reports` 与版本报告元数据，保留当前消息流和选择状态。

**Tech Stack:** Vue 3 Composition API、Pinia、Vitest、Vue Test Utils、CSS Grid、XC design tokens。

## Global Constraints

- 不新增前端依赖；保持 npm 和现有 Vue/Pinia 模式。
- 颜色一律使用 `var(--xc-*)` token，不写十六进制或 rgb 值。
- 时间格式固定为 `YYYY-MM-DD HH:mm:ss`；空值或非法值显示 `—`。
- 右栏布局固定为 `minmax(0, 1fr) minmax(240px, 20%)`；两个标题不可随对应列表滚动。
- 报告只展示 `status === 'completed' && reportId` 的记录，并按 `createdAt` 降序；无效/缺失时间排在最后。
- 不执行 `git add`、`git commit`、`git push` 等 Git 写操作。

---

## File Structure

- Modify: `src/views/home/index.vue` — 侧栏的格式化/排序、固定标题+独立滚动列表结构、自适应 CSS 与报告查看按钮样式。
- Modify: `src/store/modules/calculation.js` — 报告完成后增量同步当前会话的报告元数据。
- Modify: `tests/report-generation-flow.spec.js` — 验证 SSE 完成后 Store 同步会话详情而不重建消息流。
- Create: `tests/home-records-sidebar.spec.js` — 验证侧栏时间、排序、结构和专用按钮类。

### Task 1: 完成后同步权威报告元数据

**Files:**
- Modify: `src/store/modules/calculation.js:2-13, 111-154, 226-275`
- Test: `tests/report-generation-flow.spec.js`

**Interfaces:**
- Consumes: `getConversation(conversationId)`，响应体为 `{ data: { versions: Array<{ taskId, report }>, reports: Array<Report> } }`。
- Produces: `syncReportsFromConversation(): Promise<void>`，仅更新 `reports`、匹配版本的 `version.report` 与 `reportTasks`；不修改 `messages`、`selectedVersion` 或 `conversationId`。

- [ ] **Step 1: 写出报告完成后同步的失败测试**

在 `tests/report-generation-flow.spec.js` 的 hoisted `calcApi` mock 中加入 `getConversation`，并新增以下用例：

```js
it('syncs complete report metadata from the conversation without replacing messages', async () => {
  reportApi.createReport.mockResolvedValue({ data: { reportTaskId: 8, taskId: 42, status: 'generating', steps: [] } })
  calcApi.getConversation.mockResolvedValue({
    data: {
      reports: [{ reportId: 'r-8', taskId: 42, version: 'V1', title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56', status: 'completed' }],
      versions: [{ taskId: 42, report: { reportId: 'r-8', title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56', status: 'completed' } }],
    },
  })
  stream.mockImplementation(async (_id, { onEvent }) => {
    onEvent({ type: 'complete', data: { reportTaskId: 8, taskId: 42, reportId: 'r-8', status: 'completed' } })
  })
  const store = useCalculationStore()
  store.conversationId = 'c-1'
  store.selectedVersion = 'V1'
  store.versions = [{ taskId: 42, version: 'V1' }]
  store.messages = [{ id: 'm-existing', kind: 'text', text: '保留消息' }]

  await store.generateReport(42)

  expect(calcApi.getConversation).toHaveBeenCalledWith('c-1')
  expect(store.reports).toEqual(calcApi.getConversation.mock.results[0].value ? expect.any(Array) : expect.any(Array))
  expect(store.reports[0]).toMatchObject({ title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56' })
  expect(store.versions[0].report).toMatchObject({ title: '甘肃项目投资报告' })
  expect(store.selectedVersion).toBe('V1')
  expect(store.messages.find((message) => message.id === 'm-existing')).toBeTruthy()
})
```

将不必要的 `mock.results` 断言改为：

```js
expect(store.reports).toHaveLength(1)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm exec vitest -- run tests/report-generation-flow.spec.js`

Expected: FAIL，因为当前测试 mock 未导出 `getConversation`，且 Store 在 SSE 完成后不请求会话详情。

- [ ] **Step 3: 实现最小会话报告同步方法**

在 `calculation.js` 中新增 action，使用已有 `getConversation` import：

```js
async syncReportsFromConversation() {
  if (!this.conversationId) return
  const response = await getConversation(this.conversationId)
  const detail = response.data || {}
  const reports = detail.reports || []
  this.reports = reports
  for (const version of this.versions) {
    const remote = (detail.versions || []).find((item) => item.taskId === version.taskId)
    if (remote?.report) version.report = remote.report
  }
  this.reportTasks = Object.fromEntries(
    [...reports, ...this.versions.map((version) => version.report)].filter(Boolean)
      .filter((report) => report.reportTaskId)
      .map((report) => [report.reportTaskId, report]),
  )
}
```

在 `generateReport()` 的 SSE `complete` 分支中，在 `_applyReport(data)` 与完成消息更新后调用：

```js
this.syncReportsFromConversation().catch(() => {})
```

仅在 `type === 'complete'` 调用；失败事件和流异常恢复路径维持现有 `_applyReport` 行为。

- [ ] **Step 4: 运行 Store 测试确认通过**

Run: `npm exec vitest -- run tests/report-generation-flow.spec.js`

Expected: PASS，现有进度卡测试与新增元数据同步测试都通过。

### Task 2: 侧栏数据格式与报告倒序展示

**Files:**
- Modify: `src/views/home/index.vue:121-164, 186-192, 218-228`
- Create: `tests/home-records-sidebar.spec.js`

**Interfaces:**
- Consumes: `calc.versions` 中的 `{ version, result, input, calculatedAt }`，以及 `calc.reports` 中的 `{ reportId, status, version, title, createdAt }`。
- Produces: `formatRecordTime(value): string` 与 `reversedReports`（已完成报告按有效 `createdAt` 降序的展示数组）。

- [ ] **Step 1: 新建侧栏展示失败测试**

创建 `tests/home-records-sidebar.spec.js`，沿用 `tests/home-welcome.spec.js` 的 session/store/router/子组件 mock 方式。将 store mock 设为有会话状态，最少包含：

```js
messages: [{ id: 'm-1', role: 'user', kind: 'text', text: '测算' }],
selectedVersion: 'V2',
latestVersion: { version: 'V2' },
versions: [
  { version: 'V1', taskId: 1, calculatedAt: '2026-07-27T14:10:56', result: { financial: { projectIrr: 8.1 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } } },
  { version: 'V2', taskId: 2, calculatedAt: null, result: { financial: { projectIrr: 8.2 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } } },
],
reports: [
  { reportId: 'old', status: 'completed', version: 'V1', title: '旧报告', createdAt: '2026-07-26T14:10:56' },
  { reportId: 'new', status: 'completed', version: 'V2', title: '新报告', createdAt: '2026-07-27T14:10:56' },
  { reportId: 'unknown', status: 'completed', version: 'V1', title: '无时间报告', createdAt: null },
],
```

新增断言：

```js
expect(wrapper.text()).toContain('测算时间：2026-07-27 14:10:56')
expect(wrapper.text()).toContain('测算时间：—')
expect(wrapper.text()).toContain('2026-07-27 14:10:56')
expect(wrapper.text()).not.toContain('2026-07-27T14:10:56')
const titles = wrapper.findAll('.ir-report-list__item strong').map((node) => node.text())
expect(titles).toEqual(['新报告', '旧报告', '无时间报告'])
expect(wrapper.find('.ir-report-list__view').exists()).toBe(true)
expect(wrapper.find('.ir-home__side-section > .ir-home__side-title').exists()).toBe(true)
expect(wrapper.find('.ir-home__side-section > .ir-home__side-scroll').exists()).toBe(true)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: FAIL，因为尚未显示测算时间、未格式化时间、未按时间排序，且新的结构/按钮类不存在。

- [ ] **Step 3: 实现格式化、稳定排序和模板结构**

在 `index.vue` 新增：

```js
function formatRecordTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function recordTimeValue(value) {
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? null : time
}

const reversedReports = computed(() => calc.reports
  .filter((report) => report.status === 'completed' && report.reportId)
  .map((report, index) => ({ report, index, time: recordTimeValue(report.createdAt) }))
  .sort((a, b) => {
    if (a.time === null && b.time === null) return a.index - b.index
    if (a.time === null) return 1
    if (b.time === null) return -1
    return b.time - a.time || a.index - b.index
  })
  .map(({ report }) => report))
```

将每个 `.ir-home__side-section` 中的空态或 `ul` 包裹在 `<div class="ir-home__side-scroll">` 中，标题保持为该 section 的第一个子元素。给测算版本的摘要和 IRR 之间加：

```vue
<div class="ir-ver__time">测算时间：{{ formatRecordTime(v.calculatedAt) }}</div>
```

将报告时间改为：

```vue
<span>{{ formatRecordTime(report.createdAt) }}</span>
```

并将报告记录查看按钮类改为：

```vue
<button class="ir-report-list__view" @click="openReport(report.reportId)">查看报告</button>
```

- [ ] **Step 4: 运行新增组件测试确认通过**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: PASS，时间、报告排序、标题/滚动容器结构与专用按钮类均通过。

### Task 3: 自适应右栏与固定标题的样式

**Files:**
- Modify: `src/views/home/index.vue:231-489`
- Test: `tests/home-records-sidebar.spec.js`

**Interfaces:**
- Consumes: Task 2 产生的 `.ir-home__side-scroll`、`.ir-ver__time`、`.ir-report-list__view`。
- Produces: 右栏为 `minmax(240px, 20%)`，两份列表各自在标题下滚动，报告查看按钮具有独立的较高灰色外观。

- [ ] **Step 1: 在组件测试中补充布局类断言**

在 `tests/home-records-sidebar.spec.js` 中补充以下断言，确保渲染结构具备样式选择器所需的节点：

```js
expect(wrapper.findAll('.ir-home__side-scroll')).toHaveLength(2)
expect(wrapper.find('.ir-ver__time').text()).toBe('测算时间：—')
```

- [ ] **Step 2: 运行测试确认当前结构失败**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js`

Expected: FAIL（若 Task 2 尚未实施）或 PASS（若 Task 2 已完成）；此步骤只确认结构测试持续覆盖样式依赖。

- [ ] **Step 3: 实现最小 CSS 调整**

在 `index.vue` 的 scoped style 中替换与补充以下规则：

```css
.ir-home { grid-template-columns: minmax(0, 1fr) minmax(240px, 20%); }
.ir-home__side { grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); }
.ir-home__side-section { min-height: 0; display: flex; flex-direction: column; }
.ir-home__side-scroll { min-height: 0; overflow-y: auto; padding-right: var(--xc-space-2); }
.ir-ver__time { margin: var(--xc-space-2) 0; font-size: var(--xc-fs-3xs); color: var(--xc-text-mute); }
.ir-report-list__view {
  min-height: 28px;
  padding: 4px var(--xc-space-3);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-3xs);
  cursor: pointer;
}
```

移除 `.ir-home__side-section { overflow-y: auto; }`，确保滚动只发生于 `.ir-home__side-scroll`。保留现有 `.ir-ver__report`，它仍用于测算记录的报告操作按钮。

- [ ] **Step 4: 运行相关前端测试**

Run: `npm exec vitest -- run tests/home-records-sidebar.spec.js tests/report-generation-flow.spec.js tests/home-welcome.spec.js`

Expected: PASS。

- [ ] **Step 5: 构建生产产物**

Run: `npm run build`

Expected: Exit code 0，Vite 生产构建完成。

## Final Verification

- [ ] **Step 1: 运行完整前端测试套件**

Run: `npm test`

Expected: Exit code 0，全部 Vitest 用例通过。

- [ ] **Step 2: 人工验证关键路径**

运行开发服务器后，在同一会话中完成至少两次测算并各生成一份报告。确认：

1. 测算记录显示秒级时间；
2. 报告时间不出现 `T`；
3. 新报告完成后无需刷新即可显示标题、关联版本、时间和查看入口；
4. 报告从新到旧排列；
5. 记录超过分区高度时标题固定，只有各自列表滚动；
6. 右栏宽度随窗口变化且不小于 240px；
7. 报告记录“查看报告”按钮较高且为灰色中性样式。

- [ ] **Step 3: 审查变更范围**

Run: `git diff --check && git diff -- src/views/home/index.vue src/store/modules/calculation.js tests/report-generation-flow.spec.js tests/home-records-sidebar.spec.js`

Expected: `git diff --check` 无空白错误；修改仅限本计划列出的文件。不要执行任何 Git 写操作。
