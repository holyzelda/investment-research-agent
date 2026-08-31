# CLAUDE.md

先读仓库根 `CLAUDE.md` 获取身份、响应壳、飞书和快照等跨端约束。本文件只描述前端的非显然实现约定。

## 常用命令

从 `agent-frontend/` 执行。项目要求 Node.js `>=20.12.1`、npm `>=10.5.0`，包管理器固定为 npm；依赖变更必须同步 `package-lock.json`。

```bash
npm ci
npm run dev
npm run build
npm run build:staging
npm run preview
npm test
npm run test:watch
npm exec vitest -- run tests/calc-flow.spec.js
npm exec vitest -- run tests/calc-flow.spec.js -t "publishes each thinking frame reactively before done"
```

测试匹配 `tests/**/*.spec.js`，环境为 jsdom。当前没有 lint script，也没有 ESLint/Prettier 配置；不要虚构 lint 命令。

## 开发服务器与请求

- Vite `base` 是 `/investment/`，`@` 指向 `src/`。`VITE_APP_BASE_API` 默认 `/gateway/ir-agent/`；开发代理去掉此前缀后转发到 `VITE_DEV_BACKEND`，默认 `http://127.0.0.1:9089`。
- `/gateway/ecenter/` 和其他 `/gateway/` 平台接口转发到对应平台网关。个人代理覆盖写入被忽略的 `.env.local`，不要为本地端口修改已提交的 `.env*`。
- `src/utils/request.js` 的成功返回值是完整 `{code, msg, data}`，不会自动解包 `data`；API 模块或调用方需按现有模式读取。`blob` / `arraybuffer` 直接返回二进制。
- IR 请求附加 Bearer Token、`userId` 和 URL 编码后的 `username`；平台接口不附加 IR 身份。401 必须清理本地 Token/身份、记录需登录状态并弹出重新登录确认。

## 异步、参数与报告

- 对话使用 `src/utils/chatSse.js`；报告进度使用 `src/utils/reportSse.js`。流结束必须处理 `done`、显式错误、用户 abort 和异常 EOF，并保持 turn/conversation 的失效保护。
- 对话工具产生测算任务后可预取结果，但结果卡只在 `done` 后发布。消息和版本保持追加顺序，选中版本只定位既有结果，不重排消息。新增长请求或页面切换异步流程时复用 turn/epoch/request-version，防止旧响应覆盖新状态。
- `src/utils/paramAdjust.js` 根据后端参数字典的 `zone`、`control`、`step`、`min/max`、`g`、`options` 和冻结入参控制展示与覆盖值；不要在组件中另建参数规则。`operation_years` 保持 number，并按字典 options 渲染；同一会话内 province 固定，重新测算时一次合并基础面板和高级参数草稿。
- 正式报告从快照渲染，不重新测算。打印前将图表转换为 PNG；打印样式只作用于报告文档。

## 图表与样式

- 图表直接使用 `echarts`；源码不使用依赖中的 `vue-echarts`。Home/报告图表优先复用 `src/views/home/composables/useEcharts.js` 的 init、响应式 setOption、resize、dispose 和渲染回调。
- 中国地图使用本地 `src/assets/geo/china.json`；指数地图保持 SVG renderer，联络线地图保持 Canvas。
- XC token 位于 `src/design-system/tokens.css`，应用根节点使用 `xc-app`，数字展示复用 `.xc-num`。业务色优先使用 `var(--xc-*)` 或运行时读取 token；涨跌色与状态色是两套语义。
- Tailwind 仅用于布局/工具类，`preflight` 已关闭；不要用 Tailwind 颜色替代 XC token。跟随正在修改文件的 Vue API 显式/自动导入风格，不在同一文件混用。
