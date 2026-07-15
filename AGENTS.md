# AGENTS.md — 朱雀投研智能体（ZRA-3）工程约定与协作须知

> 面向在本仓库工作的 AI 助手与工程师。记录**不写在代码里、但影响每次开发的约定与踩坑**。
> **权威需求（PRD）在仓库外**：`D:\0_工作\2026\投研智能体\docs\prd\PRD-001.md`（台账 `D:\0_工作\2026\投研智能体\docs\PRD_REGISTRY.md`）。
> in-repo `changes/PRD-001-login-calc-mainflow/`（proposal/specs/design/tasks）是其落地拆解；**两者以 PRD 为准**，本文件不重复。

## 1. 项目定位（一句话）

面向储能投资投研的内部智能体，**统一平台的子应用**。一阶段打通"首页对话 → 飞书副本测算 → 结果三模块 → 快照/版本"。
- 前端 `agent-frontend/`：Vue3 + Vite + Element Plus + 玄策(XC)设计体系，**无独立登录页**。
- 后端 `agent-backend/`：FastAPI + 异步 SQLAlchemy(库 `ir_agent`) + Nacos，团队统一栈。

## 2. 目录（DDD 分层 + 限界上下文）

```text
agent-backend/
  app/
    core/                  # 跨上下文基础能力：配置、常量、异常、统一响应
    infrastructure/        # 技术基础设施：database / nacos / web(app_factory、deps、中间件、路由注册)
    modules/               # 限界上下文按模块隔离
      platform_access/     # 平台接入上下文：请求头身份读取、平台入口相关 API
        domain/            # 领域模型
        interface/         # FastAPI router / deps / middleware
      calculation/         # 测算上下文：参数字典、参数组装、飞书测算适配
        domain/            # 领域模型、领域服务、端口、参数字典
        application/       # 应用服务/用例编排，如 param_assembler、factory
        infrastructure/    # 仓储、数据文件读取、飞书客户端、provider
        interface/         # FastAPI router
  tests/
    unit/                  # 领域/架构守护等快速测试
    integration/           # 模块内集成测试
    e2e/                   # ASGI 端点级测试

agent-frontend/
  src/
    api/ router/ store/    # 前端接口、路由、状态
    design-system/         # XC 风格 token 与说明
    layout/ views/ styles/ # 页面骨架、业务页面、全局样式

changes/PRD-001-login-calc-mainflow/ # spec-superflow 需求/设计/任务，不在 AGENTS.md 重复展开
```

- 后端采用“实用 DDD”：`modules/<context>/{domain,application,infrastructure,interface}`；不是所有上下文都必须四层齐全，按实际需要补齐。
- 当前主要限界上下文：`platform_access`（平台身份/入口）与 `calculation`（投研测算）。跨上下文通用技术能力放 `app/infrastructure/`，通用业务无关能力放 `app/core/`。
- 架构路径由 `agent-backend/tests/unit/test_architecture_layout.py` 守护；调整目录/模块名时同步更新该测试与本节。

## 3. 铁律（务必遵守）

- **不过度设计，简单事简单做**：需求给的是什么就做什么，**不擅自加**自动探测、mode 分支、可选回退、多层封装、编号取参（`_arg(1/2/3)`）、写文件+flush 包装等"贴心功能"。工具/基准脚本尤其要直白——**读参数 → 取数 → 算 → 打印**，一条直线走完即可。**参数不要走 `sys.argv`/命令行解析**，直接在脚本顶部开一个"参数配置区"硬编码变量（要改就改那几行），方便又简单。判断标准：一个简单诉求写出几十上百行、绕来绕去，就是过度设计，回头砍。（例：现货基准脚本 `tools/spot_benchmark.py` 一度被塞进自动探测区间/mode 参数/argv 取参/写文件，被要求砍成"顶部配置区硬编码 → 取数→算→打印"。）
- **先读 PRD 再动需求**：涉及需求/参数/业务规则/接口契约的改动，动手前**必须先读权威 PRD** `D:\0_工作\2026\投研智能体\docs\prd\PRD-001.md`（不确定改哪份先查台账 `docs\PRD_REGISTRY.md`）。凭记忆容易漏关键约束（例：**各省收益结构表(表2)决定各交易品类开关、且"表2取数由本系统后端做"**——见 PRD §四来源）。
- **不自动执行 git**：`git add/commit/push` 等一律由人手动执行；助手改完代码不碰 git。
- **阶段0 不做登录**：本系统**不实现**登录页/注册/验证码/用户管理/RBAC/token 校验——统一由平台首页负责。
  身份来自平台/网关注入的**请求头**，后端 `PlatformIdentityMiddleware` 直接信任读取 `user_id/username`，仅用于快照归属。
- **前端不 fork etrader 业务**：只借鉴 XC 设计体系与框架层写法；不引入 ecenter 登录、不带 `systemSign`。
- **后端不抄 trader 后端/鉴权代码**：仅框架选型（FastAPI/SQLAlchemy/Nacos）与团队一致，实现自研。
- **飞书方案A**：系统只读写接口区 `API_INPUT/API_OUTPUT/API_META`，绝不直接读写模型单元格。

## 4. 依赖管理（统一入口，别手动装）

### 后端
- **依赖统一从 `requirements.txt` 安装**，人工执行命令：
  1. 首次建 venv（只需一次）：`Python313\python.exe -m venv .venv`
  2. 装/更新依赖：`.venv\Scripts\python.exe -m pip install -r requirements.txt`
- **不手动 `pip install <包名>`**。新增依赖：写进 `requirements.txt`（带版本范围）→ 重跑步骤 2 → 提交 `requirements.txt`。
- 按**版本范围**安装，**不使用锁文件**（团队决定；保证来源/流程统一，不追求逐字节一致）。
- MySQL 异步驱动用 `aiomysql`（纯 Python，Windows 免编译）；高性能备选 `asyncmy` 需 C++ 编译环境，按需单独装。本地/单测用 sqlite（`aiosqlite`）。

### 前端
- **统一用 pnpm**，不搞安装脚本，走约定：`pnpm install` → `pnpm dev/test/build`。
- `package.json` 已设 `packageManager: pnpm@9` + `preinstall: only-allow pnpm`，用 npm/yarn 会被拦。
- **`pnpm-lock.yaml` 必须提交**（团队一致的关键）；`package-lock.json`/`yarn.lock` 已被 .gitignore 拦。
- 新增依赖：`pnpm add <包名>` → 提交 `package.json` + `pnpm-lock.yaml`。

## 5. Python 解释器约定（全局规则）

不要直接用 `python`/`python3`（PATH 里没有）。优先级：
1. 项目 venv：Windows `agent-backend\.venv\Scripts\python.exe`；*nix `agent-backend/.venv/bin/python`。
2. 系统 Python 3.13：`C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe`。

## 6. 测试与运行

依赖安装入口见第 4 节；不要绕过统一依赖文件手动装包。

```bash
# 后端（在 agent-backend 目录）
.venv\Scripts\python.exe -m pytest                # 纯逻辑单测；DB 用例连测试库 ir_agent 真实留痕
.venv\Scripts\python.exe -m app.main              # 启动服务（连测试库）；main.py 内置入口，可 IDE F5 调试
# 建表：手动在 ir_agent 库执行 sql/ir_agent_schema.sql（DDL 由 ORM 生成，不用 Alembic 迁移）

# 前端（在 agent-frontend 目录）
pnpm test && pnpm dev
```

## 7. 踩坑记录（实测得来，避免重蹈）

### 7.1 后端测试必须用 httpx ASGITransport，不要用 Starlette TestClient
- **现象**：`TestClient` 触发 SQLAlchemy 异步引擎时报
  `ValueError: the greenlet library is required ... DLL load failed while importing _greenlet: 应用程序控制策略已阻止此文件`。
- **根因**：本机存在**应用管控策略（AppLocker/WDAC 类）**，`TestClient` 用 anyio 起**后台线程**跑事件循环，
  greenlet 的 C 扩展 `.pyd` 在新线程**首次动态加载**时被策略偶发拦截。主线程/独立脚本加载则正常。
- **对策**：测试统一用 `httpx.ASGITransport` + `AsyncClient` 在**主事件循环**内直连 ASGI 应用（FastAPI 官方异步测试写法）；
  `pytest.ini` 设 `asyncio_mode = auto`。**新增测试请照此写，勿用 TestClient。**
- **写法**：`AsyncClient` 本身就是异步上下文管理器；helper/fixture 应同步返回或 yield 配好的客户端，不要让调用方写
  `async with await _client() as client`。仍需保留 `ASGITransport(app=app)`，否则请求不会路由到本地 ASGI 应用。

### 7.2 HTTP header 只能 ASCII —— 平台传中文用户名要先编码
- **现象**：往 header 塞中文（如用户名"张三"）→ httpx 报 `UnicodeEncodeError: 'ascii' codec can't encode`。
- **约定**：平台/网关若在 header 传中文 `username`，须由**平台侧** URL-encode 或 Base64；本系统解码读取。
  确切 header 字段名 + 中文编码方式属**平台对接约定（PRD 挂账 #8）**，待与平台确认。

### 7.3 配置路径：settings 的 CONFIG_DIR 要退到 agent-backend 根
- `app/core/config/settings.py` 距 `configs/application.yml` 为 **4 层** `dirname`（config→core→app→agent-backend）。
- 少退一层会静默"配置文件不存在，使用默认值"——启动看似正常但读不到 yml。改动配置加载路径时注意。

## 8. 平台对接待确认项（挂账 #8，不阻塞开发）

- 平台/网关注入身份的**确切 header 字段名**（默认占位 `X-User-Id` / `X-User-Name`，可经 Nacos/env 覆盖 `platform.header_user_id/username`）。
- 平台跳转进入本系统的**入口 URL**。
- header 缺失时的期望行为（当前：`platform.allow_anonymous=true` 时降级匿名占位，便于本地联调）。
- 中文 `username` 的编码方式（见 7.2）。

## 9. 配置分层

- 前端 `.env.*` 仅：`VITE_APP_BASE_API`（网关基地址）/`VITE_APP_TITLE`/`VITE_FAVICON`/`VITE_APP_ENV`。
- 后端：本地 `configs/application.yml` + `.env`；生产敏感项（数据源、飞书凭证、轮询阈值、header 字段名）走 **Nacos**。
  - **应用启动/联调/集成**：默认连**测试库** `mysql+aiomysql://example_user:example_password@database.example.invalid:3306/ir_agent`（密码写在 yml，正式走 Nacos）。
  - **纯逻辑单测（pytest）**：`tests/conftest.py` 用 `IR_DB_URL` 覆盖为内存 sqlite，不连真库；**DB 相关测试**另走 `tests/db/conftest.py` 直连测试库 `ir_agent`，真实插入、留痕不清理（测试行标记 `username='__pytest__'` 便于筛/清）。
  - 配置优先级：环境变量 `IR_DB_URL` > `application.yml` > 代码默认值。
  - MySQL 异步驱动用 `aiomysql`（纯 Python，Windows 免编译）；URL 前缀 `mysql+aiomysql://`，**不是** Java 的 `jdbc:mysql://`。
  - 连库前提：`internal-3-60.example.invalid` 上需已有 `ir_agent` 库（`CREATE DATABASE ir_agent DEFAULT CHARSET utf8mb4;`）；**建表手动执行 `sql/ir_agent_schema.sql`**（DDL 由 ORM 生成，本项目不用 Alembic 迁移）。
