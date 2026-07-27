# 首页欢迎态清晰背景弱化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变投研主题底图内容与清晰度的前提下，降低欢迎态底图的视觉权重并消除全图模糊带来的未加载和眩晕观感。

**Architecture:** 仅修改 `Layout` 中已存在的 `.ir-layout__welcome-backdrop` 样式及其样式契约测试。背景图片与 XC 氛围渐变维持原样；删除全图 `filter` 和缩放，使用 `::after` 伪元素的两个 `linear-gradient()` 背景层分别实现全局轻度压暗和左侧文案区增强压暗。

**Tech Stack:** Vue 3 单文件组件、scoped CSS、Vitest、Vite

## Global Constraints

- 仅在 `isWelcome` 为真时作用于 `.ir-layout__welcome-backdrop`；对话态及其他路由不变。
- 不解读、裁切或修改投研主题背景图的内容与资源。
- 删除全图模糊与缩放，不得保留 `filter: blur()` 或 `transform: scale()`。
- 前景内容、AI 球体、顶栏、导航和侧栏不受遮罩影响。
- 遮罩仅使用既有 `var(--xc-*)` token，不新增硬编码 `#hex`、`rgb()` 或 `rgba()` 色值、Vue 状态、模板节点、依赖或交互。
- 不执行 Git 写操作。

---

### Task 1: 以清晰双层渐变遮罩替换底图模糊

**Files:**
- Modify: `agent-frontend/src/layout/index.vue:210-226`
- Modify: `agent-frontend/tests/layout-welcome-backdrop.spec.js:59-70`

**Interfaces:**
- Consumes: `isWelcome` 已控制 `.ir-layout__welcome-backdrop` 的欢迎态渲染；`--ir-welcome-bg` 提供底图 URL；`var(--xc-surface-workspace)` 提供深色表面 token。
- Produces: 欢迎态背景图保持原始清晰度；`::after` 使用两个渐变层压低底图视觉权重，左侧强于右侧；非欢迎态背景元素仍不渲染。

- [ ] **Step 1: 将样式契约测试改为期待清晰渐变方案**

在 `tests/layout-welcome-backdrop.spec.js` 的“首页且无会话时铺满全屏背景层”用例中，保留背景元素和 CSS 变量断言；删除当前 `filter: blur(2px);` 断言，并添加：

```js
expect(layoutSource).not.toContain('filter: blur(')
expect(layoutSource).not.toContain('transform: scale(')
expect(layoutSource).toContain('.ir-layout__welcome-backdrop::after')
expect(layoutSource).toContain('linear-gradient(90deg, var(--xc-surface-workspace) 0%, transparent 72%)')
expect(layoutSource).toContain('linear-gradient(0deg, var(--xc-surface-workspace) 0%, var(--xc-surface-workspace) 100%)')
```

保留 `background: var(--xc-surface-workspace);` 的断言只在最终 CSS 仍包含该精确文本时使用；本任务会用渐变 `background` 替换单色背景，因此删除该旧断言。

- [ ] **Step 2: 运行测试确认其因尚有模糊且缺少渐变而失败**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: FAIL，`layoutSource` 仍包含 `filter: blur(2px);`，且还没有双层 `linear-gradient()` 遮罩声明。

- [ ] **Step 3: 删除失焦规则，写入双层渐变遮罩**

在 `src/layout/index.vue` 的 `.ir-layout__welcome-backdrop` 中，删除：

```css
  filter: blur(2px);
  transform: scale(1.01);
```

将现有 `::after` 规则中的单色 `background` 与 `opacity` 替换为：

```css
.ir-layout__welcome-backdrop::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, var(--xc-surface-workspace) 0%, transparent 72%),
    linear-gradient(0deg, var(--xc-surface-workspace) 0%, var(--xc-surface-workspace) 100%);
  opacity: 0.48;
}
```

第一个渐变加强左侧文案和输入区的背景压暗，并在右侧平滑消退；第二个渐变提供均匀的全局压暗。保留背景容器原有的图片与 `var(--xc-grad-atmosphere)` 合成方式、定位、层级和 `pointer-events: none`。

- [ ] **Step 4: 运行单测确认欢迎态条件与清晰遮罩契约通过**

Run: `npm exec vitest -- run tests/layout-welcome-backdrop.spec.js`

Expected: PASS，四个用例全部通过，且源文件不再包含模糊或缩放规则。

- [ ] **Step 5: 运行关联测试与生产构建**

Run: `npm exec vitest -- run tests/home-welcome.spec.js tests/layout-welcome-backdrop.spec.js && npm run build`

Expected: 两个测试文件全部 PASS，Vite 生产构建成功；可保留已有第三方 `PURE` 注释和 chunk-size 警告。

- [ ] **Step 6: 查看本次前端差异，不进行 Git 写操作**

Run: `git diff -- src/layout/index.vue tests/layout-welcome-backdrop.spec.js`

Expected: 差异只含背景视觉处理和测试契约调整；不得执行 `git add`、`git commit`、`git push` 或其他 Git 写操作。
