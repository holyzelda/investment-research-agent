# 首页欢迎态背景构图调整 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将欢迎态投研主题背景图轻微右移并缩小，保留当前清晰双层渐变遮罩和前景视觉层级。

**Architecture:** 只调整 `.ir-layout__welcome-backdrop` 的第二个背景层。XC 氛围渐变仍覆盖全屏；图片背景从居中 `cover` 调整为 `58% center / 96% auto`，由现有工作区深色底色和遮罩自然承接缩小后可见的边缘。

**Tech Stack:** Vue 3 单文件组件、scoped CSS、Vitest、Vite

## Global Constraints

- 仅欢迎态的 `.ir-layout__welcome-backdrop` 生效；对话态和其他路由不得变化。
- 不修改背景资源、双层遮罩、前景内容、AI 球体、模板、状态或交互。
- 背景图保持清晰，不添加模糊、缩放 `filter` 或 transform。
- 使用当前 XC token 和背景变量；不新增依赖、状态或硬编码颜色。
- 不执行 Git 写操作。

---

### Task 1: 调整欢迎态背景图片位置和尺寸

**Files:**
- Modify: `agent-frontend/src/layout/index.vue:211-217`
- Modify: `agent-frontend/tests/layout-welcome-backdrop.spec.js:59-74`

**Interfaces:**
- Consumes: `--ir-welcome-bg` 为 Vite 导入的投研主题图片 URL；`var(--xc-grad-atmosphere)` 为保持全屏覆盖的第一背景层。
- Produces: 图片背景使用 `58% center / 96% auto no-repeat`，实现约 8% 的右移和约 4% 的缩小；现有欢迎态渲染条件及遮罩规则保持不变。

- [ ] **Step 1: 写入背景构图样式契约测试**

在欢迎态背景测试中新增：

```js
expect(welcomeBackdropStyles).toContain('var(--ir-welcome-bg) 58% center / 96% auto no-repeat')
```

保留已有的背景元素渲染、无模糊/缩放和双层遮罩断言。

- [ ] **Step 2: 运行单测确认其因旧的居中 cover 背景而失败**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: FAIL，找不到 `var(--ir-welcome-bg) 58% center / 96% auto no-repeat`。

- [ ] **Step 3: 修改背景图片层的定位和尺寸**

将背景声明改为：

```css
background: var(--xc-grad-atmosphere), var(--ir-welcome-bg) 58% center / 96% auto no-repeat;
```

不要修改 `.ir-layout__welcome-backdrop::after` 的双层渐变遮罩。

- [ ] **Step 4: 运行单测确认构图与既有欢迎态契约通过**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: PASS，四个用例均通过。

- [ ] **Step 5: 运行关联测试和生产构建**

Run: `npm exec vitest -- run tests/home-welcome.spec.js tests/layout-welcome-backdrop.spec.js && npm run build`

Expected: 7 个关联测试全部通过，Vite 生产构建成功；允许保留既有第三方 `PURE` 注释和 chunk-size 警告。

- [ ] **Step 6: 查看改动差异，不进行 Git 写操作**

Run: `git diff -- src/layout/index.vue tests/layout-welcome-backdrop.spec.js`

Expected: 差异只包含背景图片定位/尺寸与对应测试断言调整；不得执行 Git 写操作。
