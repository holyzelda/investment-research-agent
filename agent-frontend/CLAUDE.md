# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

## 项目概述

"朱雀投研智能体"（ZRA-3）前端 —— 统一平台的子应用。前端使用 ecenter 登录、`getInfo` 获取用户资料与动态菜单，并保留其 Bearer Token。IR 业务请求还必须携带固定 `userId` / `username` Header：本地由请求拦截器转发 ecenter 已解析身份，测试/生产由可信网关注入或覆盖同名 Header；`username` 需 URL 编码为 ASCII。不得在业务请求体/query 中传递身份，不得伪造访客身份。

技术栈：Vue 3 + Vite 5 + Element Plus + Pinia + Vue Router 4 + ECharts 5（通过 vue-echarts）+ Tailwind（仅布局工具类，已关闭 `preflight`）+ "玄策（XC）"设计体系（深色优先，基于 CSS 自定义属性）。

## 常用命令

包管理器**统一用 npm**。使用 Node.js v20.12.1（对应 npm 10.5.0）；`package-lock.json` 必须保持提交。开发初始化与 CI 使用 `npm ci`，新增或移除依赖时使用 `npm install` / `npm uninstall` 并同步提交 `package.json` 与 `package-lock.json`。

```bash
npm ci                 # 按 package-lock.json 安装依赖
npm run dev            # 启动开发服务器 http://localhost:5210
npm run build          # 生产构建 -> dist/
npm run build:staging  # 以 --mode staging 构建（加载 .env.staging）
npm run preview        # 本地预览构建产物
npm test               # 运行全部测试（一次性，vitest run）
npm run test:watch     # vitest watch 模式
```

运行单个测试文件：`npm exec vitest -- run tests/calc-flow.spec.js`
按名称运行单个测试：`npm exec vitest -- run -t "polls a non-terminal task"`

测试文件位于 `tests/*.spec.js`（不与源码同目录），使用 `vitest` + `@vue/test-utils` + `jsdom`，通过 `vite.config.js` 中的 `test.include` 进行匹配。

## 开发代理 / 后端联调

所有 API 请求都经由 `VITE_APP_BASE_API`（默认 `/gateway/ir-agent/`，在 `.env` 中配置）。开发环境下 Vite 会把该前缀代理到本地后端：

```
浏览器 → /gateway/ir-agent/ir/me → （vite 代理，去除前缀）→ http://127.0.0.1:9089/ir/me
```

如需覆盖代理目标，在本地 `.env.local`（已在 `.gitignore` 中忽略）中设置 `VITE_DEV_BACKEND`，**不要**为了个人后端端口去改已提交的 `.env*` 文件。开发环境下需单独启动后端（`uvicorn ...`），否则 API 请求无法解析。

`.env*` 仅保存前端构建与代理配置：`VITE_APP_BASE_API`、`VITE_APP_TITLE`、`VITE_FAVICON`、`VITE_APP_ENV`、`VITE_DEV_BACKEND`、`VITE_ECENTER_BACKEND`、`VITE_GATEWAY_BACKEND`。真实凭据不得提交到 env 文件；后端业务配置也不得出现在前端 env 中。

## 架构说明

### 请求/响应契约
`src/utils/request.js` 用 axios 封装了固定的后端响应壳：每个响应体都是 `{code, msg, data}`。拦截器在 `code === 200` 时解包出 `data`，其余情况弹出 `ElMessage.error` 并 reject；`code === 401` 被视为"平台会话问题"（不是前端可自行处理的鉴权状态，只提示用户返回平台重新进入）。二进制响应（`responseType: 'blob'|'arraybuffer'`）绕过该响应壳。各接口模块（`src/api/*.js`）都是对 `request({...})` 的薄封装。

### 登录、路由与身份
`src/router/index.js` 提供登录页与业务首页，`src/permission.js` 负责 ecenter 菜单和动态路由。`store/modules/session.js` 从 ecenter `getInfo` 归一化并缓存 `userId` / `username`；请求层仅向 IR 业务接口添加这两个 Header，绝不向 `/gateway/ecenter/**`、`/gateway/code` 等 ecenter/验证码接口发送。用户名 Header 使用 URL 编码；身份缺失不降级为“访客”，应由后端返回 401。

### 状态管理：两个 Pinia store
- `store/modules/session.js` —— 保存 ecenter 当前用户（`userId`/`username`）和 Token；登录后通过 ecenter `getInfo` 加载并缓存身份，供请求层传递给 IR 后端。
- `store/modules/calculation.js` —— 核心业务 store，驱动整个"对话 → 测算"流程：
  - `messages`：有序对话记录；实时主链使用 `kind: 'assistant-stream'` 原地承载思考链、打字答案和内嵌结果卡，历史恢复仍使用静态 `text` / `result`。消息顺序只增不改，选择不同版本不会重排消息流。
  - `versions`：某会话下已完成的测算结果（`V1`、`V2`……），可通过 `selectedVersion`/`selectVersion` 独立于对话流选中。
  - `sendAndCalculate(text)`：不在前端解析或校验测算参数，原样调用 `POST /ir/chat/diag`。`thinking` 实时更新节点链；`answer` 文本先缓冲，`done` 后打字输出；命中 `create_calculation_task` 后按 `taskId` 拉取结果并渲染现有 `ResultCard`，结果卡不等待打字完成。
  - 流式生命周期：单活跃回合通过回合令牌隔离异步回调；`done`、`error`、停止和异常 EOF 统一收束。响应期间 Composer 提供停止按钮，首页强制自动滚动；推荐问题在答案打字结束后展示。
  - `recalculate()` 是例外：参数调整继续直调 `/ir/calc/tasks`、轮询终态并拉结果，但复用同款思考进度和失效保护。
  - 会话延续：一旦存在 `conversationId`，后续 `/ir/chat/diag` 请求体带 `conversation_id`；切换历史会话或新建会话会先终止旧流。
  - 历史侧栏（`listConversations`/`getConversation`/`deleteConversation`）：用户从 `AppSidebar` 重新打开历史会话时，根据详情重建 `messages`/`versions`，快速切换通过请求序号避免旧响应覆盖新会话。

### 视图结构
- `layout/index.vue` + `layout/components/AppSidebar.vue`：整体外壳 —— 侧边栏（新建会话、4 个导航项中有 3 个是 `disabled` 的占位项，对应后续 PRD 中的三大模块：全国指数地图/联络线地图/政策与市场）、带删除确认的历史会话列表、顶栏（品牌 + 当前用户）。
- `views/home/index.vue`：唯一的实际页面。同一模板下有两种状态：无会话时的居中"欢迎态"布局（光球图形、引导文案、输入框、示例提示胶囊）；有会话时的对话态布局（可滚动消息流 + 右侧 300px 版本记录栏）。点击版本记录栏中的某一项会把对应结果卡片滚动进视口并切换高亮样式 —— 不会重新拉取数据或重排消息。
- `views/home/components/ResultCard.vue`：把测算结果组织为文档中约定的三个部分：`①基本信息`（`BasicInfoBlock`）、`②财务指标`（`FinancialBlock`，固定 5 项 KPI）、`③进阶图形结果`（`RevenueDonut` + `DebtServiceCoverage`）。最新版本的结果卡还承载参数重新测算：`ParamAdjustPanel` 维护基础参数临时值，`AdvancedParamDialog` 暂存高级参数草稿；点击基础面板的“重新测算”时合并提交，弹窗自身不创建测算任务。高级参数是否可编辑必须由后端字典的 `control`、`g` 与冻结入参决定，不在前端写入经营年限、换电成本或中长期电价的业务判断。报告生成经报告任务 SSE 推进，等待阶段复用 `ThinkingChain`，成功/失败提示与测算回答统一使用 `AiAnswerContent`；正式报告页的 AI 分析也复用同一内容组件，同时保留 A4 文档外层布局。
- `views/home/components/DebtServiceCoverage.vue`：偿债倍数折线图，数据契约 `advanced.debtServiceCoverage.cashflowRatio`（`Array<number|null>`，`null` 为断点，取自飞书 `画图数据` 区）。Y 轴不是线性轴，而是把真实倍数映射到“显示坐标”的分段轴（`0–1` 每格 0.5、`>1` 每格 0.2，视觉等高），轴标签与 tooltip 通过反映射函数还原真实值——改这个图前先读组件内 `toDisplayValue`/`toRatioValue`。警戒线固定在真实值 `1.0`（显示坐标 `2`）；蓝色安全余量通过一条静默辅助 `line` series（clamp 到警戒线、`areaStyle.origin` 锚定）实现，只在真实值高于 1.0 时出现在“警戒线到折线之间”，不是整块背景矩形。
- `views/home/composables/useEcharts.js`：共享的图表生命周期封装（挂载时 `init`，任意响应式依赖变化时通过 `watch(optionFactory, ..., {deep: true})` 触发 `setOption(..., true)`，监听 resize，卸载时 dispose）。图表组件传入的是一个返回 option 的工厂函数，而非静态 option。`xcChartColors()`/`xcVar()` 会从当前计算出的 CSS 自定义属性（`--xc-chart-1..8` 等）实时读取分类色/语义色，使图表跟随主题变化而非写死十六进制颜色。

### 参数调整契约
- 后端参数字典是参数调整 UI 的唯一元数据来源；前端通过 `paramDict` 的 `zone`、`control`、`step`、`min`、`max`、`g` 以及冻结 `seedInput` 决定展示、精度、范围和可编辑性。
- `ParamAdjustPanel.vue` 仅保留项目、金融和常规收益边界字段；高级字段由 `AdvancedParamDialog.vue` 按金融/收益/成本区展示。`operation_years` 只在高级弹窗按字典 `control: 'select'` 和 `options` 渲染为 15/20 年下拉，不要硬编码选项或放回 inline 面板。高级参数先保存到当前 `ResultCard` 的草稿，再由基础面板的“重新测算”合并为一次 `calc.recalculate()` 请求；运营期值保持 number 并走 `param_overrides.operation_years`。
- `src/utils/paramAdjust.js` 负责分区、覆盖值组装、动态范围和按 `step` 的精度处理；数值显示仍统一使用 `src/utils/formatNumber.js`，不要在组件中直接 `toFixed`。
- 项目信息卡的只读/可编辑展示遵循同一左侧强调标记样式；可编辑容量/功率须保留参数字典的单位，且以轻量数字编辑形式展示。

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
