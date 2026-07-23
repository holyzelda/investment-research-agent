# 市场脉搏循环滚动修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复市场脉搏自动滚动到达底部后停止的问题，实现稳定的下滚、停留、回顶、再下滚循环。

**Architecture:** 仅调整 `MarketPulse.vue` 的底部定时回调。自动循环使用即时 `scrollTop = 0`，不使用平滑动画；用户点击“查看全部资讯”保持已有平滑滚动。测试通过 fake timer 精确验证底部回调重置位置并重新调度动画。

**Tech Stack:** Vue 3、Vitest、Vue Test Utils。

---

### Task 1: 为底部回顶循环添加失败测试

**Files:**
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 添加底部循环用例**

使用 `vi.useFakeTimers()`，并新增测试：

```javascript
it('自动滚动到底部停留后回到顶部并开始下一轮', async () => {
  vi.useFakeTimers()
  const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
  const list = wrapper.get('[data-news-scroll]').element
  Object.defineProperty(list, 'scrollHeight', { value: 960 })
  Object.defineProperty(list, 'clientHeight', { value: 432 })
  list.scrollTop = 527

  await wrapper.get('[data-news-scroll]').trigger('mouseleave')
  animationCallback(1000)
  animationCallback(1016)
  expect(list.scrollTop).toBe(528)

  await vi.advanceTimersByTimeAsync(1200)

  expect(list.scrollTop).toBe(0)
  expect(requestAnimationFrame).toHaveBeenCalledTimes(expect.any(Number))
  vi.useRealTimers()
})
```

在 `afterEach` 中调用 `vi.useRealTimers()`，确保其他测试不受影响。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: FAIL，因为当前回调调用 `scrollTo({ top: 0, behavior: 'smooth' })`，不会立即将 `scrollTop` 归零。

### Task 2: 以即时回顶实现稳定循环

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 修改底部停留后的回调**

在 `stepAutoScroll()` 的 `window.setTimeout` 回调中，将：

```javascript
container.scrollTo({ top: 0, behavior: 'smooth' })
```

替换为：

```javascript
container.scrollTop = 0
restartTimerId = null
lastTimestamp = null
startAutoScroll()
```

保持 `AUTO_SCROLL_BOTTOM_PAUSE_MS` 不变。不要改变 `scrollToAllNews()` 中面向用户的平滑滚动。

- [ ] **Step 2: 运行组件测试确认通过**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-components.spec.js`

Expected: PASS。

### Task 3: 回归验证与文档同步

**Files:**
- Modify: `my_projects/政策与市场模块-功能与开发文档.md`

- [ ] **Step 1: 将自动滚动描述明确为即时回顶循环**

将“到底部停留后平滑回顶循环”改为“到底部停留后即时回到顶部，再开始下一轮向下滚动”，避免与用户点击“查看全部资讯”的平滑滚动混淆。

- [ ] **Step 2: 运行前端政策与市场回归测试**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vitest/vitest.mjs run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js`

Expected: PASS。

- [ ] **Step 3: 运行前端生产构建**

Run: `cd agent-frontend && /e/openclaw/nodejs/node.exe node_modules/vite/bin/vite.js build`

Expected: 退出码 0；既有 Rollup 注释和大分包警告不视为失败。

- [ ] **Step 4: 提交此任务**

```bash
git add agent-frontend/src/views/policy-market/components/MarketPulse.vue agent-frontend/tests/policy-market-components.spec.js my_projects/政策与市场模块-功能与开发文档.md
git commit -m "fix: loop market pulse auto scroll"
```
