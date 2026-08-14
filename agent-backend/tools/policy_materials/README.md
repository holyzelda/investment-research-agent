# 政策材料每日同步

该目录包含北极星政策材料抓取、Excel 校验入库和 crontab 定时执行入口。

## 目录职责

- `bjx_policy_news.py`：抓取指定日期的三个栏目并生成 Excel。
- `import_excel_to_db.py`：通过项目统一 `Settings` 获取 `database.url`，校验 Excel，按 `link_url` 跳过数据库已有记录并入库。
- `run_policy_sync.sh`：串联抓取、入库、归档和历史文件清理。
- `run_policy_sync_cron.sh`：加载项目现有 `.env.prod` 并记录日志，供 crontab 调用。

运行数据默认写入 `agent-backend/data/policy_materials`：

- `pending`：等待入库的 Excel。
- `imported/<日期>`：入库成功后归档的 Excel。
- `failed/<日期_时间>`：任务失败时保留的现场文件。

## 手动执行

进入后端目录并安装统一依赖：

```bash
python -m pip install -r requirements.txt
```

确认本地配置或 Nacos 中已配置 `database.url`，然后执行完整同步；默认处理昨日数据：

```bash
bash ./tools/policy_materials/run_policy_sync.sh
```

数据库连接串格式示例：

```yaml
database:
  url: mysql+aiomysql://example_user:example_password@database.example.invalid:3306/数据库名
```

入库脚本复用 `app/core/config/settings.py` 的统一配置入口。配置优先级与后端服务一致：默认值 → `configs/application.yml` → 业务环境变量 → Nacos 远端业务配置（最高优先级）。

当 `NACOS_ENABLED=true` 时，任务会在每次入库前读取 `${APP_NAME}-${NACOS_PROFILE}.yml`，并从合并后的 `Settings.database.url` 创建数据库连接。该一次性任务只加载配置，不向 Nacos 注册服务实例；任务结束后会关闭 Nacos 客户端。Nacos 不可用时，沿用项目现有策略回退到本地 YAML 和环境变量。

补跑指定日期：

```bash
POLICY_TARGET_DATE=2026-08-13 bash ./tools/policy_materials/run_policy_sync.sh
```

脚本使用 `flock` 防止同一台服务器上的任务重叠。重复执行同一天数据时，入库脚本会按 `link_url` 跳过已有记录。

## 历史文件清理

完整同步并归档成功后，脚本会自动执行以下清理：

- 删除 `pending` 中超过 3 天的 `.xlsx` 文件。
- 删除 `imported` 中超过 30 天的 `.xlsx` 文件，并移除清空后的日期目录。
- 删除 `failed` 中超过 90 天的失败目录及其中全部文件。

保留期限可以通过环境变量调整：

```bash
export POLICY_PENDING_RETENTION_DAYS=3
export POLICY_IMPORTED_RETENTION_DAYS=30
export POLICY_FAILED_RETENTION_DAYS=90
```

保留天数必须是大于或等于 0 的整数。清理失败会使本次任务返回失败，并保留日志供排查。

## 配置 crontab

以下命令假设项目部署在 `/opt/investment-research-agent`，任务使用 `iragent` 用户运行。先设置脚本执行权限：

```bash
cd /opt/investment-research-agent/agent-backend
chmod +x tools/policy_materials/run_policy_sync.sh
chmod +x tools/policy_materials/run_policy_sync_cron.sh
```

cron 入口默认加载后端现有的 `.env.prod`，与 `start_prod.sh` 使用同一套 Nacos 启动参数，不需要额外创建环境配置。需要在测试环境执行时设置 `ENV_FILE=.env.test`。

Python 解释器按以下顺序自动选择：环境变量 `PYTHON_BIN`、项目 `.venv/bin/python`、系统 `python3`、系统 `python`。通常不需要单独配置；如果依赖安装在其他虚拟环境中，可在现有 `.env.prod` 中设置 `PYTHON_BIN=/实际虚拟环境/bin/python`。

对应的 Nacos Data ID 为 `iresearch-agent-service-prod.yml`，其中应包含：

```yaml
database:
  url: mysql+aiomysql://example_user:example_password@database.example.invalid:3306/ir_agent
```

先使用实际运行用户手动验证一次：

```bash
sudo -u iragent /usr/bin/bash \
  /opt/investment-research-agent/agent-backend/tools/policy_materials/run_policy_sync_cron.sh
```

查看日志确认 Excel 抓取、入库和归档均成功：

```bash
tail -n 200 \
  /opt/investment-research-agent/agent-backend/data/policy_materials/logs/policy-sync-$(date +%Y-%m).log
```

验证成功后，编辑 `iragent` 用户的 crontab：

```bash
sudo -u iragent crontab -e
```

确认服务器时区为 `Asia/Shanghai` 后，加入以下内容。任务每天北京时间 `06:30` 执行，默认同步昨天的数据：

```cron
30 6 * * * /usr/bin/bash /opt/investment-research-agent/agent-backend/tools/policy_materials/run_policy_sync_cron.sh
```

保存后检查是否安装成功：

```bash
sudo -u iragent crontab -l
```

服务器应使用 `Asia/Shanghai` 时区，可通过 `timedatectl` 检查。脚本自身使用 `flock` 防止任务重叠；cron 不会补跑关机期间错过的任务，需要补跑时手动设置 `POLICY_TARGET_DATE`。爬虫详情页的本地浏览器代理在服务器上通常不存在，代理不可用时脚本会回退使用标题过滤关键词，不影响 Excel 生成。
