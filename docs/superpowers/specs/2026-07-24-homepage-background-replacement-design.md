# 首页欢迎态全局背景图设计

**日期：** 2026-07-24（2026-07-24 修订：范围由 Home 局部背景改为全局 layout 底层）
**范围：** `agent-frontend` 首页无会话欢迎态的全局外壳背景

## 目标

使用用户提供的深色科技底图（源：`D:\0_工作\2026\投研智能体\报告模块\首页v1.png`）作为首页欢迎态铺满整个外壳的最底层背景，位于顶栏与悬浮 rail / 历史侧栏的下层，同时保留 XC 设计语言的青/紫氛围色。

## 背景与修订说明

- 初版曾把背景放在 `Home` 组件的欢迎容器内（`.ir-welcome__background`），只能覆盖主视图区域，无法延伸到左侧悬浮导航与顶栏下层，且旧的透明 PNG 实为无 Alpha 的 RGB 图，`object-fit: cover` 会遮盖 XC 氛围色。
- 修订后：背景层上移到全局外壳 `src/layout/index.vue`，铺满 `.ir-layout`（100vh）；新图同为 RGB，但在图片之上叠一层半透明 `var(--xc-grad-atmosphere)` 渐变，使 XC 设计语言色重新透出。

## 范围与非目标

- 仅在 `route.name === 'Home'` 且 `calc.messages.length === 0`（首页无会话欢迎态）显示。
- 用户发送首条消息进入对话态、打开历史会话、进入报告页 / 联络线页后不渲染该背景。
- 不改变欢迎态标题、引导文案、能力标签、输入框、示例胶囊的结构、位置、尺寸或间距。
- 不改动 `AppRail`、`AppSidebar` 的样式或透明度；不新增依赖、接口或状态。

## 视觉与层级

- 将源图复制为前端静态资源 `src/assets/home-welcome-background.png`，由 layout 通过 `import` 让 Vite 指纹化。
- 背景层为 `.ir-layout` 的直接子元素，绝对定位 `inset: 0`、`z-index: 0`、`pointer-events: none`。
- 图片通过 CSS 变量 `--ir-welcome-bg` 注入，背景合成为 `var(--xc-grad-atmosphere), var(--ir-welcome-bg) center / cover no-repeat`：氛围渐变为首层（叠加在上），图片为底层（cover 铺满、允许边缘裁切）。
- 顶栏 `.ir-layout__topbar` 与主体 `.ir-layout__body` 升为 `position: relative; z-index: 1`，浮于背景之上；rail/sidebar 仍靠自身 `backdrop-filter` 让下层图片自然透显。
- `.ir-layout::before`（`z-index: -1` 的常驻氛围渐变）保留，作为非欢迎态时的基础氛围。

## 颜色与设计体系约束

- 组件样式禁止新增内联 hex/rgb/rgba，一律使用 `var(--xc-*)`；图片 URL 经绑定的 CSS 变量注入。
- 复用既有 token：`--xc-surface-workspace`、`--xc-grad-atmosphere`、`--xc-z-nav` 等。

## 验收与测试

- 首页无会话欢迎态：全局背景层 `.ir-layout__welcome-backdrop` 渲染、`aria-hidden="true"`、通过 `--ir-welcome-bg` 注入图片。
- 存在会话时：背景层不渲染。
- 非首页路由（报告详情 / 联络线）：背景层不渲染。
- `Home` 组件不再渲染局部背景 `.ir-welcome__background`。
- 欢迎态文案、输入框、示例胶囊布局与交互不变。
- 新增 `tests/layout-welcome-backdrop.spec.js` 覆盖上述条件；更新 `tests/home-welcome.spec.js` 断言 Home 不再承载局部背景。
