# 市场脉搏内部滚动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将市场脉搏资讯改为固定高度的内部滚动列表，默认约可见五条，移除横向滚动资讯，并用“查看全部资讯”将内部列表平滑滚至末尾。

**Architecture:** 不调整后端接口与 Store。`MarketPulse.vue` 保留全部资讯 DOM，通过具固定高度和 `overflow-y: auto` 的滚动容器承载内容；组件内的按钮直接调用该容器的 `scrollTo`。按钮只在资讯数量超过五条时出现。

**Tech Stack:** Vue 3、Vitest、Vue Test Utils、CSS 自定义属性。

---

### Task 1: 为内部滚动行为添加失败测试

**Files:**
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 新增超过五条资讯的组件测试**

在 `政策与市场咨询组件` 测试中添加：

```javascript
it('资讯超过五条时提供内部滚动和查看全部入口', async () => {
  const news = Array.from({ length: 6 }, (_, index) => ({
    id: index + 1,
    title: `资讯 ${index + 1}`,
    publishTime: '2026-07-23T09:00:00',
    tags: [],
  }))
  const wrapper = mount(MarketPulse, { props: { news } })
  const scrollTo = vi.fn()
  const list = wrapper.get('[data-news-scroll]')
  Object.defineProperty(list.element, 'scrollHeight', { value: 960 })
  Object.defineProperty(list.element, 'clientHeight', { value: 320 })
  list.element.scrollTo = scrollTo

  expect(wrapper.find('.pm-pulse__ticker').exists()).toBe(false)
  expect(wrapper.findAll('[data-news-id]')).toHaveLength(6)
  await wrapper.get('[data-view-all-news]').trigger('click')
  expect(scrollTo).toHaveBeenCalledWith({ top: 640, behavior: 'smooth' })
})

it('资讯不超过五条时不显示查看全部入口', () => {
  const wrapper = mount(MarketPulse, {
    props: { news: Array.from({ length: 5 }, (_, index) => ({ id: index, title: `资讯 ${index}`, tags: [] })) },
  })

  expect(wrapper.find('[data-view-all-news]').exists()).toBe(false)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: FAIL，原因是横幅仍存在、滚动容器和入口均未实现。

### Task 2: 实现内部滚动资讯区

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 在脚本中定义滚动容器和入口状态**

移除 `tickerMessage` computed，保留 `computed` 仅用于：

```javascript
const newsScrollRef = ref(null)
const canViewAllNews = computed(() => props.news.length > 5)

function scrollToAllNews() {
  const container = newsScrollRef.value
  if (!container) return
  container.scrollTo({
    top: container.scrollHeight - container.clientHeight,
    behavior: 'smooth',
  })
}
```

从 Vue 导入 `ref`。

- [ ] **Step 2: 替换模板中的横幅和资讯列表容器**

删除 `.pm-pulse__ticker` 模板。将资讯条目放入带 ref 和测试标识的容器：

```vue
<div ref="newsScrollRef" class="pm-pulse__news" data-news-scroll>
  <p v-if="loading" class="pm-pulse__state">正在加载市场资讯</p>
  <p v-else-if="error" class="pm-pulse__state pm-pulse__state--error">{{ error }}</p>
  <p v-else-if="!news.length" class="pm-pulse__state">暂无市场资讯</p>
  <template v-else v-for="item in news" :key="item.id">
    <!-- 保留现有有外链 a / 无外链 div 条目分支 -->
  </template>
</div>
<button v-if="canViewAllNews" type="button" class="pm-pulse__view-all" data-view-all-news @click="scrollToAllNews">
  查看全部资讯
</button>
```

保留现有标题、标签、日期和外链安全属性；不截断数组，确保滚动容器内有全部记录。

- [ ] **Step 3: 增加固定高度与可滚动样式**

删除 `.pm-pulse__ticker` 相关样式，新增：

```css
.pm-pulse__news {
  display: grid;
  max-height: 432px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.pm-pulse__view-all {
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  padding: var(--xc-space-2) var(--xc-space-3);
  background: var(--xc-surface-raised);
  color: var(--xc-accent-blue);
  font: inherit;
  font-size: var(--xc-fs-xs);
  text-align: center;
  cursor: pointer;
}
.pm-pulse__view-all:hover,
.pm-pulse__view-all:focus-visible {
  border-color: var(--xc-accent-blue);
}
```

`432px` 对应紧凑资讯条目约五条的可见空间；窄屏仍由页面单列布局承载，不增加页面下方内容。

- [ ] **Step 4: 运行组件测试确认通过**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: PASS。

### Task 3: 执行回归验证并同步文档

**Files:**
- Modify: `my_projects/政策与市场模块-功能与开发文档.md`

- [ ] **Step 1: 更新市场脉搏描述**

将市场脉搏能力说明更新为：右侧资讯区固定高度、默认约显示五条、可在内部上下滚动；超过五条时“查看全部资讯”平滑滚动至内部列表末尾。删除任何横向滚动资讯或页面下方完整列表的表述。

- [ ] **Step 2: 运行前端政策与市场回归测试**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js`

Expected: PASS。

- [ ] **Step 3: 运行前端生产构建**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vite/bin/vite.js build`

Expected: 退出码 0；既有 Rollup 注释与大分包警告可记录但不视为失败。

- [ ] **Step 4: 提交此任务**

```bash
git add agent-frontend/src/views/policy-market/components/MarketPulse.vue agent-frontend/tests/policy-market-components.spec.js my_projects/政策与市场模块-功能与开发文档.md
git commit -m "feat: make market pulse news internally scrollable"
```
