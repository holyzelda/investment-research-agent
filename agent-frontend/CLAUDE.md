# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

先读仓库根 `CLAUDE.md` 获取身份、响应壳、飞书和快照等跨端约束。本文件只描述 `agent-frontend/` 的实际实现。

## 常用命令

从 `agent-frontend/` 执行。项目要求 Node.js `>=20.12.1`、npm `>=10.5.0`，包管理器固定为 npm；`package-lock.json` 必须与依赖变更同步。

```bash
npm ci                 # 按 lockfile 安装
npm run dev            # Vite，访问 http://localhost:5210/investment/
npm run build          # 生产构建
npm run build:staging  # vite build --mode staging
npm run preview        # 预览构建产物
npm test               # vitest run
npm run test:watch     # Vitest watch

npm exec vitest -- run tests/calc-flow.spec.js
npm exec vitest -- run tests/calc-flow.spec.js -t "publishes each thinking frame reactively before done"
```

测试匹配 `tests/**/*.spec.js`，环境为 jsdom。当前没有 lint script，也没有 ESLint/Prettier 配置；不要虚构 lint 命令。

## 开发服务器与代理

- Vite `base` 是 `/investment/`，`@` 指向 `src/`。
- `VITE_APP_BASE_API` 默认 `/gateway/ir-agent/`；开发代理去掉此前缀后转发到 `VITE_DEV_BACKEND`，默认 `http://127.0.0.1:9089`。
- `/gateway/ecenter/` 和其他 `/gateway/` 平台接口转发到对应平台网关。个人代理覆盖写入被忽略的 `.env.local`，不要为了本地端口修改已提交的 `.env*`。

## 应用结构

`index.html → src/main.js → App.vue → router-view`。`main.js` 注册 Pinia、Router、Element Plus，并加载 XC 全局样式和报告打印样式；`src/permission.js` 完成 Token 承接、用户资料加载及后端菜单动态路由注册。

`src/router/index.js` 中的页面都已实现：

- `/login`：ecenter 登录；也支持平台窗口或 URL 传入 Token。
- `/home`：对话、思考链、测算结果、参数调整、版本和报告记录。
- `/index-map`：全国储能投资指数地图、排名与省级详情。
- `/tie-line`：联络线地图、筛选、详情和功率趋势。
- `/policy-market`：政策咨询历史/提交与市场资讯。
- `/reports/:reportId`：独立 A4 正式报告页面；浏览器打印前由 `views/report/utils/paginateReport.js` 分页并等待字体、图表快照。

主要 Pinia stores 位于 `src/store/modules/`：`session` 管理 ecenter 身份，`permission` 管理动态菜单，`calculation` 驱动对话/测算/报告，`indexMap`、`tieLine`、`policyMarket` 管理各自页面。长请求和页面切换普遍使用 turn/epoch/request-version 防止旧异步响应覆盖新状态，新增异步流程时复用该模式。

## 请求与流式契约

- `src/utils/request.js` 的成功返回值是完整 `{code, msg, data}`，**不会自动解包 `data`**；API 模块或调用方需按现有模式读取。`blob` / `arraybuffer` 直接返回二进制。
- IR 请求附加 Bearer Token、`userId` 和 URL 编码后的 `username`；`/gateway/code`、`/gateway/ecenter/**` 不附加 IR 身份。401 会清理本地 Token/身份、记录需登录状态并弹出重新登录确认。
- 对话使用 `src/utils/chatSse.js`；报告进度使用 `src/utils/reportSse.js`。流结束必须处理 `done`、显式错误、用户 abort 和异常 EOF，并保持当前 turn/conversation 的失效保护。
- 对话工具产生测算任务后可预取结果，但结果卡只在 `done` 后发布。消息和版本保持追加顺序，选中版本只定位既有结果，不重排消息。

## 参数与报告

- `src/utils/paramAdjust.js` 根据后端参数字典的 `zone`、`control`、`step`、`min/max`、`g`、`options` 和冻结入参控制展示与覆盖值；不要在组件中另建参数规则。`operation_years` 保持 number，并按字典 options 渲染。
- 同一会话内 province 固定；重新测算由基础面板合并高级参数草稿后一次提交。
- 正式报告从 `/ir/reports/:reportId` 的快照数据渲染，不重新测算。图表在打印前转换为 PNG，打印样式只作用于报告文档。

## 图表与样式

- 图表直接使用 `echarts`；虽然依赖中存在 `vue-echarts`，源码没有使用它。Home/报告图表优先复用 `src/views/home/composables/useEcharts.js` 的 init、响应式 setOption、resize、dispose 和渲染回调。
- 中国地图由本地 `src/assets/geo/china.json` 注册；指数地图使用 SVG renderer，联络线地图使用 Canvas，修改时保持各自实现。
- XC token 位于 `src/design-system/tokens.css`，应用根节点使用 `xc-app`，数字展示复用 `.xc-num`。业务色优先使用 `var(--xc-*)` 或运行时读取 token；涨跌色与状态色是两套语义。
- Tailwind 仅用于布局/工具类，`preflight` 已关闭；不要用 Tailwind 颜色替代 XC token。跟随正在修改文件的 Vue API 显式/自动导入风格，不在同一文件混用。
