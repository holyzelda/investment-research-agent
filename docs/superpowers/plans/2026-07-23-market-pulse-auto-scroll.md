# 市场脉搏自动滚动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让市场脉搏内部资讯区在内容溢出时平缓自动循环滚动，并在用户悬停或手动操作时暂停。

**Architecture:** 自动滚动状态完全封装在 `MarketPulse.vue`。组件基于已存在的内部滚动容器，以 `requestAnimationFrame` 推进 `scrollTop`；抵达底部后通过短暂停留并回到顶部形成循环。鼠标进入、滚轮和触控事件暂停，离开后重新调度；组件卸载清理动画帧和定时器。

**Tech Stack:** Vue 3 Composition API、Vitest、Vue Test Utils、浏览器 `requestAnimationFrame`。

---

### Task 1: 为自动滚动行为添加失败测试

**Files:**
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 添加自动滚动测试与浏览器 API mock**

在测试顶部保存并 mock 动画 API：

```javascript
let animationCallback
let animationId = 0
beforeEach(() => {
  animationCallback = null
  vi.stubGlobal('requestAnimationFrame', vi.fn((callback) => {
    animationCallback = callback
    animationId += 1
    return animationId
  }))
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
})
afterEach(() => vi.unstubAllGlobals())
```

添加内容溢出时推进滚动的用例：

```javascript
it('资讯溢出时自动推进内部滚动位置', () => {
  const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
  const list = wrapper.get('[data-news-scroll]').element
  Object.defineProperty(list, 'scrollHeight', { value: 960 })
  Object.defineProperty(list, 'clientHeight', { value: 432 })
  list.scrollTop = 0

  wrapper.vm.startAutoScroll()
  animationCallback(1000)
  animationCallback(1016)

  expect(list.scrollTop).toBeGreaterThan(0)
})
```

添加悬停暂停与底部循环用例：

```javascript
it('悬停时暂停自动滚动，离开后恢复', async () => {
  const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
  const list = wrapper.get('[data-news-scroll]')
  Object.defineProperty(list.element, 'scrollHeight', { value: 960 })
  Object.defineProperty(list.element, 'clientHeight', { value: 432 })

  wrapper.vm.startAutoScroll()
  await list.trigger('mouseenter')
  expect(cancelAnimationFrame).toHaveBeenCalled()
  await list.trigger('mouseleave')
  expect(requestAnimationFrame).toHaveBeenCalledTimes(2)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: FAIL，因为组件没有公开 `startAutoScroll`，也没有处理悬停或自动动画。

### Task 2: 实现自动循环滚动与交互暂停

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 添加自动滚动状态与生命周期清理**

在 `<script setup>` 导入 `onMounted`、`onBeforeUnmount`、`nextTick`，并定义：

```javascript
const AUTO_SCROLL_SPEED = 18
const AUTO_SCROLL_BOTTOM_PAUSE_MS = 1200
let animationFrameId = null
let restartTimerId = null
let lastTimestamp = null
let isAutoScrollPaused = false
```

实现 `stopAutoScroll()`：取消已有动画帧和重启定时器，重置 `lastTimestamp`。实现 `startAutoScroll()`：仅当容器存在、未暂停且 `scrollHeight > clientHeight` 时调度 `requestAnimationFrame(stepAutoScroll)`。

在 `onMounted` 后 `nextTick(startAutoScroll)`，在 `onBeforeUnmount(stopAutoScroll)` 清理资源。为便于现有组件测试，保留 `startAutoScroll` 作为脚本 setup 的公开绑定。

- [ ] **Step 2: 实现动画帧和底部循环**

```javascript
function stepAutoScroll(timestamp) {
  const container = newsScrollRef.value
  if (!container || isAutoScrollPaused) return
  if (container.scrollHeight <= container.clientHeight) return

  if (lastTimestamp === null) {
    lastTimestamp = timestamp
  } else {
    const elapsedSeconds = (timestamp - lastTimestamp) / 1000
    container.scrollTop += AUTO_SCROLL_SPEED * elapsedSeconds
    lastTimestamp = timestamp
  }

  const maxScrollTop = container.scrollHeight - container.clientHeight
  if (container.scrollTop >= maxScrollTop) {
    container.scrollTop = maxScrollTop
    stopAnimationFrameOnly()
    restartTimerId = window.setTimeout(() => {
      container.scrollTo({ top: 0, behavior: 'smooth' })
      lastTimestamp = null
      startAutoScroll()
    }, AUTO_SCROLL_BOTTOM_PAUSE_MS)
    return
  }
  animationFrameId = window.requestAnimationFrame(stepAutoScroll)
}
```

`stopAnimationFrameOnly()` 只取消当前动画帧，不取消底部回顶定时器，以便 `stepAutoScroll` 安排循环。`startAutoScroll()` 先清理旧动画帧，避免重复调度。

- [ ] **Step 3: 处理用户交互与查看全部按钮竞争**

在资讯容器添加事件：

```vue
@mouseenter="pauseAutoScroll"
@mouseleave="resumeAutoScroll"
@wheel="pauseAutoScroll"
@touchstart="pauseAutoScroll"
@scroll="handleManualScroll"
```

实现：

```javascript
function pauseAutoScroll() {
  isAutoScrollPaused = true
  stopAutoScroll()
}
function resumeAutoScroll() {
  isAutoScrollPaused = false
  lastTimestamp = null
  startAutoScroll()
}
function handleManualScroll() {
  pauseAutoScroll()
}
```

在 `scrollToAllNews()` 的开头调用 `pauseAutoScroll()`，再保持已有 `container.scrollTo({ top: ..., behavior: 'smooth' })`。用户离开资讯区时才由 `mouseleave` 恢复自动滚动。

- [ ] **Step 4: 运行组件测试确认通过**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: PASS。

### Task 3: 同步文档并执行回归验证

**Files:**
- Modify: `my_projects/政策与市场模块-功能与开发文档.md`

- [ ] **Step 1: 更新市场脉搏说明**

补充以下行为：内容溢出时资讯区缓慢自动下滚，到底部停留后平滑回顶循环；用户悬停、滚轮或触控操作时暂停，离开后恢复。说明“查看全部资讯”触发后只滚动内部列表，且会暂停自动滚动。

- [ ] **Step 2: 运行前端政策与市场回归测试**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js`

Expected: PASS。

- [ ] **Step 3: 运行生产构建**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vite/bin/vite.js build`

Expected: 退出码 0；既有 Rollup 注释和大分包警告不视为失败。

- [ ] **Step 4: 提交此任务**

```bash
git add agent-frontend/src/views/policy-market/components/MarketPulse.vue agent-frontend/tests/policy-market-components.spec.js my_projects/政策与市场模块-功能与开发文档.md
git commit -m "feat: auto-scroll market pulse news"
```
