# 能力规格：backend-scaffold（后端基座）

> 来源：PRD §3 技术约束（对齐 trader）；DP-0 决策（FastAPI+SQLAlchemy 异步 MySQL+Alembic+Nacos）。

## ADDED Requirements

### Requirement: FastAPI 应用工厂镜像 trader

The system SHALL 在 `agent-backend/` 下以 trader（etrader-agent-nx/agent-backend）为蓝本建立 FastAPI 应用：应用工厂 `create_app()`、CORS→请求日志→鉴权中间件顺序、启动/关闭生命周期钩子、路由集中注册 `register_routers()`、loguru 日志。

#### Scenario: 服务可启动

- **WHEN** 以配置就绪的环境运行 `uvicorn app.main:app`
- **THEN** 服务成功启动，`/docs` 可访问，`/health` 返回健康状态

### Requirement: 统一响应壳与异常处理

The system SHALL 采用 `{"code": int, "msg": str, "data": any}` 统一响应壳，并注册业务异常/HTTP 异常/参数校验异常/全局异常处理器，错误码语义与 trader 对齐（401 未授权、400 参数、500 内部错误）。

#### Scenario: 业务异常被规范化

- **WHEN** 某接口抛出 `BusinessException("参数非法", 400)`
- **THEN** 响应为 HTTP 400，body 为 `{"code":400,"msg":"参数非法","data":null}`

### Requirement: Nacos 配置装载与本地降级

The system SHALL 通过 Nacos（`v2.nacos` SDK）在启动时加载数据源、Redis、飞书凭证、轮询阈值等业务配置（data_id 形如 `{app.name}-{profile}.yml`），Nacos 未启用或取不到时降级到本地 `.env`/`application.yml`；前端不感知这些配置。

#### Scenario: Nacos 装载成功

- **WHEN** `NACOS_ENABLED=true` 且 Nacos 中存在数据源配置
- **THEN** 启动日志显示"从 Nacos 加载数据库配置成功"，`ir_agent` 数据源可用

#### Scenario: Nacos 降级

- **WHEN** `NACOS_ENABLED=false`
- **THEN** 服务从本地环境变量加载数据库配置并正常启动

### Requirement: 异步 SQLAlchemy 与 ir_agent 数据源

The system SHALL 提供异步 SQLAlchemy 引擎/会话，主数据源为 MySQL 库 `ir_agent`，以 FastAPI 依赖注入方式向路由提供 `AsyncSession`，并以 Alembic 管理 `ir_agent` 表结构迁移。

#### Scenario: 会话依赖可用

- **WHEN** 某路由声明 `session: AsyncSession = Depends(get_db_session)` 并执行查询
- **THEN** 查询在 `ir_agent` 上执行成功，请求结束会话被正确释放

#### Scenario: 迁移可执行

- **WHEN** 执行 `alembic upgrade head`
- **THEN** `ir_agent` 中创建出本变更定义的快照/会话/任务相关表
