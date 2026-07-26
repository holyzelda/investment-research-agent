# 首页参考图复刻实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以用户提供的参考图和高清集装箱素材重构首页欢迎态，同时完整保留既有会话、测算、报告、导航和历史会话行为。

**Architecture:** 保持 `layout/index.vue`、`AppRail.vue`、`AppSidebar.vue`、`views/home/index.vue` 和 `ChatComposer.vue` 的既有职责边界。欢迎态改为左侧交互列和右侧集装箱主视觉列；顶栏使用本地展示配置渲染三项指标，不调用统计接口；会话态分支和 Pinia/API 契约不变。

**Tech Stack:** Vue 3 Composition API、Vite、Pinia、Element Plus、CSS custom properties、Vitest、Vue Test Utils。

## Global Constraints

- 以 `1618 x 972` 桌面视口作为视觉对齐基准，顶栏高度固定为约 `52px`。
- 只使用现有 `--xc-*` 设计令牌；组件样式不得新增硬编码颜色值。
- 集装箱主视觉源自 `D:\0_工作\2026\投研智能体\报告模块\集装箱.png`（1448 x 1086 RGB），项目内文件名固定为 `src/assets/home-energy-storage-hero.png`。
- 主视觉只在 `!hasConversation` 欢迎态渲染，并以 `mix-blend-mode: screen` 融入工作台背景；加载失败时隐藏自身，不显示破图图标。
- 顶栏指标固定为覆盖省份 `28 个`、生成报告 `256 份`、测算项目数 `128 个`，仅为本地展示配置，不新增后端请求。
- 历史会话侧栏根节点必须具有 `data-testid="history-sidebar"`，不得渲染“查看全部历史会话”文字、链接或占位区域。
- `onSend -> calc.sendAndCalculate`、`ChatComposer` 的 `responding`/`placeholder` props 和 `send` 事件、路由映射、会话和报告行为必须保持不变。
- 窄屏允许两列堆叠或收窄；指标可隐藏，但输入框必须可见可用。
- 不修改后端、数据库、接口、Pinia 数据结构或计算规则；不新增依赖。
- 不执行任何 Git 命令（包括 `git add`、`git commit`、`git push`、`git restore`）。

---

## File Structure

- Replace: `agent-frontend/src/assets/home-energy-storage-hero.png` — 用户提供的高清集装箱主视觉。
- Modify: `agent-frontend/src/design-system/tokens.css` — 统一顶栏高度令牌为 52px。
- Modify: `agent-frontend/src/layout/index.vue` — 三段式矮顶栏和本地指标配置。
- Modify: `agent-frontend/src/layout/components/AppRail.vue` — 参考图对应的轨道尺寸、间距和激活视觉，不变更路由逻辑。
- Modify: `agent-frontend/src/layout/components/AppSidebar.vue` — 历史面板测试锚点和参考图视觉密度，不变更交互逻辑。
- Modify: `agent-frontend/src/views/home/index.vue` — 欢迎态左右分栏、主视觉加载兜底和响应式布局；不触碰会话态结构。
- Modify: `agent-frontend/src/views/home/components/ChatComposer.vue` — 输入框外观尺寸和令牌化样式，不改变组件 API。
- Modify: `agent-frontend/tests/home-welcome.spec.js` — 主视觉与示例指令发送回归。
- Modify: `agent-frontend/tests/layout-sidebar.spec.js` — 历史侧栏锚点与禁用全历史入口回归。

### Task 1: 锁定欢迎态和历史侧栏行为

**Files:**
- Modify: `agent-frontend/tests/home-welcome.spec.js`
- Modify: `agent-frontend/tests/layout-sidebar.spec.js`

**Interfaces:**
- Consumes: `Home` 的欢迎态条件 `!hasConversation`、`ChatComposer` 的 `send` 事件、`calc.sendAndCalculate(text)`。
- Produces: `.ir-welcome__energy-hero` 与 `[data-testid="history-sidebar"]` 的稳定测试契约。

- [ ] **Step 1: 将欢迎态的 `ChatComposer` mock 改为可触发 `send` 的按钮**

  用以下 mock 替换 `tests/home-welcome.spec.js` 现有的 `ChatComposer` mock：

  ```js
  vi.mock('@/views/home/components/ChatComposer.vue', () => ({
    default: {
      template: `
        <button
          data-testid="welcome-send"
          @click="$emit('send', '测算甘肃 200MW/800MWh 独立储能项目')"
        />
      `,
    },
  }))
  ```

- [ ] **Step 2: 补充欢迎态结构和发送行为断言**

  在同一 `describe('home welcome presentation', ...)` 中保留现有主视觉断言，并加入：

  ```js
  it('sends a welcome example through the existing calculation flow', async () => {
    const wrapper = mount(Home, { global: { stubs: {} } })

    await wrapper.get('[data-testid="welcome-send"]').trigger('click')

    expect(calc.sendAndCalculate).toHaveBeenCalledWith(
      '测算甘肃 200MW/800MWh 独立储能项目',
    )
  })
  ```

- [ ] **Step 3: 补充侧栏禁用全历史入口断言**

  在 `tests/layout-sidebar.spec.js` 的 `marks the history panel...` 测试中，保留现有 `data-testid` 断言并加入：

  ```js
  expect(wrapper.text()).not.toContain('查看全部历史会话')
  expect(wrapper.find('[data-testid="all-history-link"]').exists()).toBe(false)
  ```

- [ ] **Step 4: 运行聚焦测试，确认当前缺少测试锚点时失败**

  在 `agent-frontend/` 目录运行：

  ```bash
  npm exec vitest -- run tests/home-welcome.spec.js tests/layout-sidebar.spec.js
  ```

  预期：`home-welcome.spec.js` 中主视觉测试和 `layout-sidebar.spec.js` 中侧栏锚点测试在实施前失败；发送行为和全历史入口断言可通过。

- [ ] **Step 5: 不执行 Git 操作**

  保留测试改动在工作区，继续后续任务。

### Task 2: 替换高清集装箱主视觉资源

**Files:**
- Replace: `agent-frontend/src/assets/home-energy-storage-hero.png`
- Source: `D:\0_工作\2026\投研智能体\报告模块\集装箱.png`

**Interfaces:**
- Consumes: 用户提供的 1448 x 1086 RGB PNG。
- Produces: 可由 `import energyStorageHeroSrc from '@/assets/home-energy-storage-hero.png'` 静态导入的 PNG。

- [ ] **Step 1: 覆盖项目中的旧截图裁切资源**

  在仓库根目录运行：

  ```bash
  cp '/d/0_工作/2026/投研智能体/报告模块/集装箱.png' \
    'agent-frontend/src/assets/home-energy-storage-hero.png'
  ```

  这不是截图裁切操作；必须原样复制用户提供的高清素材。

- [ ] **Step 2: 用显式 Python 3.13 解释器确认资源尺寸和模式**

  在仓库根目录运行：

  ```bash
  'C:/Users/JDPC0200/AppData/Local/Programs/Python/Python313/python.exe' -c "from PIL import Image; image = Image.open(r'agent-frontend/src/assets/home-energy-storage-hero.png'); print(image.size, image.mode)"
  ```

  预期输出：`(1448, 1086) RGB`。

- [ ] **Step 3: 在资源浏览器中目视检查文件**

  确认图中包含集装箱、发光圆形底座、REVENUE/ENERGY/POWER 信息面板和输电塔；不应出现首页文案、输入框、左侧导航或历史面板。

- [ ] **Step 4: 不执行 Git 操作**

  不暂存或提交替换后的静态资源。

### Task 3: 收窄顶栏并重整左侧工作台外壳

**Files:**
- Modify: `agent-frontend/src/design-system/tokens.css:197-200`
- Modify: `agent-frontend/src/layout/index.vue:4-14,49-125,145-190`
- Modify: `agent-frontend/src/layout/components/AppRail.vue:61-129`
- Modify: `agent-frontend/src/layout/components/AppSidebar.vue:3-10,156-304`
- Test: `agent-frontend/tests/layout-sidebar.spec.js`

**Interfaces:**
- Consumes: `session.username`、已有 `AppRail` 路由事件和 `AppSidebar` 全部 emits。
- Produces: 高度由 `var(--xc-topbar-h)` 驱动的顶栏，以及带 `data-testid="history-sidebar"` 的历史面板根节点。

- [ ] **Step 1: 更新唯一的顶栏高度令牌**

  在 `tokens.css` 的布局常量区域，将：

  ```css
  --xc-topbar-h:    88px;
  ```

  替换为：

  ```css
  --xc-topbar-h:    52px;
  ```

  保持 `--xc-rail-w: 46px`、`--xc-sidebar-w: 300px` 和 `--xc-gutter-x: 24px` 不变，避免无必要改变其他页面布局。

- [ ] **Step 2: 为顶栏定义本地展示指标配置**

  在 `layout/index.vue` 的 stores/refs 声明之后增加以下常量。图标以安全的内联 SVG 字符串沿用 `AppRail.vue` 的渲染方式，不请求后端：

  ```js
  const metrics = [
    {
      label: '覆盖省份', value: '28', unit: '个',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    },
    {
      label: '生成报告', value: '256', unit: '份',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 17h6" stroke-linecap="round"/></svg>',
    },
    {
      label: '测算项目数', value: '128', unit: '个',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z"/><path d="M4 7.5V16l8 5 8-5V7.5"/><path d="M12 12v9"/></svg>',
    },
  ]
  ```

- [ ] **Step 3: 将顶栏模板替换为品牌、指标、用户三段式结构**

  用以下内容替换现有 `<header class="ir-layout__topbar">` 的内部内容：

  ```vue
  <div class="ir-brand">
    <img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />
    <span class="ir-brand__name">{{ title }}</span>
    <span class="ir-brand__sub">ZRA · 储能投资投研助手</span>
  </div>
  <div class="ir-layout__metrics" aria-label="平台概览">
    <div v-for="metric in metrics" :key="metric.label" class="ir-layout__metric">
      <span class="ir-layout__metric-icon" v-html="metric.icon" aria-hidden="true" />
      <span class="ir-layout__metric-copy">
        <span>{{ metric.label }}</span>
        <strong class="xc-num">{{ metric.value }}<em>{{ metric.unit }}</em></strong>
      </span>
    </div>
  </div>
  <div class="ir-layout__user">
    <img class="ir-layout__avatar" :src="userAvatar" alt="" aria-hidden="true" />
    <span>{{ session.username || '访客' }}</span>
    <svg class="ir-layout__user-arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="m4 6 4 4 4-4" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </div>
  ```

- [ ] **Step 4: 以令牌和紧凑尺寸更新顶栏样式**

  将 `.ir-layout__topbar` 的高度替换为 `var(--xc-topbar-h)`；在其后新增以下规则：

  ```css
  .ir-layout__metrics { display: flex; align-items: center; height: 100%; }
  .ir-layout__metric { display: flex; align-items: center; gap: var(--xc-space-2); padding: 0 var(--xc-space-5); }
  .ir-layout__metric + .ir-layout__metric { border-left: 1px solid var(--xc-border-soft); }
  .ir-layout__metric-icon { display: grid; place-items: center; width: 18px; height: 18px; color: var(--xc-accent-blue); }
  .ir-layout__metric-icon :deep(svg) { width: 18px; height: 18px; }
  .ir-layout__metric-copy { display: flex; flex-direction: column; gap: 1px; color: var(--xc-text-mute); font-size: var(--xc-fs-3xs); line-height: var(--xc-lh-tight); }
  .ir-layout__metric-copy strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-semi); }
  .ir-layout__metric-copy em { margin-left: 2px; color: var(--xc-text-mute); font-size: var(--xc-fs-3xs); font-style: normal; }
  .ir-layout__user-arrow { width: 14px; height: 14px; color: var(--xc-text-mute); }
  @media (max-width: 960px) { .ir-layout__metrics { display: none; } .ir-brand__sub { display: none; } }
  ```

  同时将品牌名、标记和头像缩小到适配 52px 高度的可读尺寸；只使用现有间距、字号和颜色令牌。

- [ ] **Step 5: 添加历史面板测试锚点并令尺寸引用共享令牌**

  在 `AppSidebar.vue` 的 `<aside class="ir-sider">` 加入静态属性：

  ```vue
  <aside
    class="ir-sider"
    data-testid="history-sidebar"
  ```

  将外层样式的硬编码宽度替换为共享令牌：

  ```css
  .ir-sider { width: var(--xc-sidebar-w); }
  ```

  保留折叠态的 56px 宽度和悬浮展开逻辑；模板中不新增“查看全部历史会话”元素。

- [ ] **Step 6: 调整轨道与侧栏的视觉密度，不改变事件或路由代码**

  `AppRail.vue` 保持 `--xc-rail-w: 46px`、`onClick(it)`、`is-active`、`is-disabled`、tooltip 逻辑不变，仅将按钮边框、背景、激活光效和间距对齐参考图。

  `AppSidebar.vue` 保持 `new-chat`、`open-history`、`delete-history`、折叠、悬浮预览和 `hidden` 行为不变，仅使用现有 `--xc-*` 令牌微调面板内边距、头部、新建会话按钮和历史条目密度。把 `.ir-sider__new` 与 `.ir-rail-btn.is-active` 中的 `#fff` 改为 `var(--xc-text-inverse)`，把删除按钮 fallback `var(--xc-status-danger, #e95a4f)` 改为 `var(--xc-status-danger)`。

- [ ] **Step 7: 运行侧栏回归测试**

  在 `agent-frontend/` 目录运行：

  ```bash
  npm exec vitest -- run tests/layout-sidebar.spec.js
  ```

  预期：全部通过，包括 `history-sidebar` 测试锚点、无全历史入口和隐藏/展开事件。

- [ ] **Step 8: 不执行 Git 操作**

  所有顶栏和导航样式改动保持未暂存。

### Task 4: 重构欢迎态为左右分栏并接入主视觉

**Files:**
- Modify: `agent-frontend/src/views/home/index.vue:6-39,157-205,225-295`
- Modify: `agent-frontend/src/views/home/components/ChatComposer.vue:55-123`
- Test: `agent-frontend/tests/home-welcome.spec.js`

**Interfaces:**
- Consumes: `energyStorageHeroSrc` 静态资源、`calc.responding`、`examples`、`onSend(text)`。
- Produces: 仅欢迎态存在的 `.ir-welcome__energy-hero`，加载失败时设置 `hidden`，且示例指令继续调用 `onSend`。

- [ ] **Step 1: 导入主视觉并增加加载失败状态**

  在 `index.vue` 的现有资源导入后添加：

  ```js
  import energyStorageHeroSrc from '@/assets/home-energy-storage-hero.png'
  ```

  在 `scrollEl` 声明后添加：

  ```js
  const heroFailed = ref(false)

  function hideEnergyHero() {
    heroFailed.value = true
  }
  ```

- [ ] **Step 2: 将欢迎态模板替换为交互列和主视觉列**

  将当前 `.ir-welcome__inner` 内容替换为：

  ```vue
  <div class="ir-welcome__inner">
    <div class="ir-welcome__content">
      <img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />
      <h1 class="ir-welcome__hi">你好，我是朱雀投研智能体</h1>
      <p class="ir-welcome__lead">
        用一句话给出<strong>省份 · 容量 · 功率</strong>，我来完成储能项目的权威测算，
        并给出财务指标、收入结构与 15 年现金流。
      </p>
      <div class="ir-welcome__abilities" aria-label="能力范围">
        <span>项目测算</span><span>收益拆解</span><span>现金流分析</span>
      </div>
      <ChatComposer
        class="ir-welcome__composer"
        :responding="calc.responding"
        placeholder="描述你的储能项目，例如：测算甘肃 200MW/800MWh 独立储能项目"
        @send="onSend"
      />
      <div class="ir-welcome__chips">
        <button
          v-for="eg in examples"
          :key="eg"
          class="ir-chip"
          :disabled="calc.responding"
          @click="onSend(eg)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
            <path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" />
          </svg>
          <span>{{ eg }}</span>
        </button>
      </div>
    </div>
    <div v-if="!heroFailed" class="ir-welcome__visual" aria-hidden="true">
      <img class="ir-welcome__energy-hero" :src="energyStorageHeroSrc" alt="" @error="hideEnergyHero" />
    </div>
  </div>
  ```

  恢复注释位置的当前示例按钮循环，不改变 `examples` 内容、`:disabled="calc.responding"` 或 `@click="onSend(eg)"`。

- [ ] **Step 3: 用分栏 CSS 替换居中欢迎态 CSS**

  用以下布局原则替换 `.ir-welcome` 到 `.ir-chip svg` 的欢迎态规则：

  ```css
  .ir-welcome { flex: 1 1 auto; display: flex; min-height: 0; padding: var(--xc-space-8) var(--xc-space-9); }
  .ir-welcome__inner { display: grid; grid-template-columns: minmax(0, 1fr) minmax(420px, 0.9fr); align-items: center; width: min(1180px, 100%); margin: 0 auto; }
  .ir-welcome__content { position: relative; z-index: 1; max-width: 680px; text-align: left; }
  .ir-welcome__visual { position: relative; min-height: 520px; pointer-events: none; }
  .ir-welcome__energy-hero { position: absolute; top: 50%; left: 50%; width: min(720px, 54vw); max-width: none; transform: translate(-50%, -50%); mix-blend-mode: screen; }
  ```

  保留球体浮动动画、渐变标题、示例按钮和发送禁用状态。将文本、能力标签、输入框和胶囊左对齐；用 `var(--xc-grad-brand-h)` 形成标题和能力标签的渐变字效果。不要在 CSS 中添加任何 `#`、`rgb` 或 `rgba` 新颜色字面量。

- [ ] **Step 4: 添加窄屏退让规则**

  在欢迎态 CSS 后新增：

  ```css
  @media (max-width: 1100px) {
    .ir-welcome__inner { grid-template-columns: minmax(0, 1fr) minmax(320px, 0.65fr); }
    .ir-welcome__energy-hero { width: min(600px, 55vw); }
  }
  @media (max-width: 760px) {
    .ir-welcome { padding: var(--xc-space-6) var(--xc-space-4); overflow-y: auto; }
    .ir-welcome__inner { grid-template-columns: 1fr; }
    .ir-welcome__content { max-width: none; }
    .ir-welcome__visual { min-height: 260px; order: -1; }
    .ir-welcome__energy-hero { width: min(560px, 100vw); }
    .ir-welcome__chips { justify-content: flex-start; }
  }
  ```

- [ ] **Step 5: 只调整 `ChatComposer` 外观，保持组件 API**

  保持 props、`emit('send', v)`、Enter/Shift+Enter、spinner 和禁用逻辑不变。使用现有令牌将 `ChatComposer.vue` 的 `.ir-composer__frame` 最小高度调整为 `156px`、圆角调整为 `var(--xc-radius-xl)`；将 `.ir-composer__send` 调整为 `54px` 正方形。将 `#fff` 替换为 `var(--xc-text-inverse)`，不添加线性渐变或硬编码颜色。

- [ ] **Step 6: 运行欢迎态回归测试**

  在 `agent-frontend/` 目录运行：

  ```bash
  npm exec vitest -- run tests/home-welcome.spec.js
  ```

  预期：主视觉层存在，点击 mock 的示例发送按钮后仍调用 `calc.sendAndCalculate('测算甘肃 200MW/800MWh 独立储能项目')`。

- [ ] **Step 7: 不执行 Git 操作**

  保持视图、输入框和测试改动在工作区。

### Task 5: 完整回归、构建与视觉核验

**Files:**
- Verify: `agent-frontend/src/assets/home-energy-storage-hero.png`
- Verify: `agent-frontend/src/design-system/tokens.css`
- Verify: `agent-frontend/src/layout/index.vue`
- Verify: `agent-frontend/src/layout/components/AppRail.vue`
- Verify: `agent-frontend/src/layout/components/AppSidebar.vue`
- Verify: `agent-frontend/src/views/home/index.vue`
- Verify: `agent-frontend/src/views/home/components/ChatComposer.vue`
- Verify: `agent-frontend/tests/home-welcome.spec.js`
- Verify: `agent-frontend/tests/layout-sidebar.spec.js`

**Interfaces:**
- Consumes: 前四个任务的资源、样式、模板和测试契约。
- Produces: 经测试、生产构建和人工视觉检查验证的首页欢迎态。

- [ ] **Step 1: 运行完整前端测试套件**

  在 `agent-frontend/` 目录运行：

  ```bash
  npm run test
  ```

  预期：全部 `tests/**/*.spec.js` 通过；若有既存失败，记录测试文件和实际失败输出，不能将其归为本次改动已通过。

- [ ] **Step 2: 构建生产包**

  在 `agent-frontend/` 目录运行：

  ```bash
  npm run build
  ```

  预期：Vite 构建完成，没有 Vue 模板、静态资源或未解析导入错误。

- [ ] **Step 3: 在基准视口做人工欢迎态核验**

  启动本地开发服务后，在 `1618 x 972` 视口检查：

  ```text
  - 顶栏约为 52px，高度明显低于改造前的 64px。
  - 中部可见覆盖省份 28 个、生成报告 256 份、测算项目数 128 个。
  - 左侧轨道与历史会话面板不遮挡顶栏或主区。
  - 页面没有“查看全部历史会话”文字、链接或预留空间。
  - 欢迎态左列包含球体、标题、说明、能力标签、输入框和示例胶囊。
  - 右列包含集装箱、数据面板、发光底座和输电塔，深色底通过 screen 融入工作台。
  - 主视觉不覆盖输入框、历史面板或顶栏；窄屏下输入框仍可访问。
  ```

- [ ] **Step 4: 验证会话态未回归**

  使用一个现有历史会话或成功发送一次示例指令，确认欢迎态切换后仍可见既有消息流、`ResultCard`、底部 `ChatComposer`、版本记录、报告记录和报告跳转入口。若开发后端不可用，则记录该限制，并以 Vitest 的发送断言作为行为覆盖证据。

- [ ] **Step 5: 仅进行非 Git 的最终检查**

  使用编辑器变更列表核对：改动仅限本计划的前端资源、样式、组件、测试和设计/计划文档。不得运行任何 `git` 命令。
