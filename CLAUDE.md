# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

> 权威需求（PRD）在仓库外：`D:\0_工作\2026\投研智能体\docs\prd\PRD-001.md`（台账 `D:\0_工作\2026\投研智能体\docs\PRD_REGISTRY.md`）。
> 仓库内 `changes/PRD-001-login-calc-mainflow/`（proposal/specs/design/tasks）是其落地拆解；**两者以 PRD 为准**，本文件不重复展开。

## 1. 项目定位

面向储能投资投研的内部智能体"朱雀投研智能体"（ZRA-3），**统一平台的子应用**（不是独立系统）：用户在统一平台首页完成登录后跳转承接进入本系统，身份由平台/网关注入请求头，本系统后端直接信任读取。**本系统不实现登录页/注册/验证码/用户管理/RBAC/token 校验**——这些一律由统一平台首页负责，属于明确的范围外。

一阶段目标：打通"首页对话 → 飞书副本测算 → 结果三模块 → 快照/版本"主闭环。

## 2. 仓库结构（monorepo，两个独立运行的应用）

```
agent-backend/    # FastAPI + 异步 SQLAlchemy（库 ir_agent）+ Nacos，实用 DDD 分层
agent-frontend/   # Vue3 + Vite + Element Plus + Pinia + 玄策(XC) 设计体系，无登录页
changes/          # spec-superflow 需求/设计/任务制品（PRD-001 的落地拆解）
```

两个子应用各有自己的 README（`agent-backend/README.md`、`agent-frontend/README.md`，含完整命令参考），`agent-frontend/CLAUDE.md` 补充前端的具体架构细节（Pinia store 形态、消息/版本模型、设计体系约定）。本文件覆盖跨两侧的公共信息，不与它们重复。

## 3. 铁律（务必遵守）

- **不过度设计，简单事简单做**：需求给的是什么就做什么，**不擅自加**自动探测、mode 分支、可选回退、多层封装、编号取参（`_arg(1/2/3)`）、写文件+flush 包装等"贴心功能"。工具/基准脚本尤其要直白——**读参数 → 取数 → 算 → 打印**，一条直线走完即可。**参数不要走 `sys.argv`/命令行解析**，直接在脚本顶部开一个"参数配置区"硬编码变量（要改就改那几行），方便又简单。判断标准：一个简单诉求写出几十上百行、绕来绕去，就是过度设计，回头砍。（例：现货基准脚本 `tools/spot_benchmark.py` 一度被塞进自动探测区间/mode 参数/argv 取参/写文件，被要求砍成"顶部配置区硬编码 → 取数→算→打印"。）
- **先读 PRD 再动需求**：涉及需求/参数/业务规则/接口契约的改动，动手前**必须先读权威 PRD**（不确定改哪份先查台账 `PRD_REGISTRY.md`）。凭记忆容易漏关键约束（例：**各省收益结构表(表2)决定各交易品类开关、且"表2取数由本系统后端做"**——见 PRD §四来源）。
- **不自动执行 git**：`git add/commit/push` 等一律由人手动执行；改完代码不碰 git。
- **阶段0 不做登录**：见第 1 节。身份来自平台/网关注入的**请求头**，后端 `PlatformIdentityMiddleware` 直接信任读取 `user_id/username`，仅用于快照归属。
- **前端不 fork etrader 业务**：只借鉴 XC 设计体系与框架层写法；不引入 ecenter 登录、不带 `systemSign`。
- **后端不抄 trader 后端/鉴权代码**：仅框架选型（FastAPI/SQLAlchemy/Nacos）与团队一致，实现自研。
- **飞书方案A**：系统只读写接口区 `API_INPUT/API_OUTPUT/API_META`，绝不直接读写模型单元格；`API_OUTPUT`（标量/表格输出）与 `画图数据`（专供前端图表的序列，如偿债倍数）是仅有的两个允许读取的输出区域。

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

## 5. Python 解释器约定

不要直接用 `python`/`python3`（PATH 里没有）。优先级：
1. 项目 venv：Windows `agent-backend\.venv\Scripts\python.exe`；\*nix `agent-backend/.venv/bin/python`。
2. 系统 Python 3.13：`C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe`。

## 6. 常用命令

### 后端（在 `agent-backend/` 目录）

```bash
# 依赖安装见第 4 节；不要绕过统一依赖文件手动装包
.venv\Scripts\python.exe -m pytest                                        # 全部测试；纯逻辑单测走内存 sqlite，tests/db/* 连测试库 ir_agent 真实留痕
.venv\Scripts\python.exe -m pytest tests/unit/calculation/test_param_dictionary.py -q   # 单个测试文件
.venv\Scripts\python.exe -m pytest -k test_dictionary_loads -q            # 按用例名跑单个测试
.venv\Scripts\python.exe -m app.main                                      # 启动服务（连测试库）；main.py 内置入口，可 IDE F5 调试
```

> 建表：手动在 `ir_agent` 库执行 `sql/ir_agent_schema.sql`（DDL 由 ORM 生成，本项目不用 Alembic 做建表迁移）。
> **必须从 `agent-backend` 目录以模块方式运行**（`-m app.main`），或把 IDE 工作目录设为 `agent-backend`；否则绝对导入 `from app.core...` 会报 `ModuleNotFoundError: app`。

### 前端（在 `agent-frontend/` 目录）

```bash
pnpm install
pnpm dev                                          # http://localhost:5210，/gateway/* 代理到本地后端
pnpm test                                         # vitest run，全部测试一次性跑完
pnpm vitest run tests/calc-flow.spec.js           # 单个测试文件
pnpm vitest run -t "polls a non-terminal task"    # 按用例名跑单个测试
pnpm build
```

联调两侧：终端 A 起后端（`uvicorn app.main:app --reload --port 8080` 或 `-m app.main`），终端 B `pnpm dev`；代理目标在 `vite.config.js` 的 `server.proxy` 配，后端端口改了同步改 `.env` 的 `VITE_DEV_BACKEND`。

## 7. 后端架构（DDD 分层 + 限界上下文）

```text
agent-backend/
  app/
    main.py                # 应用入口（暴露 app + 本地直跑），组装逻辑在 infrastructure/web
    core/                  # 跨上下文基础能力：配置、常量、异常、{code,msg,data} 统一响应壳
    infrastructure/        # 技术基础设施：database（ORM 基类 + 异步引擎/会话）/ nacos / web（app_factory、deps、中间件、路由注册）
    modules/                # 限界上下文按模块隔离
      platform_access/     # 平台接入上下文：请求头身份读取（CurrentUser）、GET /ir/me
        domain/            # 领域模型
        interface/         # FastAPI router / deps(get_current_user) / middleware
      calculation/         # 测算上下文（核心业务）：参数字典、参数组装、飞书测算适配
        domain/            # 领域模型、领域服务、端口(ports)、参数字典 —— 不依赖 FastAPI/DB/HTTP
        application/       # 用例编排：param_assembler、task_service、snapshot_service、factory（组合根）
        infrastructure/    # 仓储、静态数据文件（param_dict.json、revenue_structure.json）、飞书客户端、现货电价 provider
        interface/         # FastAPI router（/ir/calc/*、/ir/conversations/*）
  tests/
    unit/                  # 领域/架构守护等快速测试
    integration/           # 模块内集成测试
    e2e/                   # ASGI 端点级测试
```

依赖方向：`interface → application → domain`；`domain` 不依赖 FastAPI、数据库或外部服务；`infrastructure` 实现 `domain/ports.py` 声明的端口。架构路径由 `tests/unit/test_architecture_layout.py`（一份期望可导入模块路径清单）守护；调整目录/模块名时同步更新该测试、`agent-backend/README.md` 和本节。

### `calculation` 上下文的真实流程

飞书电子表格是唯一权威计算器，本系统**不重写财务公式**。一次测算任务的流程：

1. **参数组装**（`param_assembler.py`）按顺序合并四来源写入一份 `api_input`：①对话抽取的基础信息（省份/容量/功率/节点/电压）②系统默认值（参数字典）③现货电价查表（`SpotPriceAlgo` 端口）——2026-07 确认规则：若是重新测算且节点/容量/功率/日循环次数相对上一个已完成版本的冻结入参**未变化**，则沿用该版本的现货电价并叠加用户本次的手工修改；若任一项**变化**，则重新查表，并**忽略**本次提交的陈旧现货电价覆盖 ④按省表2 市场开关与两档收益插值计算（容量/功率变化时同理重算、忽略陈旧覆盖）⑤中长期电价常量。最后一步**受控覆盖**：只接受参数字典中标记 `g=1, direction=input, writable=true` 的参数生效，未知/输出项/null 值一律忽略，**省份永远不可被覆盖**（一旦在会话中确定即锁定）。
2. **执行**（`feishu_calc_engine.py` 状态机 + `retry_policy.py`）复制飞书底稿副本、写入 `API_INPUT`/`API_META`、轮询等算完成、读取 `API_OUTPUT`（含 `画图数据` 区，如偿债倍数序列），并校验 `request_id`/参数哈希防止读到串号/旧值；失败按**可重试**（超时、5xx、429、request_id 不匹配）与**不可重试**（401/403、模板缺失、参数非法）分类——见 `RetryPolicy`/`classify_error`。
3. **落快照**（`snapshot_service.py`）每次成功测算独立落 7 类快照（不覆盖）到 MySQL `ir_agent`：会话、消息、任务、入参快照、数据快照、飞书I/O快照、结果快照。`report_snapshot` 刻意做到自给自足——历史/结果展示只读它，即使飞书副本被清理，历史结果依然可查看。

参数字典（`infrastructure/data/param_dict.json`）是唯一的数据契约：每个字段标注来源于四来源中的哪一个、是否用户可调（`g`）、飞书单元格映射，以及（供前端参数调整面板用的）`zone`/`control`/`min`/`max`/`step` 元数据。通过 `ParamDictionary`/`ParamSpec`（`domain/param_dictionary.py`）加载——把它当 schema 用，不要绕过它写死查表。

多版本会话：同一 `conversation_id` 反复 `POST /ir/calc/tasks` 会追加版本（V1、V2……）；`task_service.py` 的 `_resolve_version` 取最新**已完成**版本的冻结 `input_snapshot`，同时用于校验省份锁定和判断上面提到的现货电价/两档收益"依赖是否变化"。

现货电价本身是离线预计算查表，不是实时计算：`tools/spot_precompute.py` 按省/节点逐日跑一次多循环 DP，把结果落进 `ir_spot_daily_optimal_province/node` 表；`PrecomputeSpotPriceAlgo` 查询时只是对滚动一年窗口求和、乘以省级修正系数（系数在查询时应用，改配置即热更新，不用重算）。日更调度细节见 `agent-backend/README.md`"现货电价"一节。

## 8. 前端架构

详见 `agent-frontend/CLAUDE.md`。一句话概括：`store/modules/calculation.js` 驱动一个类聊天流程——从自由文本抽取最小输入 → `POST /ir/calc/tasks` → 轮询 → 拉结果 → 追加为一个版本；现在同一个 store 还驱动 inline 参数重新调整（`recalculate()`）和跨会话历史回放（`openConversation()`），都统一走同一套提交-轮询-拉结果-追加的 `_submitAndTrack` 辅助方法。

## 9. 跨两侧的公共约定

- 响应壳统一为 `{code, msg, data}`（后端 `core/response.py` + `core/exceptions.py` 的四类异常处理器）；前端 `utils/request.js` 负责解壳。校验失败统一走 HTTP 400（`ValidationException`/Pydantic `RequestValidationError`），不是 422/500。
- 身份是"信任式"而非令牌式：`PlatformIdentityMiddleware` 从可配置 header（`platform.header_user_id/username`，默认 `X-User-Id`/`X-User-Name`）读取 `user_id`/`username`，写入 `request.state`，仅用于快照/会话归属。全仓库没有任何 session、JWT 或密码逻辑。
- 会话软删除（`ConversationORM.deleted_at`），从不硬删除；历史读取、删除、任务状态/结果查询均按当前用户 id 过滤，非本人资源一律返回 404（不是 403），避免暴露资源是否存在。

## 10. 踩坑记录（实测得来，避免重蹈）

### 10.1 后端测试必须用 httpx ASGITransport，不要用 Starlette TestClient
- **现象**：`TestClient` 触发 SQLAlchemy 异步引擎时报
  `ValueError: the greenlet library is required ... DLL load failed while importing _greenlet: 应用程序控制策略已阻止此文件`。
- **根因**：本机存在**应用管控策略（AppLocker/WDAC 类）**，`TestClient` 用 anyio 起**后台线程**跑事件循环，
  greenlet 的 C 扩展 `.pyd` 在新线程**首次动态加载**时被策略偶发拦截。主线程/独立脚本加载则正常。
- **对策**：测试统一用 `httpx.ASGITransport` + `AsyncClient` 在**主事件循环**内直连 ASGI 应用（FastAPI 官方异步测试写法）；
  `pytest.ini` 设 `asyncio_mode = auto`。**新增测试请照此写，勿用 TestClient。**
- **写法**：`AsyncClient` 本身就是异步上下文管理器；helper/fixture 应同步返回或 yield 配好的客户端，不要让调用方写
  `async with await _client() as client`。仍需保留 `ASGITransport(app=app)`，否则请求不会路由到本地 ASGI 应用。

### 10.2 HTTP header 只能 ASCII —— 平台传中文用户名要先编码
- **现象**：往 header 塞中文（如用户名"张三"）→ httpx 报 `UnicodeEncodeError: 'ascii' codec can't encode`。
- **约定**：平台/网关若在 header 传中文 `username`，须由**平台侧** URL-encode 或 Base64；本系统解码读取。
  确切 header 字段名 + 中文编码方式属**平台对接约定**（见第 11 节），待与平台确认。

### 10.3 配置路径：settings 的 CONFIG_DIR 要退到 agent-backend 根
- `app/core/config/settings.py` 距 `configs/application.yml` 为 **4 层** `dirname`（config→core→app→agent-backend）。
- 少退一层会静默"配置文件不存在，使用默认值"——启动看似正常但读不到 yml。改动配置加载路径时注意。

## 11. 平台对接待确认项（不阻塞开发）

- 平台/网关注入身份的**确切 header 字段名**（默认占位 `X-User-Id` / `X-User-Name`，可经 Nacos/env 覆盖 `platform.header_user_id/username`）。
- 平台跳转进入本系统的**入口 URL**。
- header 缺失时的期望行为（当前：`platform.allow_anonymous=true` 时降级匿名占位，便于本地联调）。
- 中文 `username` 的编码方式（见 10.2）。

## 12. 配置分层

- 前端 `.env.*` 仅：`VITE_APP_BASE_API`（网关基地址）/`VITE_APP_TITLE`/`VITE_FAVICON`/`VITE_APP_ENV`。
- 后端：本地 `configs/application.yml` + `.env`；生产敏感项（数据源、飞书凭证、轮询阈值、header 字段名）走 **Nacos**。
  - **应用启动/联调/集成**：默认连**测试库** `mysql+aiomysql://example_user:example_password@database.example.invalid:3306/ir_agent`（密码写在 yml，正式走 Nacos）。
  - **纯逻辑单测（pytest）**：`tests/conftest.py` 用 `IR_DB_URL` 覆盖为内存 sqlite，不连真库；**DB 相关测试**另走 `tests/db/conftest.py` 直连测试库 `ir_agent`，真实插入、留痕不清理（测试行标记 `username='__pytest__'` 便于筛/清）。
  - 配置优先级：环境变量 `IR_DB_URL` > `application.yml` > 代码默认值。
  - MySQL 异步驱动用 `aiomysql`（纯 Python，Windows 免编译）；URL 前缀 `mysql+aiomysql://`，**不是** Java 的 `jdbc:mysql://`。
  - 连库前提：`internal-3-60.example.invalid` 上需已有 `ir_agent` 库（`CREATE DATABASE ir_agent DEFAULT CHARSET utf8mb4;`）；**建表手动执行 `sql/ir_agent_schema.sql`**（DDL 由 ORM 生成，本项目不用 Alembic 迁移）。
