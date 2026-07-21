# 朱雀投研智能体 · 后端（agent-backend）

团队统一栈：**FastAPI + 异步 SQLAlchemy + Nacos**（仅框架选型一致，代码自研，不复制 trader 后端/鉴权）。

## 阶段0：平台接入（无登录）
本系统**不做**登录/注册/验证码/用户/权限。用户在统一平台完成登录后跳转承接；
平台/网关向请求头注入身份，`PlatformIdentityMiddleware` 读取 `user_id/username` 注入 `request.state`，
仅用于快照归属。header 字段名可配（`platform.header_user_id/username`，默认 `X-User-Id`/`X-User-Name`，待与平台约定）。

## 目录（DDD 分层 + 限界上下文）

采用“实用 DDD”组织：跨上下文的基础能力放 `core/` 与 `infrastructure/`，业务按限界上下文放在 `modules/<context>/` 下。典型上下文内部按 `domain / application / infrastructure / interface` 分层；不是所有上下文都必须四层齐全，按实际需要补齐。

依赖方向原则：`interface → application → domain`；`domain` 不依赖 FastAPI、数据库或外部服务；`infrastructure` 实现端口、仓储、数据读取与外部系统适配。

```
app/
├── main.py                         # 应用入口（暴露 app + 本地直跑），组装逻辑在 infrastructure/web
├── core/                           # 跨上下文基础能力
│   ├── config/settings.py          # 分层配置（默认→yaml→env）
│   ├── constants.py                # HttpStatus 等常量
│   ├── exceptions.py               # 通用异常
│   └── response.py                 # {code,msg,data} 响应壳
├── infrastructure/                 # 技术基础设施
│   ├── database/                   # ORM 基类(base) + 异步引擎/会话(session)
│   ├── nacos/client.py             # Nacos 装载（未启用则本地降级）
│   └── web/                        # 组合根：app_factory / deps / health / 路由注册 / 通用中间件
├── modules/                        # 限界上下文（DDD 核心）
│   ├── platform_access/            # 平台接入上下文：请求头身份读取、平台入口相关 API
│   │   ├── domain/models.py        # CurrentUser 等领域模型
│   │   └── interface/              # deps(get_current_user) / middleware / router(/ir/me)
│   └── calculation/                # 测算上下文：参数字典、参数组装、飞书测算适配
│       ├── domain/                 # models / services / ports / param_dictionary
│       ├── application/            # param_assembler / factory 等用例编排
│       ├── infrastructure/         # 仓储、数据文件读取、飞书客户端、provider
│       │   └── data/               # param_dict、revenue_structure 等静态数据
│       └── interface/router.py     # /ir/calc/* 端点
configs/application.yml             # 本地配置
migrations/                         # Alembic（异步）
tests/                              # unit / integration / e2e（端点测试用 ASGITransport）
```

架构路径由 `tests/unit/test_architecture_layout.py` 守护；调整目录或模块名时同步更新该测试、本文档和根目录 `CLAUDE.md`。

## 命令

依赖统一从 `requirements.txt` 安装，人工执行以下命令即可。

```bash
# ① 首次：创建虚拟环境（只需一次，之后复用）
C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
#   Linux/Mac: python3 -m venv .venv

# ② 安装 / 更新依赖（改了 requirements.txt 后重跑此条）
.venv\Scripts\python.exe -m pip install -r requirements.txt
#   Linux/Mac: .venv/bin/python -m pip install -r requirements.txt

# ③ 运行测试（单测走内存 sqlite，不连真库）
.venv\Scripts\python.exe -m pytest

# ④ 启动服务（默认加载 .env.test；业务配置来自 Nacos 或 configs/application.yml）
#   方式一（推荐）：运行 run.py，先加载环境文件再创建应用
.venv\Scripts\python.exe run.py
#   生产环境显式选择环境文件
set ENV_FILE=.env.prod && .venv\Scripts\python.exe run.py
#   方式二：传统 uvicorn 命令（等价）
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8080

# ⑤ 数据库迁移（Batch 3 有模型后）
.venv\Scripts\alembic.exe upgrade head
```

> **依赖管理约定**：所有人统一从 `requirements.txt` 安装（命令 ②），**不要手动 `pip install <包名>`**。
> 新增依赖：把包写进 `requirements.txt`（带版本范围，如 `xxx>=1.2`）→ 重跑命令 ② → 提交 `requirements.txt`。
> 按**版本范围**安装，不使用锁文件（团队决定：保证来源/流程统一，不追求逐字节一致）。
> MySQL 异步驱动用 `aiomysql`（纯 Python，Windows 免编译）；高性能备选 `asyncmy` 需 C++ 编译环境，按需单独装。

> **启动方式说明**：`run.py` 负责在创建应用前加载 `ENV_FILE` 指定的 `.env.test` 或 `.env.prod`；`app/main.py` 保留标准 `app.main:app` ASGI 导出。必须从 `agent-backend` 目录运行，或在 IDE 中将工作目录设为 `agent-backend`。
> host/port/热更新从 `ENV_FILE` 指定的 `.env.test` 或 `.env.prod` 读取（`APP_DEBUG=true` 自动开 reload）。

## 配置分层
启动参数与业务参数分层存放：

- `.env.test` / `.env.prod`：只保存 `APP_*` 和 `NACOS_*`。由 `app/main.py` 根据 `ENV_FILE` 显式选择，缺省为 `.env.test`；其中 `APP_NAME` 与 `NACOS_PROFILE` 决定远端 data ID `{app.name}-{profile}.yml`。
- `configs/application.yml`：本地业务配置，包括 `database`、`platform`、`feishu`、`cors`、`calc` 与 `spot_price`。
- Nacos：使用与本地 YAML 相同的业务节点覆盖本地配置；Nacos 未启用、不可达、返回空内容或 YAML 非法时自动使用本地 YAML。

Nacos 远端业务配置优先级最高，其次为已有 `IR_*` 业务环境变量，随后是本地 YAML 与默认值。Nacos 远端配置不会覆盖 `app` 或 `nacos` 节点，因此服务连接信息和注册身份在启动后保持稳定。

### 上线前需改动的配置清单
> 业务配置在 `configs/application.yml` 与对应 Nacos data ID 中保持相同结构；生产应由 Nacos 承载敏感项，勿把生产凭据提交进仓库。

**数据库**
- `database.url`（env `IR_DB_URL`）→ 生产 `ir_agent` 库连接串。

**现货电价库 `spot_price`**
- `enabled`（env `IR_SPOT_ENABLED`）→ `true` 启用查表。
- `province_dsn`（env `IR_SPOT_PROVINCE_DSN`）→ 生产省级电价库。
- `node_dsn`（env `IR_SPOT_NODE_DSN`）→ 生产节点电价库。
- `province_price_coefficients` → 按生产口径的省级修正系数。
- ⚠ 预计算表（`ir_spot_daily_optimal_province/node`、`ir_spot_station`）需在**生产 ir_agent 库重建** DDL（`sql/spot_precompute_schema.sql`）并**重新全量回填**（测试库预算数据不可带到生产）。

**飞书 `feishu`**（env `IR_FEISHU_*`）
- `app_id` / `app_secret` → 生产自建应用凭据。
- `template_token` → 生产底稿模板 token。
- `target_folder_token` → 生产副本文件夹 token。
- `revenue_structure_token` → 生产表2 电子表格 token。

**平台 / 其它**
- `.env.prod` 中的 `NACOS_ENABLED`、`NACOS_SERVER_ADDR`、`NACOS_NAMESPACE`、`NACOS_GROUP`、`NACOS_PROFILE`、`NACOS_DISCOVERY_SERVICE_NAME` → 上线前由运维填入；服务会在成功加载配置后注册到 Nacos。
- `platform.header_user_id/username` → 与平台约定的真实 header 字段名（挂账#8）。
- `platform.allow_anonymous` → 生产设 `false`（⚠ 挂账#9：当前禁匿名分支未拦截，上线前需补 401）。
- `APP_HOST` / `APP_PORT`、`cors.allow_origins`（生产收紧到平台域名，勿留 `*`）。

## 现货电价 · 预计算与日更

现货充/放均价用离线预计算：多循环 DP 逐日算好各 K 的最优结果，落 `ir_agent` 三张表；
测算时按滚动一年窗口 SUM → 均价 → ×省份系数 → ÷1000，毫秒级（`PrecomputeSpotPriceAlgo`）。
核心逻辑在 `app/modules/calculation/infrastructure/spot_precompute.py`（`run_precompute()`），手动脚本与应用内日更调度共用同一份逻辑。

```bash
# 首次全量回填（下班挂后台，断点续传、中断可重跑；CPU 密集，宜独立机器/时段跑）：
# 顶部配置区设 PROVINCE_AREAS=["*"]、NODE_STATIONS=["*"]、RUN_DATE=当天
.venv\Scripts\python.exe tools\spot_precompute.py
```

**日更自动化（应用内固定时刻触发，随 `agent-backend` 服务启动自动挂载，无需系统计划任务/cron）**：

- `spot_price.daily_update_enabled` 默认 `false`；仅需要跑日更的部署机设为 `true`（或环境变量 `IR_SPOT_DAILY_UPDATE_ENABLED=true`）。
- `daily_update_hour` / `daily_update_minute` 默认 `03:30`，应晚于源电价库当天数据入库完成的时刻；`daily_update_workers` 默认 `4`，比全量回填手动脚本更保守，避免与在线 API 争抢资源。
- 实现为 `spot_daily_scheduler.py` 的 APScheduler `BackgroundScheduler`（独立线程，不阻塞 FastAPI 事件循环/启动）。每次触发先抢 MySQL `GET_LOCK('ir_spot_daily_update')`；多实例/多 worker 下只有一个实例实际运行，其他实例跳过。任务异常只记录日志，不影响服务。
- 日更只补当天新增数据；首次上线仍需先完成一次全量回填，不能用日更补出滚动一年窗口的历史。

> 全量回填 CPU 密集（进程池默认 10 核，十几小时级），建议独立机器/时段跑；不要在运行日更的同一服务进程内同时手动全量回填。
