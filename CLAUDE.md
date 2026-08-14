# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库定位

朱雀投研智能体（ZRA-3）由两个独立运行的子应用组成：

- `agent-frontend/`：Vue 3 平台子应用，包含 ecenter 登录与动态菜单、对话测算、全国储能投资指数、联络线、政策与市场、正式报告页面。
- `agent-backend/`：FastAPI 服务，按 `platform_access`、`calculation`、`middle_platform`、`report`、`tie_line_map`、`index_map`、`policy_market` 七个上下文组织。

进入子应用前先读其 `CLAUDE.md`；命令和局部架构以子应用文件为准。本文件只记录跨端边界。spec、设计文档和 README 可用于定位背景，但若与实现冲突，应以源码、配置和测试为准。

## 身份与请求边界

- 前端实际承接 ecenter 登录、`getInfo` 和动态菜单，并保存平台 Bearer Token。IR 业务请求使用固定 `userId` / `username` Header；`username` 由前端 URL 编码为 ASCII。
- `/gateway/ecenter/**`、`/gateway/code` 等平台请求不携带 IR 身份 Header。测试/生产环境由可信网关认证后注入或覆盖同名 Header。
- 后端只消费平台身份，不调用 ecenter、不解析或签发 Token，也不实现注册、用户管理、RBAC 或 JWT。除文档和健康检查外，缺少任一身份 Header 返回 401，绝不回退为匿名用户。
- 会话、任务、结果、报告和咨询记录均按当前用户归属查询；非本人资源统一表现为 404。

## 主要数据流

1. 前端通过 `POST /ir/chat/diag` 连接中台 SSE 对话代理；工具事件产生测算任务。
2. 后端以参数字典组装冻结入参，复制 15 年或 20 年飞书模板，只读写接口区域并生成结果快照；同一会话的后续测算只追加版本。
3. 历史会话和结果从数据库快照恢复，不重新调用飞书。正式报告从测算快照生成，报告任务通过 SSE 推送进度，前端用浏览器打印生成 PDF。
4. 全国指数、联络线、政策与市场是独立业务模块；它们与测算/报告共享统一平台身份和响应壳，但不应被塞入测算上下文。

## 跨端不变量

- 响应壳统一为 `{code, msg, data}`；请求参数校验映射为 HTTP 400，不使用 FastAPI 默认 422，也不把参数错误包装成 500。
- 飞书是权威计算器，应用不重写财务公式。只可读写 `API_INPUT`、`API_OUTPUT`、`API_META`；允许额外读取的输出区域仅限代码中明确配置的报告/画图数据区域，不直接访问模型公式单元格。
- `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json` 是参数元数据、可调性和飞书映射的唯一契约；前后端不得绕过字典写死参数规则。
- `operation_years` 只允许 15 或 20，用于选择固定运营期模板；它保留在冻结入参和快照中，但不得写入 `API_INPUT` 单元格。同一会话可以混用两种运营期版本。
- 每次成功测算都追加版本，不覆盖历史入参或结果；历史展示必须能仅依赖快照完成。

## 工程约束

- 前端只使用 npm：初始化用 `npm ci`，依赖变更用 `npm install` / `npm uninstall`，同步维护 `package.json` 与 `package-lock.json`；不用 pnpm/yarn。
- 后端依赖只经 `agent-backend/requirements.txt` 管理。Python 命令优先使用 `agent-backend/.venv\Scripts\python.exe`，不要调用 PATH 中的 `python` / `python3`。
- 改 ORM 时同步检查手工 DDL、增量 migration、快照读写与历史兼容；具体约束见后端 `CLAUDE.md`。
- 未经用户明确要求，不执行 `git add`、`git commit`、`git push` 等 Git 写操作。
- 不要建worktree，就在当前分支上直接修改