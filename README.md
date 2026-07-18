# 朱雀投研智能体 ZRA-3（investment-research-agent）

面向储能投资投研的内部智能体，**统一平台的子应用**。一阶段打通"首页对话 → 飞书副本测算 → 结果三模块 → 快照/版本"主闭环。

> 阶段0 为**平台接入**：不做登录/用户/权限（由统一平台首页统一管理），用户经平台跳转承接落地对话首页，身份由平台/网关注入请求头、后端直接信任读取。

## 结构
```
investment-research-agent/
├── agent-frontend/   # Vue3 + Vite + Element Plus + 玄策(XC)设计体系（无登录页）
├── agent-backend/    # FastAPI + 异步 SQLAlchemy(ir_agent) + Nacos；实用 DDD 分层
├── changes/          # spec-superflow 规格制品（proposal/specs/design/tasks）
└── CLAUDE.md         # AI 协作入口：硬性规则、目录约定、踩坑记录
```

后端当前按 `app/modules/<context>/{domain,application,infrastructure,interface}` 组织限界上下文，主要上下文为 `platform_access` 与 `calculation`。详细目录与协作规则见 `CLAUDE.md`，后端命令与配置见 `agent-backend/README.md`。

## 快速开始
详见各子应用 README：
- 前端：`agent-frontend/README.md`
- 后端：`agent-backend/README.md`

## 规格与需求
- PRD：`D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md`
- 规格制品：`changes/PRD-001-login-calc-mainflow/`（proposal / specs / design / tasks）

## 技术栈
| 层 | 选型 |
|---|---|
| 前端 | Vue 3 · Vite 5 · Element Plus 2.4 · Pinia · Vue Router 4 · ECharts 5 · 玄策设计体系 |
| 后端 | FastAPI · 异步 SQLAlchemy 2 · httpx/tenacity · APScheduler · Nacos |
| 数据 | MySQL 库 `ir_agent`（快照 JSON 存储；建表 DDL 见 `agent-backend/sql/ir_agent_schema.sql`） |
| 计算 | 飞书底稿副本（方案A 独立接口区 API_INPUT/OUTPUT/META） |
