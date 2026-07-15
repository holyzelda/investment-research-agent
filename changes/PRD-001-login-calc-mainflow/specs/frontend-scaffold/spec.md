# 能力规格：frontend-scaffold（前端基座）

> 来源：PRD 技术定位 / §3；US-0.1（2026-07-04 变更）。**全新 Vue3 工程 + XC 设计体系 + 通用框架层**，无独立登录页，落地对话首页，视觉对齐 trader/平台。

## ADDED Requirements

### Requirement: 全新 Vue3 工程与通用框架层

The system SHALL 在 `agent-frontend/` 下新建 Vite + Vue 3 工程，技术栈版本对齐 trader（Vue 3.3.x / Element Plus 2.4.x / Pinia / Vue Router / Vite / ECharts 5 / Tailwind 3.4 / vue-slider-component / nprogress），并具备通用框架层：axios 请求实例（按 `{code,msg,data}` 解析、统一错误提示、可注入平台身份头透传）、`layout/` 主布局、路由、通用组件与 svg-icon。**无独立登录页、无登录路由守卫、无用户/权限模块**。

#### Scenario: 依赖与构建对齐

- **WHEN** 在 `agent-frontend/` 执行安装与 `dev`
- **THEN** 应用可启动，`package.json` 的 vue/element-plus/pinia/vue-router/echarts/tailwindcss/vue-slider-component 主版本与 trader 一致

#### Scenario: 无登录/用户/权限代码

- **WHEN** 走查前端源码与路由表
- **THEN** 不存在登录页、注册、验证码、用户管理、权限守卫代码；入口路由直达对话首页

### Requirement: 平台承接落地对话首页

The system SHALL 以"对话首页"为默认落地页，承接来自平台首页的跳转入口；应用启动即进入对话工作台，不经过任何本系统登录环节。

#### Scenario: 落地对话首页

- **WHEN** 从平台入口 URL 打开本系统
- **THEN** 直接呈现对话首页工作台

### Requirement: XC 玄策设计体系接入

The system SHALL 引入 `src/design-system/`（`tokens.css`、`design-system.md`、`element-plus-overrides.scss`、`CHARTS.md`），全局挂载 `--xc-*` token 与 Element Plus 覆盖样式，页面/组件通过 `var(--xc-*)` 与 `.xc-*` 书写，禁止内联 hex；图表配色遵循 CHARTS.md 硬约束（红涨绿跌）。

#### Scenario: token 生效

- **WHEN** 应用以根 class `xc-app` 渲染
- **THEN** 深色基线（暖灰 `rgb(36,36,36)`）与 `--xc-*` 变量生效，Element Plus 组件呈现 XC 覆盖样式

### Requirement: 朱雀品牌化与平台观感统一

The system SHALL 以"朱雀投研智能体"品牌配置系统名/副标题/favicon，界面视觉与 trader/平台统一（XC 玄策体系），不出现异构风格。

#### Scenario: 品牌与风格

- **WHEN** 打开对话首页
- **THEN** 展示"朱雀投研智能体"品牌，视觉风格与平台一致

### Requirement: 配置分层（前端仅网关基地址）

The system SHALL 通过 `.env.*` 仅配置 `VITE_APP_BASE_API`（网关基地址，路由到后端 `/ir`）、`VITE_APP_TITLE`、`VITE_FAVICON`、`VITE_APP_ENV`，区分开发/测试/生产；不在前端硬编码后端地址或业务配置。

#### Scenario: 环境切换

- **WHEN** 以 staging/生产模式构建
- **THEN** 应用使用对应 `.env` 的 `VITE_APP_BASE_API` 与标题/favicon，无需改动源码
