# 首页欢迎态背景弱化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 仅在首页无会话欢迎态中弱化全屏背景图，使前景文案、输入框与 AI 球体成为清晰的视觉焦点。

**Architecture:** 在现有 `Layout` 的 `.ir-layout__welcome-backdrop` 背景容器内完成视觉处理，不改模板、状态或资源。通过背景容器的 `::after` 伪元素叠加 XC 深色表面 token 遮罩，并让背景容器本身以轻微 CSS `filter: blur(2px)` 弱化图片细节；背景容器保持 `pointer-events: none` 和底层层级，前景不受影响。

**Tech Stack:** Vue 3 单文件组件、scoped CSS、Vite、Vitest

## Global Constraints

- 仅作用于 `src/layout/index.vue` 中由 `isWelcome` 控制的 `.ir-layout__welcome-backdrop`。
- 仅在首页无会话欢迎态生效；对话态和非首页路由不得改变。
- 不变更背景图片资源、欢迎态布局、前景组件、AI 球体、顶栏、侧栏、导航、接口或状态。
- 不新增依赖、配置项或运行时状态。
- 组件样式不新增硬编码 `#hex`、`rgb()` 或 `rgba()`，颜色使用既有 `var(--xc-*)` token。
- 不执行 Git 写操作。

---

### Task 1: 弱化欢迎态全局背景层

**Files:**
- Modify: `agent-frontend/src/layout/index.vue:210-217`
- Test: `agent-frontend/tests/layout-welcome-backdrop.spec.js`

**Interfaces:**
- Consumes: `isWelcome` 已控制欢迎态背景元素的渲染；`--ir-welcome-bg` 已提供背景图片 URL。
- Produces: `.ir-layout__welcome-backdrop` 在欢迎态保留原有图片和氛围渐变，同时具有 `filter: blur(2px)` 与 `::after` 的 XC token 深色蒙层；非欢迎态不渲染该元素。

- [ ] **Step 1: 写入验证欢迎态背景视觉处理的失败测试**

在 `tests/layout-welcome-backdrop.spec.js` 的欢迎态断言中，取得 `.ir-layout__welcome-backdrop`，并断言其 class 仍存在且相关组件样式含有以下规则：

```js
expect(wrapper.find('.ir-layout__welcome-backdrop').exists()).toBe(true)
expect(layoutSource).toContain('filter: blur(2px);')
expect(layoutSource).toContain('.ir-layout__welcome-backdrop::after')
expect(layoutSource).toContain('background: var(--xc-surface-workspace);')
```

其中 `layoutSource` 通过测试文件顶层读取 `src/layout/index.vue` 原始文本，沿用仓库现有测试的 Node 文件读取方式；断言不使用快照，以避免与样式格式化无关的变动造成失败。

- [ ] **Step 2: 运行单测确认其因缺少视觉规则而失败**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: FAIL，断言无法在 `src/layout/index.vue` 中找到 `filter: blur(2px);` 和 `.ir-layout__welcome-backdrop::after`。

- [ ] **Step 3: 在背景层添加轻微模糊和蒙层**

在 `.ir-layout__welcome-backdrop` 中保留现有定位、层级、图片和渐变背景声明，紧接其后加入：

```css
  filter: blur(2px);
  transform: scale(1.01);
```

随后新增伪元素规则：

```css
.ir-layout__welcome-backdrop::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--xc-surface-workspace);
  opacity: 0.45;
}
```

`transform: scale(1.01)` 用于覆盖 `blur(2px)` 在背景层边缘可能露出的透明像素；遮罩以 `opacity` 单独控制，因此不会覆盖或改变原有 `var(--xc-grad-atmosphere)` 与图片合成方式。不要修改模板和 JavaScript。

- [ ] **Step 4: 运行单测确认规则与欢迎态条件均通过**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: PASS，且既有欢迎态和非欢迎态渲染断言不变。

- [ ] **Step 5: 运行关联页面测试与生产构建**

Run: `npm exec vitest -- run tests/home-welcome.spec.js tests/layout-welcome-backdrop.spec.js && npm run build`

Expected: 两个测试文件均 PASS，Vite 生产构建成功完成。

- [ ] **Step 6: 检查工作区差异，不执行 Git 写操作**

Run: `git diff -- agent-frontend/src/layout/index.vue agent-frontend/tests/layout-welcome-backdrop.spec.js`

Expected: 只包含背景弱化规则及其对应测试；不执行 `git add`、`git commit` 或其他 Git 写操作。
