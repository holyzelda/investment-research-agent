# 项目 CLAUDE 配置文件（朱雀投研智能体 ZRA-3）

> 本文件是**高频铁律 + 查阅路由**，不复述细节。详细内容在下面指向的权威文档里，按需读，不要每次全读。

## 1、按需查阅路由（关键：不要无脑全读大文档）

先判断需求类型，只读对应文档 / 章节，不要每次把整份开发指南读完：

| 需求类型 | 先读 |
|---|---|
| 任何改动动手前的工程铁律、目录约定、已知踩坑 | `AGENTS.md`（仓库根） |
| 定位「小功能放哪 / 改动影响哪些模块 / 怎么验证」 | `my_projects/investment-research-agent-项目开发指南.md` 里**对应章节**（前端看第 5 章、后端看第 6 章、数据契约看第 7 章、常见需求看第 8 章、验证看第 9 章） |
| 业务规则 / 参数 / 接口契约变更 | 仓外权威 PRD（优先级最高，路径见开发指南第 1.2 节，属本机/协作方各自约定，不在此硬编码绝对路径） |
| 涉及「联络线地图」模块 | `my_projects/联络线地图模块-功能与开发文档.md` |
| 涉及「政策与市场」模块 | `my_projects/政策与市场模块-功能与开发文档.md`；当前前端入口为 `agent-frontend/src/views/policy-market/`，数据边界为 `agent-frontend/src/api/policyMarket.js` 与 `agent-frontend/src/store/modules/policyMarket.js` |
| 纯闲聊、简单问答、与代码无关 | 无需读文档，直接答 |

冲突时优先级：**仓外 PRD > 仓内规格制品 > 源码/测试/DDL > 各类 README/指南**。

## 2、不可突破的红线（每次都要守）

- **不实现登录**：本项目是平台子应用，不做登录/注册/token 校验/路由守卫；身份由平台请求头注入。
- **后端分层**：`interface → application → domain`，`infrastructure` 实现外部依赖。`domain` 层禁止 import FastAPI / SQLAlchemy / httpx / 飞书 SDK。目录由 `tests/unit/test_architecture_layout.py` 守护，动目录必须同步改测试。
- **飞书只碰接口区**：只与 `API_INPUT / API_OUTPUT / API_META` 交互，绝不直接读写飞书模型单元格或公式区。
- **前端 pnpm-only**：新依赖用 `pnpm add`，同步提交 `package.json` 和 `pnpm-lock.yaml`；不用 npm/yarn。
- **颜色走 token**：图表和业务色用 `var(--xc-*)`，禁止硬编码 `#hex`/`rgb()`；ECharts 复用 `useEcharts` 生命周期，Canvas 内的色值用运行时读取的 XC 变量。
- **改 ORM 必同步手工 DDL**：无 Alembic，改模型要同步 `agent-backend/sql/*.sql`、快照读写、历史兼容。
- **历史结果只从快照恢复**：查历史结果不得重跑飞书 / 重新测算。
- **不落密钥**：`my_projects/` 及任何文档不写数据库连接、密码、飞书 Token、生产地址。

## 3、验证约定

- 后端跑测试用项目虚拟环境，不依赖 PATH 里的 `python`：`.venv\Scripts\python.exe -m pytest`。
- 后端端点测试一律用 `httpx.ASGITransport + AsyncClient`，不用 Starlette `TestClient`（当前 Windows 环境会踩 greenlet 限制）。
- 前端：`pnpm test` / `pnpm build` / `pnpm dev`（node 不在 PATH 时先 `export PATH="/c/Program Files/nodejs:$PATH"`）。
- 新增字段要沿全链路连带检查：请求模型 ↔ DTO/组装器/映射器 ↔ 快照读写 ↔ 前端展示/历史恢复 ↔ 测试。

## 4、文档同步

新增/移除模块、路由、主要 API，或改动主链路、快照表、核心 Store、图表结构时，同步更新 `investment-research-agent-项目开发指南.md`；涉及联络线地图时同步更新其子文档。
