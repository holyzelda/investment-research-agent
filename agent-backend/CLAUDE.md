# CLAUDE.md

先读仓库根 `CLAUDE.md` 获取跨端身份、响应壳、飞书和快照等约束。本文件只描述后端的非显然实现约定。

## 常用命令

从 `agent-backend/` 执行。依赖只通过 `requirements.txt` 管理；不要调用 `python` / `python3`，优先使用项目虚拟环境。

Linux 使用 `.venv/bin/python`，Windows 将它替换为 `.venv\\Scripts\\python.exe`：

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.main
.venv/bin/python run.py  # 读取 ENV_FILE，默认 .env.test；默认端口 9089
```

Windows 环境启动 Python 时 `sys.stdout` 可能为 `None`，需使用包装并显式启用 async 模式。Linux 云端只运行 `tests/unit`，不得运行会连接数据库的 `tests/db`：

```bash
.venv/bin/python -m pytest tests/unit -q -o asyncio_mode=auto
.venv/bin/python -m pytest tests/unit/calculation/test_param_dictionary.py -q -o asyncio_mode=auto
```

Windows 对应命令使用项目虚拟环境的解释器，并保留 `sys.stdout` 包装：

```powershell
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit', '-q', '-o', 'asyncio_mode=auto']))"
```

虚拟环境不可用时才使用 `C:\Users\JDPC0200\AppData\Local\Programs\Python\Python313\python.exe`。当前没有独立 lint 配置或 lint 命令。

## 后端实现约定

- `domain` 不得 import FastAPI、SQLAlchemy、httpx 或飞书 SDK；移动模块时同步更新 `tests/unit/test_architecture_layout.py`。
- `PlatformIdentityMiddleware` 仅放行 `/docs`、`/redoc`、`/openapi.json`、`/health`；其他请求缺少 `userId` 或 `username` 即返回 401。`username` 在中间件中 URL 解码后写入 `request.state`。
- 测算会话标识请求头统一为网关安全的 `X-IR-Conversation-Id`；`/ir/chat/diag` 请求体中的 `conversation_id` 仍是 JSON 字段。
- 后端不验证平台 Token，也不添加登录、用户表、RBAC、JWT 或匿名身份。按用户查询不到会话、任务、报告或咨询时返回 404。
- 端点测试使用 `httpx.ASGITransport + AsyncClient`，不用 Starlette `TestClient`。HTTP Header 必须是 ASCII；测试中文用户名时先 URL 编码。

## 测算与快照

- `ParamAssembler` 的冻结 `api_input` 必须遵循现有组装顺序：对话基础参数、字典默认值、现货价格查询/继承、省份收益结构、中长期常量、受控覆盖。
- `CalculationTaskService` 按 15/20 年选择固定模板；`FeishuCalcEngine` 只操作允许区域，并校验 `request_id` 与参数 hash。
- `param_dict.json` 是参数唯一契约。覆盖值只接受 `g=1`、`direction=input`、`writable=true` 的条目；未知、输出和 null 值按现有规则忽略。province 在同一会话中固定；仅节点、容量、功率或日循环次数变化时重算现货价格，否则继承冻结价格对。
- `operation_years` 只允许整数 15/20；保留在入参与快照中，但 `HttpFeishuGateway.write_input()` 必须跳过它，不得写入 `API_INPUT`。复制失败重试时复用同一文档 Token。
- 历史详情和报告只读快照，不重新访问飞书；每次成功测算追加版本。

## 后台流程与数据库

- 报告任务以 task 为幂等边界，内容写不可变 JSON 快照；服务启动时把中断的 generating 任务标记 failed。进度由 SSE 推送，规则化数据和图表不因 AI 降级文本失败而丢失。
- 现货预计算、每日调度和政策咨询预热由应用 lifespan 管理，不要在 Router 导入时启动后台任务；中台代理只维护 SSE/session 映射，不复制测算参数解析。
- 配置优先级为代码默认值 → `configs/application.yml` → `IR_*` 环境变量 → Nacos 业务节点；应用、日志、CORS、Nacos 自身配置不由 Nacos 反向覆盖。修改 `settings.py` 的路径逻辑可能使服务静默回退到默认值。
- 修改 ORM 时同时更新 `sql/ir_agent_schema.sql`、`sql/` 下对应的增量 SQL、快照读写和历史兼容。普通测试使用内存 SQLite；`tests/db/` 仅由 GitHub Actions 的一次性 MySQL 服务运行，夹具在建表前校验精确 CI 地址和隔离开关。它会写入合成记录，不能当作纯单元测试运行，也不得连接现有数据库。
