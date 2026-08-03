# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

先读仓库根 `CLAUDE.md` 获取跨端身份、飞书、快照和 Git 约束。本文件只描述 `agent-backend/` 的实际实现。

## 常用命令

从 `agent-backend/` 执行。依赖只通过 `requirements.txt` 管理；不要调用 `python` / `python3`，优先使用项目虚拟环境。

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.main
.venv\Scripts\python.exe run.py  # 读取 ENV_FILE，默认 .env.test；默认端口 9089
```

当前环境启动 Python 时 `sys.stdout` 可能为 `None`，且仓库没有 pytest 配置文件；测试统一使用包装并显式启用 async 模式：

```bash
# 全量
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"

# 单文件
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py', '-q', '-o', 'asyncio_mode=auto']))"

# 单测试
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py::test_dictionary_loads', '-q', '-o', 'asyncio_mode=auto']))"
```

虚拟环境不可用时才使用 `C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe`。当前没有独立 lint 配置或 lint 命令。

## 组合根与模块边界

`app/main.py` 是 FastAPI 组合根：注册异常处理、CORS、请求日志、平台身份中间件和各业务 Router。lifespan 依次初始化 Nacos、日志、数据库，恢复中断的报告任务，启动现货日调度和政策问答预热；关闭时逆向释放这些资源。

`app/modules/` 有七个业务上下文：

- `platform_access`：固定 Header 身份与 `/ir/me`。
- `calculation`：参数、飞书测算、会话、快照和现货预计算。
- `middle_platform`：`/ir/chat/diag` 中台 SSE 代理及会话映射。
- `report`：报告任务、AI 分析、快照和进度 SSE。
- `tie_line_map`：联络线列表、详情、功率导入与趋势。
- `index_map`：指数周期、总览和省级详情。
- `policy_market`：市场资讯、咨询记录、AI 咨询与启动预热。

模块按需采用 `interface → application → domain`，`infrastructure` 实现数据库、HTTP、飞书等外部适配器。`domain` 不得 import FastAPI、SQLAlchemy、httpx 或飞书 SDK。目录和导入边界由 `tests/unit/test_architecture_layout.py` 守护；移动模块时同步更新该测试。

## 通用 Web 契约

- `app/core/response.py` 统一 `{code, msg, data}`；`app/core/exceptions.py` 将请求模型和业务校验错误映射为 HTTP 400。
- `PlatformIdentityMiddleware` 仅放行 `/docs`、`/redoc`、`/openapi.json`、`/health`；其他请求缺少 `userId` 或 `username` 即返回 401。`username` 在中间件中 URL 解码后写入 `request.state`。
- 测算会话标识请求头统一为网关安全的 `X-IR-Conversation-Id`；`/ir/chat/diag` 请求体中的 `conversation_id` 仍是 JSON 字段。
- 后端不验证平台 Token，也不添加登录、用户表、RBAC、JWT 或匿名身份。按用户查询不到会话、任务、报告或咨询时返回 404。
- 端点测试使用 `httpx.ASGITransport + AsyncClient`，不用 Starlette `TestClient`。HTTP Header 必须是 ASCII；测试中文用户名时先 URL 编码。

## 测算与快照

1. `ParamAssembler` 按“对话基础参数 → 参数字典默认值 → 现货价格查询/继承 → 省份收益结构 → 中长期常量 → 受控覆盖”生成冻结 `api_input`。
2. `CalculationTaskService` 选择 15/20 年模板；`FeishuCalcEngine` 复制模板、写 `API_INPUT`、轮询 `API_META`、读取 `API_OUTPUT`，并校验 `request_id` 与参数 hash。
3. `SnapshotService` 持久化成功版本；历史详情和报告只读快照，不重新访问飞书。

`app/modules/calculation/infrastructure/data/param_dict.json` 是参数的唯一契约。覆盖值只接受 `g=1`、`direction=input`、`writable=true` 的条目；未知、输出和 null 值按现有规则忽略。province 在同一会话中固定；仅当节点、容量、功率或日循环次数变化时重算现货价格，否则继承冻结价格对。

`operation_years` 只允许整数 15/20，并由 `CalculationTaskService._template_token_for()` 选择固定模板。它保留在入参与快照中，但 `HttpFeishuGateway.write_input()` 必须跳过它，不得写入 `API_INPUT`。每次成功测算追加版本；一次副本复制失败重试时复用同一文档 Token。

## 报告及其他后台流程

- `POST /ir/calc/tasks/{taskId}/report` 以 task 为幂等边界；报告任务经历 `generating/completed/failed`，进度由 `/ir/report-tasks/{id}/events` 推送。报告内容写不可变 JSON 快照，服务启动时把中断的 generating 任务标记 failed。
- 报告 AI 分节并发生成；上游或校验失败时使用已有降级文本，不影响规则化数据和图表展示。
- 现货预计算和每日调度位于 calculation infrastructure；政策咨询预热在 policy_market infrastructure。它们都由应用 lifespan 管理，不要在 Router 导入时启动后台任务。
- 中台聊天服务负责转发 SSE 和维护用户/中台 session 关联；测算业务仍由 calculation 模块完成，不在代理层复制参数解析。

## 配置与数据库

- 配置优先级为代码默认值 → `configs/application.yml` → `IR_*` 环境变量 → Nacos 业务节点。应用、日志、CORS、Nacos 自身配置不由 Nacos 反向覆盖。
- `settings.py` 从 `app/core/config/` 向上定位 `configs/application.yml`；修改路径逻辑可能使服务静默回退到默认值。
- `sql/ir_agent_schema.sql` 用于手工创建完整 schema；`migrations/versions/` 当前有 3 个增量 Alembic revision。修改 ORM 时同时更新手工 DDL、必要的增量 migration、快照读写和历史兼容。
- 普通测试由 `tests/conftest.py` 使用内存 SQLite；`tests/db/` 会连接真实测试数据库并写记录，不能当作纯单元测试运行。
