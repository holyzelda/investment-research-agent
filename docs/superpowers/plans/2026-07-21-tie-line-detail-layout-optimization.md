# 联络线右侧详情布局优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化联络线地图右侧详情栏宽度、内部间距和功率趋势按钮/图表布局，使 380–440px 详情栏内的线路档案与趋势图可读且可点击。

**Architecture:** 只调整现有 Vue 单文件组件和对应 Vitest，不改后端、不改 Store 数据结构、不重写地图页面。页面主体由 CSS Grid 控制桌面端地图/详情比例，小屏使用媒体查询切换单列上下布局；详情和趋势组件通过局部 CSS 释放有效宽度并改善按钮网格。

**Tech Stack:** Vue 3 SFC、CSS Grid、Vitest、@vue/test-utils、Vite、XC CSS token。

---

## 文件结构与职责

| 文件 | 变更 | 职责 |
|---|---|---|
| `agent-frontend/src/views/tie-line/index.vue` | 修改 | 页面主体地图/详情 Grid 布局和小屏降级。 |
| `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue` | 修改 | 右侧详情卡片内边距、标题区、指标卡片响应式。 |
| `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue` | 修改 | 日期按钮自适应网格、图表隐藏态避免覆盖按钮。 |
| `agent-frontend/tests/tie-line-layout.spec.js` | 新建 | 锁定页面主体 Grid、gap、小屏单列布局。 |
| `agent-frontend/tests/tie-line-detail-panel.spec.js` | 修改 | 锁定详情面板趋势事件、档案仍渲染。 |
| `agent-frontend/tests/tie-line-power-trend.spec.js` | 修改 | 锁定按钮可点击与隐藏图表不阻塞交互。 |

## Task 1：页面主体 Grid 扩宽右侧详情栏

**Files:**
- Create: `agent-frontend/tests/tie-line-layout.spec.js`
- Modify: `agent-frontend/src/views/tie-line/index.vue:92-115`

- [ ] **Step 1: 写页面布局失败测试**

新建 `agent-frontend/tests/tie-line-layout.spec.js`：

```js
import { describe, expect, it } from 'vitest'
import TieLinePage from '@/views/tie-line/index.vue'

describe('联络线页面主体布局', () => {
  it('桌面端使用地图主体和 380-440px 右侧详情栏', () => {
    const styles = TieLinePage.styles.map((style) => style.content).join('\n')

    expect(styles).toContain('grid-template-columns: minmax(680px, 1fr) clamp(380px, 31vw, 440px)')
    expect(styles).toContain('gap: 12px')
  })

  it('小屏切换为单列上下布局，避免横向溢出', () => {
    const styles = TieLinePage.styles.map((style) => style.content).join('\n')

    expect(styles).toContain('@media (max-width: 1180px)')
    expect(styles).toContain('grid-template-columns: 1fr')
    expect(styles).toContain('min-height: 520px')
  })
})
```

- [ ] **Step 2: 运行布局测试，确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-layout.spec.js
```

预期：失败，提示没有 `clamp(380px, 31vw, 440px)` 或没有小屏单列媒体查询。

- [ ] **Step 3: 修改页面主体布局 CSS**

在 `agent-frontend/src/views/tie-line/index.vue` 中替换相关 CSS：

```css
.tie-line-page__body {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(680px, 1fr) clamp(380px, 31vw, 440px);
  gap: 12px;
}
.tie-line-page__map-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--xc-map-ocean);
  border-radius: var(--xc-radius-md);
}
.tie-line-page__detail { min-width: 0; }
@media (max-width: 1440px) {
  .tie-line-page__header { align-items: flex-start; }
  .tie-line-page__heading { max-width: 420px; }
}
@media (max-width: 1180px) {
  .tie-line-page { overflow-y: auto; }
  .tie-line-page__body {
    flex: 0 0 auto;
    min-height: auto;
    grid-template-columns: 1fr;
    grid-template-rows: minmax(520px, 58vh) auto;
  }
  .tie-line-page__map-wrap { min-height: 520px; }
  .tie-line-page__detail { min-height: 0; }
}
```

删除原 `@media (max-width: 1440px)` 内的 `grid-template-columns: minmax(0, 1fr) 320px;`，避免小屏仍压窄右栏。

- [ ] **Step 4: 运行布局测试确认通过**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-layout.spec.js
```

预期：PASS。

## Task 2：优化详情面板内部有效宽度

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue:77-99`
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js`

- [ ] **Step 1: 写详情面板样式约束失败测试**

在 `agent-frontend/tests/tie-line-detail-panel.spec.js` 追加：

```js
it('详情面板使用紧凑内边距并在窄屏下指标退为单列', () => {
  const styles = TieLineDetailPanel.styles.map((style) => style.content).join('\n')

  expect(styles).toContain('padding: var(--xc-space-4)')
  expect(styles).toContain('@media (max-width: 1180px)')
  expect(styles).toContain('grid-template-columns: 1fr')
})
```

- [ ] **Step 2: 运行详情面板测试，确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

预期：新增测试失败，因为当前面板仍为 `padding: var(--xc-space-5)` 且没有窄屏指标单列规则。

- [ ] **Step 3: 调整详情面板 CSS**

在 `TieLineDetailPanel.vue` 中替换/追加：

```css
.tl-detail {
  height: 100%;
  box-sizing: border-box;
  padding: var(--xc-space-4);
  overflow-y: auto;
  background: var(--xc-surface-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
}
.tl-detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--xc-space-3);
}
.tl-detail__head > div { min-width: 0; }
.tl-detail__title {
  margin: var(--xc-space-1) 0 0;
  font-size: var(--xc-fs-h3);
  font-weight: var(--xc-fw-semi);
  line-height: var(--xc-lh-snug);
  overflow-wrap: anywhere;
}
.tl-detail__tag {
  flex: 0 0 auto;
  padding: var(--xc-space-1) var(--xc-space-2);
  color: var(--xc-text-soft);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-xs);
  font-size: var(--xc-fs-2xs);
}
@media (max-width: 1180px) {
  .tl-detail { height: auto; }
  .tl-detail__metrics { grid-template-columns: 1fr; }
}
```

保留已有 `.tl-detail__metrics` 桌面端 `repeat(2, minmax(0, 1fr))`。

- [ ] **Step 4: 运行详情测试确认通过**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

预期：PASS。

## Task 3：优化功率趋势按钮网格和隐藏图表层

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue:152-168`
- Modify: `agent-frontend/tests/tie-line-power-trend.spec.js`

- [ ] **Step 1: 写趋势按钮布局失败测试**

在 `agent-frontend/tests/tie-line-power-trend.spec.js` 追加：

```js
it('日期按钮使用自适应网格且隐藏图表不拦截点击', () => {
  const styles = TieLinePowerTrend.styles.map((style) => style.content).join('\n')

  expect(styles).toContain('repeat(auto-fit, minmax(58px, 1fr))')
  expect(styles).toContain('pointer-events: none')
})
```

- [ ] **Step 2: 运行趋势组件测试，确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-power-trend.spec.js
```

预期：失败，因为当前日期按钮为固定 `repeat(5, minmax(0, 1fr))`。

- [ ] **Step 3: 调整趋势按钮 CSS**

在 `TieLinePowerTrend.vue` 中替换 `.tl-power-trend__ranges`：

```css
.tl-power-trend__ranges {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(58px, 1fr));
  gap: var(--xc-space-1);
  margin-top: var(--xc-space-3);
}
```

保留 `.tl-power-trend__canvas--hidden` 中的：

```css
pointer-events: none;
```

- [ ] **Step 4: 运行趋势测试确认通过**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-power-trend.spec.js
```

预期：PASS。

## Task 4：验证构建并启动页面检查实际效果

**Files:**
- No source changes expected.

- [ ] **Step 1: 运行相关定向测试**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-layout.spec.js tests/tie-line-detail-panel.spec.js tests/tie-line-power-trend.spec.js
```

预期：3 个测试文件全部 PASS。

- [ ] **Step 2: 运行生产构建**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm build
```

预期：构建退出码 0。若仍有 Vite 大 chunk 警告，记录为既有构建警告，不作为本次失败。

- [ ] **Step 3: 启动开发页面**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm dev -- --host 127.0.0.1
```

预期：Vite 输出本地访问地址，例如 `http://127.0.0.1:5210/`。检查 `/tie-line` 页面：地图仍占主体，右侧约 400px，按钮可点击，自定义弹层可打开，窄屏不横向溢出。

## 覆盖自检

- 右侧详情默认 400px、范围 380–440px：Task 1 `clamp(380px, 31vw, 440px)`。
- 地图仍是主体：Task 1 `minmax(680px, 1fr)`。
- gap 12px：Task 1。
- 小屏无横向溢出：Task 1 单列上下布局。
- 线路档案和功率趋势区域优化：Task 2、Task 3。
- 不重写页面、不改数据结构：所有任务仅修改现有组件 CSS/测试。
