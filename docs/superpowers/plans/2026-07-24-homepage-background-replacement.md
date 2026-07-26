# 首页欢迎态全局背景图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户提供的深色科技底图作为首页无会话欢迎态铺满整个外壳的最底层背景，位于顶栏与悬浮 rail / 历史侧栏下层，并保留 XC 氛围色；欢迎内容布局与交互不变。

**Architecture:** 背景层由全局外壳 `src/layout/index.vue` 承载（而非 `Home` 局部）。源图复制进 `src/assets` 并由 layout `import`；仅在 `route.name === 'Home'` 且 `calc.messages.length === 0` 时渲染一个 `aria-hidden` 背景元素，绝对定位铺满 `.ir-layout`。背景合成为「XC 氛围渐变叠加在图片之上」，使深色 RGB 图片打底、设计语言色透出。顶栏与主体升 `z-index` 浮于其上。

**Tech Stack:** Vue 3 SFC、Vite 静态资源导入、Vitest、Vue Test Utils。

## Global Constraints

- 仅首页无会话欢迎态显示；对话态、报告页、联络线页不显示。
- 背景铺满整个 `.ir-layout`（100vh），位于顶栏与悬浮 rail/sidebar 下层。
- 图片 `cover` 铺满、允许裁切；氛围渐变叠加在上保留 XC 青/紫设计色。
- 背景层 `pointer-events: none`；导航与欢迎交互保持可用。
- 组件样式禁止新增内联 hex/rgb；一律 `var(--xc-*)`，图片经 CSS 变量注入。
- 不改动 `AppRail`/`AppSidebar` 样式；不新增依赖、接口、状态或 Git 写操作。
- 不改变欢迎态标题、文案、能力标签、输入框与示例胶囊的现有布局、尺寸或间距。

---

### Task 1: 全局 layout 背景层与 Home 局部背景清理

**Files:**
- Replace asset: `src/assets/home-welcome-background.png`（用 `首页v1.png` 覆盖）
- Modify: `src/layout/index.vue`（模板背景 DOM、`import`、`showWelcomeBackdrop` 计算、CSS 层级）
- Modify: `src/views/home/index.vue`（移除 `.ir-welcome__background*` DOM/CSS、`welcomeBackgroundSrc` 导入、`heroFailed`/`hideEnergyHero`）
- Test: `tests/layout-welcome-backdrop.spec.js`（新增）、`tests/home-welcome.spec.js`（更新）

**Interfaces:**
- Consumes: 源图片 `D:\0_工作\2026\投研智能体\报告模块\首页v1.png`。
- Produces: 全局背景 DOM `.ir-layout__welcome-backdrop`，由 `showWelcomeBackdrop` 控制；图片经 `--ir-welcome-bg` 注入。

- [x] **Step 1: 用新图覆盖静态资源**（复用既有文件名，无导入路径变更）
- [x] **Step 2: 更新测试描述全局背景契约**（新增 layout 背景用例；home-welcome 改为断言无局部背景）
- [x] **Step 3: layout 模板新增背景 DOM + `import` + `showWelcomeBackdrop` 计算**
- [x] **Step 4: layout CSS 新增 `.ir-layout__welcome-backdrop` 合成层，顶栏/主体升 `z-index: 1`**
- [x] **Step 5: 清理 Home 局部背景 DOM / CSS / 导入 / `heroFailed` 逻辑**
- [x] **Step 6: 定向测试通过**（`layout-welcome-backdrop` + `home-welcome` + `logo-mask`）
- [x] **Step 7: 全量测试与构建通过**（`npm test` 168 通过；`npm run build` 成功、图片指纹化打包）
- [x] **Step 8: 检查无内联 hex/rgb 新增、旧引用无残留；不执行 Git 写操作**
