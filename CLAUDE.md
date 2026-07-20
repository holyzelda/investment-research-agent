# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

> 权威需求（PRD）在仓库外：`D:\0_工作\2026\投研智能体\docs\prd\PRD-001.md`（台账 `D:\0_工作\2026\投研智能体\docs\PRD_REGISTRY.md`）。
> 仓库内 `changes/PRD-001-login-calc-mainflow/` 是其落地拆解；需求、参数、业务规则或接口契约改动前先读 PRD，PRD 优先。

## 项目定位

朱雀投研智能体（ZRA-3）是统一平台的子应用。用户在平台首页完成登录后进入本系统；身份由平台/网关注入请求头。本系统不实现登录、注册、验证码、用户管理、RBAC、token 校验或前端登录页。

一阶段主闭环是：`首页对话 → 飞书副本测算 → 结果三模块 → 快照/版本`。

## 仓库结构

```text
agent-backend/    # FastAPI + 异步 SQLAlchemy + Nacos；后端约束见 agent-backend/CLAUDE.md
agent-frontend/   # Vue3 + Vite + Element Plus + Pinia + XC；前端约束见 agent-frontend/CLAUDE.md
changes/          # spec-superflow 制品
```

子应用分别独立运行；改动子应用时先读其 `CLAUDE.md` 和 README。

## 跨端铁律

- 简单需求保持简单：不擅自添加自动探测、mode 分支、回退链路、多层封装或命令行参数解析；工具脚本采用“顶部参数区 → 取数 → 计算 → 打印”。
- 不执行 `git add`、`git commit`、`git push` 等 Git 写操作，除非用户明确要求。
- 前端不 fork etrader 业务，不引入 ecenter 登录或 `systemSign`；后端不抄 trader 的业务或鉴权代码。
- 飞书方案 A：只读写 `API_INPUT`、`API_OUTPUT`、`API_META`，绝不直接读写模型单元格；允许读取的输出区域仅有 `API_OUTPUT` 与 `画图数据`。
- 响应壳统一为 `{code, msg, data}`；参数校验统一 HTTP 400，不使用 422/500。
- 平台身份是信任式 header：`user_id`/`username` 仅用于会话和快照归属；不实现 session、JWT 或密码逻辑。
- 会话软删除；会话、任务和结果读取都按当前用户过滤，非本人资源统一 404。

## 依赖管理

- 后端依赖只经 `agent-backend/requirements.txt` 管理；新增依赖写入版本范围后再安装。
- 前端只使用 `pnpm`；新增依赖通过 `pnpm add`，并提交 `package.json` 与 `pnpm-lock.yaml`。
- 不使用 `python` 或 `python3`：优先项目 `.venv`，否则使用 `C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe`。

## 跨端测算约定

- 飞书是唯一权威计算器；应用不重写财务公式。历史/结果展示只读 `report_snapshot`，不依赖飞书副本长期存在。
- 同一 `conversation_id` 的每次测算追加版本，不覆盖历史入参或结果。
- 参数字典是参数元数据与飞书映射的唯一数据契约；前后端不得绕过字典写死参数展示、可调性或接口单元格。
- `operation_years` 只支持 15、20：它决定复制哪个固定运营期飞书模板，保留在冻结入参与 `input_snapshot`，但绝不写入任何 `API_INPUT` 单元格；同一会话可混用两个运营期版本。

## Spec-Superflow

`changes/PRD-001-login-calc-mainflow/` 存在 active spec-superflow 制品。涉及该变更的实现前必须检查并遵守其状态、执行合同和 execution plan；未经合同批准及当前 execution plan 不得开始应用代码改动。
