# Codex 云端执行规范

本文件适用于整个仓库。进入 `agent-backend/` 或 `agent-frontend/` 前，还必须阅读对应目录的 `CLAUDE.md`；其中的局部架构约定与本文件互补。根目录 `CLAUDE.md` 中的身份与请求边界、飞书权威计算、参数字典、历史快照及工程约束均为强制约束，不得因云端执行而绕过。

## 安全边界

- 不连接真实飞书、中台、Nacos、现货或数据库服务，不读取或提交真实凭据。
- 云端验证固定关闭外部服务，并使用内存 SQLite。不得运行 `agent-backend/tests/db/`。
- 不修改业务逻辑、测试断言或锁文件来使环境验证通过；已知身份请求头差异应如实记录并单独处理。
- 不合并、部署、调整权限或重写 Git 历史。提交与发布仅在任务明确授权时执行。

## 受支持的 Linux 工具链

- Python 3.13（由根目录 `.python-version` 声明）。后端命令只使用 `agent-backend/.venv/bin/python`。
- Node.js 22（由根目录 `.nvmrc` 声明）及 `agent-frontend/package.json` 声明的 npm。前端只使用 npm。
- 从仓库根目录运行 `./scripts/cloud-init.sh`，只从 `requirements.txt` 和 `package-lock.json` 安装依赖。

## 云端验证

从仓库根目录运行：

```bash
./scripts/cloud-check.sh
```

脚本设置以下隔离环境，并依次运行后端单元测试、前端测试和前端构建；即使某项失败也会继续运行其余检查，逐项打印退出码，最终在任一检查失败时返回非零：

```text
NACOS_ENABLED=false
IR_FEISHU_ENABLED=false
IR_SPOT_ENABLED=false
IR_SPOT_DAILY_UPDATE_ENABLED=false
IR_DB_URL=sqlite+aiosqlite:///:memory:
```

若需单独排查，可使用脚本中的原始命令。后端检查从 `agent-backend/` 执行，范围仅为 `tests/unit`，不得擅自扩大到 `tests/db`。
