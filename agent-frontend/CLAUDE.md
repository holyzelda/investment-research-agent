# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

## 项目概述

"朱雀投研智能体"（ZRA-3）前端 —— 统一平台的子应用。**无独立登录**：用户在平台首页完成登录后跳转承接落地本系统；身份由平台/网关注入后端请求头，前端不管理任何登录 token。

技术栈：Vue 3 + Vite 5 + Element Plus + Pinia + Vue Router 4 + ECharts 5（通过 vue-echarts）+ Tailwind（仅布局工具类，已关闭 `preflight`）+ "玄策（XC）"设计体系（深色优先，基于 CSS 自定义属性）。

## 常用命令

包管理器**统一用 pnpm** —— `preinstall` 会执行 `only-allow pnpm`，用 `npm install` 会被有意拦截报错。

```bash
pnpm install          # 安装依赖（pnpm-lock.yaml 必须保持提交）
pnpm dev               # 启动开发服务器 http://localhost:5210
pnpm build              # 生产构建 -> dist/
pnpm build:staging      # 以 --mode staging 构建（加载 .env.staging）
pnpm preview             # 本地预览构建产物
pnpm test                 # 运行全部测试（一次性，vitest run）
pnpm test:watch            # vitest watch 模式
```

运行单个测试文件：`pnpm vitest run tests/calc-flow.spec.js`
按名称运行单个测试：`pnpm vitest run -t "polls a non-terminal task"`

测试文件位于 `tests/*.spec.js`（不与源码同目录），使用 `vitest` + `@vue/test-utils` + `jsdom`，通过 `vite.config.js` 中的 `test.include` 进行匹配。

## 开发代理 / 后端联调

所有 API 请求都经由 `VITE_APP_BASE_API`（默认 `/gateway/`，在 `.env` 中配置）。开发环境下 Vite 会把该前缀代理到本地后端：

```
浏览器 → /gateway/ir/me → （vite 代理，去除前缀）→ http://127.0.0.1:9089/*
```

如需覆盖代理目标，在本地 `.env.local`（已在 `.gitignore` 中忽略）中设置 `VITE_DEV_BACKEND`，**不要**为了个人后端端口去改已提交的 `.env*` 文件。开发环境下需单独启动后端（`uvicorn ...`），否则 API 请求无法解析。

`.env*` 系列文件有意只保留 4 项配置：`VITE_APP_BASE_API`、`VITE_APP_TITLE`、`VITE_FAVICON`、`VITE_APP_ENV`。任何后端业务配置都不应出现在前端 env 中。

## 架构说明

### 请求/响应契约
`src/utils/request.js` 用 axios 封装了固定的后端响应壳：每个响应体都是 `{code, msg, data}`。拦截器在 `code === 200` 时解包出 `data`，其余情况弹出 `ElMessage.error` 并 reject；`code === 401` 被视为"平台会话问题"（不是前端可自行处理的鉴权状态，只提示用户返回平台重新进入）。二进制响应（`responseType: 'blob'|'arraybuffer'`）绕过该响应壳。各接口模块（`src/api/*.js`）都是对 `request({...})` 的薄封装。

### 无鉴权/无路由守卫
`src/router/index.js` 只有一个真实路由（`/home`，`/` 重定向到它）加一个兜底重定向。没有登录路由，没有路由守卫，没有 token 刷新逻辑 —— 这一点由 `tests/scaffold.spec.js` 强制校验（断言不存在 `login|register|captcha` 相关路径/路由名）。不要在此处新增鉴权脚手架；身份信息来自 `useSessionStore().loadUserInfo()` 请求 `/ir/me`，若平台请求头缺失（本地开发下预期如此，对应后端 `allow_anonymous`），会降级为"访客"占位。

### 状态管理：两个 Pinia store
- `store/modules/session.js` —— 仅保存当前用户（`userId`/`username`），从 `/ir/me` 加载一次。刻意没有 login/logout 相关 action。
- `store/modules/calculation.js` —— 核心业务 store，驱动整个"对话 → 测算"流程：
  - `messages`：有序对话记录（`{id, role, kind: 'text'|'result', text|result, version}`）。消息顺序只增不改，选择不同版本**不会**重排消息流（见 `tests/version-list.spec.js`）。
  - `versions`：某会话下已完成的测算结果（`V1`、`V2`……），可通过 `selectedVersion`/`selectVersion` 独立于对话流选中 —— 选中某版本会在（顺序不变的）消息流中高亮对应卡片，而不是重新排序。
  - `extractMinInput(text)`：不依赖 NLP，通过正则从自由文本中轻量提取 省份（对照硬编码的 `PROVINCES` 全称/简称表）、功率 MW、容量 MWh。字段缺失时会用中文提示补充，并阻止提交 —— 这就是这个对话式 UI 的全部"表单"逻辑。
  - `sendAndCalculate(text)`：推入用户消息 → 校验提取出的输入 → 创建任务（`POST /ir/calc/tasks`）→ 若未立即终态则每 1 秒轮询一次 `getCalculationTask`，最多 60 次 → 完成后拉取完整结果（`GET /ir/calc/tasks/:id/result`），并**原地修改**那条待定的助手消息（`kind` 从 `'text'` 变为 `'result'`），而不是新推入一条 → 刷新侧边栏历史列表（尽力而为，自行吞掉异常）。
  - 会话延续：一旦存在 `conversationId`，后续 `sendAndCalculate` 调用会在请求体中带上它，使后端能把新版本挂载到同一会话下。
  - 历史侧栏（`listConversations`/`getConversation`/`deleteConversation`）：用户从 `AppSidebar` 重新打开某个历史会话时，会根据拉取到的会话详情重建完整的 `messages`/`versions` 数组。

### 视图结构
- `layout/index.vue` + `layout/components/AppSidebar.vue`：整体外壳 —— 侧边栏（新建会话、4 个导航项中有 3 个是 `disabled` 的占位项，对应后续 PRD 中的三大模块：全国指数地图/联络线地图/政策与市场）、带删除确认的历史会话列表、顶栏（品牌 + 当前用户）。
- `views/home/index.vue`：唯一的实际页面。同一模板下有两种状态：无会话时的居中"欢迎态"布局（光球图形、引导文案、输入框、示例提示胶囊）；有会话时的对话态布局（可滚动消息流 + 右侧 300px 版本记录栏）。点击版本记录栏中的某一项会把对应结果卡片滚动进视口并切换高亮样式 —— 不会重新拉取数据或重排消息。
- `views/home/components/ResultCard.vue`：把测算结果组织为文档中约定的三个部分：`①基本信息`（`BasicInfoBlock`）、`②财务指标`（`FinancialBlock`，固定 5 项 KPI）、`③进阶图形结果`（`RevenueDonut` + `CashflowLines`）。全局各处的"生成报告"按钮都是有意的占位（`ElMessage.info('报告功能将在后续开放')`）——在没有对应后端契约前不要接线；同理"调整参数并重新测算"按钮处于 `disabled` 状态，等待"Batch 5"。
- `views/home/composables/useEcharts.js`：共享的图表生命周期封装（挂载时 `init`，任意响应式依赖变化时通过 `watch(optionFactory, ..., {deep: true})` 触发 `setOption(..., true)`，监听 resize，卸载时 dispose）。图表组件传入的是一个返回 option 的工厂函数，而非静态 option。`xcChartColors()`/`xcVar()` 会从当前计算出的 CSS 自定义属性（`--xc-chart-1..8` 等）实时读取分类色/语义色，使图表跟随主题变化而非写死十六进制颜色。

### 设计体系（玄策/XC）
`src/design-system/tokens.css` 是**移植而非自有**的文件（从同系列的 `etrader-agent-nx` 项目移植过来，以与平台整体视觉保持一致）——具体已移植/待补充内容见 `src/design-system/README.md`（`element-plus-overrides.scss`、`design-system.md`、`CHARTS.md` 会在"按需"时再引入）。约定：
- 深色优先：`:root` 定义深色调色板；`:root[data-theme="light"]` 仅用于可打印报告/高管视图等场景的覆盖。
- **组件样式中禁止内联 hex/rgb 颜色**，一律使用 `var(--xc-*)`。
- 根应用节点需带 `xc-app` class 以启用该视觉基线；数字类展示统一用 `.xc-num` 工具类（等宽数字、数字专用字体）。
- 涨跌配色遵循中国行情习惯：红涨绿跌（`--xc-trade-up`/`--xc-trade-down`），与通用的 `--xc-status-ok/warn/danger` 语义色是两套体系，不要混用。
- Tailwind 仅作布局/工具类使用（`corePlugins.preflight: false`），目的正是避免与 Element Plus 及 XC token 冲突 —— 不要使用 Tailwind 的颜色类。

### 自动导入
`vite.config.js` 中配置了 `unplugin-auto-import` + `unplugin-vue-components`，并使用 `ElementPlusResolver()` —— Element Plus 组件以及常用 Vue API（如 `ref`、`computed` 等，按该插件默认配置）在 `.vue` 文件中可以免显式 import 直接使用。但现有代码大多数地方仍显式 import 了 Vue API；具体某个文件里怎么写的就跟着它的风格走，不要在同一文件内混用两种风格。

### 格式化工具函数
`src/utils/formatNumber.js` 是数值展示的唯一入口：`formatNumber(value, decimals=2)` 对 null/undefined/空字符串返回 `'—'`，整数不补零，其余按固定小数位显示；`formatPrice` 即 `formatNumber` 取 4 位小数（用于元/kWh 单价展示）。应统一使用这些函数而非临时手写 `toFixed`/模板拼接，以保证空值/加载态的展示一致。
