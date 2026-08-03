# 政策问答敏感配置外置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `tools/policy_ask.py` 中的飞书、知识库、LLM 与可选第三方服务敏感配置迁移至 `configs/application.yml` 的 `policy_ask` 节，并在导入时严格校验必填项。

**Architecture:** 在 `tools/policy_ask.py` 中增加一个只依赖 PyYAML 与标准库的配置加载函数，通过脚本相对路径固定定位 `agent-backend/configs/application.yml`。该函数将 YAML 的 `policy_ask` 映射标准化为既有模块常量所需值，必填项无效时立即抛出带路径和字段名的 `RuntimeError`；可选项为空时返回空字符串以保持原有禁用逻辑。

**Tech Stack:** Python 3、PyYAML、pytest、现有 `lark_oapi`、FastAPI 异步加载器。

---

## 文件结构

- 修改 `agent-backend/configs/application.yml`：增加 `policy_ask` 配置节，承载原脚本的敏感值和可选服务配置。
- 修改 `agent-backend/tools/policy_ask.py`：增加 YAML 配置读取/校验函数，用加载结果初始化既有常量，移除硬编码敏感值。
- 新建 `agent-backend/tests/unit/tools/test_policy_ask_config.py`：不导入飞书 SDK，直接加载脚本源码中的配置辅助函数并覆盖成功、必填项缺失、省份 Token 不完整、可选值为空四类场景。

### Task 1: 为配置加载行为建立失败测试

**Files:**
- Create: `agent-backend/tests/unit/tools/test_policy_ask_config.py`
- Modify: `agent-backend/tools/policy_ask.py:18-49`

- [ ] **Step 1: 创建测试目录与测试文件，编写配置载入函数的失败测试**

在 `agent-backend/tests/unit/tools/test_policy_ask_config.py` 写入：

```python
import ast
from pathlib import Path

import pytest
import yaml


POLICY_ASK_PATH = Path(__file__).parents[3] / "tools" / "policy_ask.py"


def _load_config_helpers():
    source = POLICY_ASK_PATH.read_text(encoding="utf-8")
    module = ast.parse(source)
    selected_nodes = [
        node for node in module.body
        if (isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_REQUIRED_PROVINCES"
            for target in node.targets
        )) or (isinstance(node, ast.FunctionDef) and node.name in {"_read_policy_ask_config", "_required_config_value"})
    ]
    helper_module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"Path": Path, "yaml": yaml}
    exec(compile(helper_module, str(POLICY_ASK_PATH), "exec"), namespace)
    return namespace["_read_policy_ask_config"]


def _valid_config():
    return {
        "policy_ask": {
            "feishu": {
                "app_id": "cli-test",
                "app_secret": "secret",
                "index_token": "index-token",
                "province_tokens": {"蒙西": "mx", "宁夏": "nx", "甘肃": "gs"},
                "cross_province_token": "",
            },
            "llm": {
                "base_url": "https://llm.example.test",
                "api_key": "llm-key",
                "model": "test-model",
            },
            "anysearch": {"api_key": ""},
            "base": {"token": "", "table": ""},
        }
    }


def _write_config(path, config):
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


def test_read_policy_ask_config_returns_required_and_optional_values(tmp_path):
    read_config = _load_config_helpers()
    config_path = tmp_path / "application.yml"
    _write_config(config_path, _valid_config())

    actual = read_config(config_path)

    assert actual["feishu"]["province_tokens"] == {"蒙西": "mx", "宁夏": "nx", "甘肃": "gs"}
    assert actual["feishu"]["cross_province_token"] == ""
    assert actual["anysearch"]["api_key"] == ""
    assert actual["base"] == {"token": "", "table": ""}


def test_read_policy_ask_config_rejects_missing_llm_api_key(tmp_path):
    read_config = _load_config_helpers()
    config = _valid_config()
    del config["policy_ask"]["llm"]["api_key"]
    config_path = tmp_path / "application.yml"
    _write_config(config_path, config)

    with pytest.raises(RuntimeError, match=r"policy_ask\.llm\.api_key"):
        read_config(config_path)


def test_read_policy_ask_config_rejects_missing_province_token(tmp_path):
    read_config = _load_config_helpers()
    config = _valid_config()
    del config["policy_ask"]["feishu"]["province_tokens"]["甘肃"]
    config_path = tmp_path / "application.yml"
    _write_config(config_path, config)

    with pytest.raises(RuntimeError, match=r"policy_ask\.feishu\.province_tokens\.甘肃"):
        read_config(config_path)
```

- [ ] **Step 2: 运行测试，确认当前实现尚未提供配置辅助函数**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tools/test_policy_ask_config.py', '-q']))"
```

预期：失败，原因是 AST 未找到 `_read_policy_ask_config` 或 `_required_config_value`，证明测试覆盖的是待实现接口。

- [ ] **Step 3: 实现最小的 YAML 配置加载与必填校验函数**

在 `agent-backend/tools/policy_ask.py` 的标准库 import 区增加：

```python
import yaml
```

将原有“飞书配置”“LLM 配置”的硬编码区替换为以下辅助函数和加载结果（`PROVINCES` 的赋值保留在该区域）：

```python
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "application.yml"
_REQUIRED_PROVINCES = ("蒙西", "宁夏", "甘肃")


def _required_config_value(config, path, config_path):
    current = config
    for key in path.split("."):
        if not isinstance(current, dict) or not isinstance(current.get(key), str) or not current[key].strip():
            raise RuntimeError(f"政策问答配置缺少必填项：{path}（配置文件：{config_path}）")
        current = current[key]
    return current.strip()


def _read_policy_ask_config(config_path):
    if not config_path.exists():
        raise RuntimeError(f"政策问答配置文件不存在：{config_path}")
    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(f"政策问答配置文件格式无效：{config_path}") from exc
    if not isinstance(raw_config, dict):
        raise RuntimeError(f"政策问答配置根节点必须是映射：{config_path}")

    policy_ask = raw_config.get("policy_ask")
    if not isinstance(policy_ask, dict):
        raise RuntimeError(f"政策问答配置缺少 policy_ask 节：{config_path}")

    feishu = policy_ask.get("feishu")
    llm = policy_ask.get("llm")
    if not isinstance(feishu, dict):
        raise RuntimeError(f"政策问答配置缺少 feishu 节：{config_path}")
    if not isinstance(llm, dict):
        raise RuntimeError(f"政策问答配置缺少 llm 节：{config_path}")

    province_tokens = feishu.get("province_tokens")
    if not isinstance(province_tokens, dict):
        raise RuntimeError(f"政策问答配置缺少 province_tokens 节：{config_path}")
    for province in _REQUIRED_PROVINCES:
        value = province_tokens.get(province)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"政策问答配置缺少必填项：policy_ask.feishu.province_tokens.{province}（配置文件：{config_path}）"
            )

    return {
        "feishu": {
            "app_id": _required_config_value(policy_ask, "feishu.app_id", config_path),
            "app_secret": _required_config_value(policy_ask, "feishu.app_secret", config_path),
            "index_token": _required_config_value(policy_ask, "feishu.index_token", config_path),
            "province_tokens": {province: province_tokens[province].strip() for province in _REQUIRED_PROVINCES},
            "cross_province_token": str(feishu.get("cross_province_token") or "").strip(),
        },
        "llm": {
            "base_url": _required_config_value(policy_ask, "llm.base_url", config_path),
            "api_key": _required_config_value(policy_ask, "llm.api_key", config_path),
            "model": _required_config_value(policy_ask, "llm.model", config_path),
        },
        "anysearch": {"api_key": str((policy_ask.get("anysearch") or {}).get("api_key") or "").strip()},
        "base": {
            "token": str((policy_ask.get("base") or {}).get("token") or "").strip(),
            "table": str((policy_ask.get("base") or {}).get("table") or "").strip(),
        },
    }
```

紧接其后添加：

```python
_POLICY_ASK_CONFIG = _read_policy_ask_config(CONFIG_PATH)
APP_ID = _POLICY_ASK_CONFIG["feishu"]["app_id"]
APP_SECRET = _POLICY_ASK_CONFIG["feishu"]["app_secret"]
INDEX_TOKEN = _POLICY_ASK_CONFIG["feishu"]["index_token"]
PROVINCES = _POLICY_ASK_CONFIG["feishu"]["province_tokens"]
CROSS_PROVINCE_TOKEN = _POLICY_ASK_CONFIG["feishu"]["cross_province_token"]
ANYSEARCH_API_KEY = _POLICY_ASK_CONFIG["anysearch"]["api_key"]
LLM_BASE_URL = _POLICY_ASK_CONFIG["llm"]["base_url"]
LLM_API_KEY = _POLICY_ASK_CONFIG["llm"]["api_key"]
LLM_MODEL = _POLICY_ASK_CONFIG["llm"]["model"]
BASE_TOKEN = _POLICY_ASK_CONFIG["base"]["token"]
BASE_TABLE = _POLICY_ASK_CONFIG["base"]["table"]
```

删除被上述赋值替代的所有硬编码 APP ID、APP Secret、Token、LLM URL/API Key/模型、`CROSS_PROVINCE_TOKEN`、`ANYSEARCH_API_KEY`、`BASE_TOKEN`、`BASE_TABLE` 定义；保留业务提示词、别名、关键字和缓存常量。

- [ ] **Step 4: 运行配置测试，确认全部通过**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tools/test_policy_ask_config.py', '-q']))"
```

预期：4 个测试通过。

- [ ] **Step 5: 不执行 Git 提交**

仓库 `CLAUDE.md` 明确要求未经用户授权不得执行 `git add`、`git commit`、`git push` 等 Git 写操作。本任务保持工作区改动，待用户另行要求时再处理提交。

### Task 2: 在 application.yml 声明政策问答配置

**Files:**
- Modify: `agent-backend/configs/application.yml:75`（在现有 `spot_price` 节之后追加）
- Test: `agent-backend/tests/unit/tools/test_policy_ask_config.py`

- [ ] **Step 1: 在 `application.yml` 追加独立 `policy_ask` 节**

在文件末尾追加以下结构，并将 `<从原 policy_ask.py 迁移的值>` 分别替换为改造前对应的实际值；不要改变现有任何配置节：

```yaml

policy_ask:
  # 政策与市场知识库问答：本地环境凭据；生产环境应由 Nacos/环境注入覆盖。
  feishu:
    app_id: "<从原 policy_ask.py 迁移的飞书 App ID>"
    app_secret: "<从原 policy_ask.py 迁移的飞书 App Secret>"
    index_token: "<从原 policy_ask.py 迁移的知识库索引 Token>"
    province_tokens:
      蒙西: "<从原 policy_ask.py 迁移的蒙西文档 Token>"
      宁夏: "<从原 policy_ask.py 迁移的宁夏文档 Token>"
      甘肃: "<从原 policy_ask.py 迁移的甘肃文档 Token>"
    cross_province_token: ""
  llm:
    base_url: "<从原 policy_ask.py 迁移的 LLM 服务地址>"
    api_key: "<从原 policy_ask.py 迁移的 LLM API Key>"
    model: "<从原 policy_ask.py 迁移的模型名>"
  anysearch:
    api_key: ""
  base:
    token: ""
    table: ""
```

- [ ] **Step 2: 以 PyYAML 解析实际配置文件并验证结构**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "from pathlib import Path; import yaml; config = yaml.safe_load(Path('configs/application.yml').read_text(encoding='utf-8')); policy_ask = config['policy_ask']; assert set(policy_ask['feishu']['province_tokens']) == {'蒙西', '宁夏', '甘肃'}; assert all(policy_ask['feishu']['province_tokens'].values()); assert all(policy_ask['llm'].values()); print('policy_ask 配置结构有效')"
```

预期：输出 `policy_ask 配置结构有效`。

- [ ] **Step 3: 运行配置单元测试，确认真实 YAML 结构与加载器契约一致**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tools/test_policy_ask_config.py', '-q']))"
```

预期：4 个测试通过。

- [ ] **Step 4: 不执行 Git 提交**

遵守仓库 Git 写操作限制；仅报告本任务形成的配置文件改动。

### Task 3: 验证延迟加载与策略问答适配器未回归

**Files:**
- Modify: `agent-backend/tools/policy_ask.py:18-49`
- Modify: `agent-backend/configs/application.yml:75`
- Test: `agent-backend/tests/unit/tools/test_policy_ask_config.py`
- Test: `agent-backend/tests/unit/policy_market/test_policy_ask_loader.py`
- Test: `agent-backend/tests/unit/policy_market/test_policy_ask_executor.py`

- [ ] **Step 1: 检查脚本中不再存在原敏感值的硬编码赋值**

从仓库根目录运行：

```bash
.venv\Scripts\python.exe -c "from pathlib import Path; text = Path('tools/policy_ask.py').read_text(encoding='utf-8'); forbidden = ('example-value-0063', 'example-value-0011', 'example-value-0013'); assert not any(value in text for value in forbidden); print('policy_ask.py 不含原敏感值')"
```

预期：输出 `policy_ask.py 不含原敏感值`。

- [ ] **Step 2: 运行配置、加载器和执行器测试**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/tools/test_policy_ask_config.py', 'tests/unit/policy_market/test_policy_ask_loader.py', 'tests/unit/policy_market/test_policy_ask_executor.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：全部通过，且加载器测试仍验证 `tools.policy_ask` 仅在后台预热/首次请求时导入。

- [ ] **Step 3: 对真实模块做导入级冒烟验证**

从 `agent-backend/` 运行：

```bash
.venv\Scripts\python.exe -c "import tools.policy_ask as policy_ask; assert policy_ask.PROVINCES.keys() == {'蒙西', '宁夏', '甘肃'}; assert policy_ask.LLM_BASE_URL; assert policy_ask.LLM_API_KEY; print('policy_ask 配置加载成功')"
```

预期：输出 `policy_ask 配置加载成功`，且不发起飞书、LLM、AnySearch 或 Base 网络请求。

- [ ] **Step 4: 汇总工作区改动但不执行 Git 写操作**

从仓库根目录运行：

```bash
git diff -- agent-backend/configs/application.yml agent-backend/tools/policy_ask.py agent-backend/tests/unit/tools/test_policy_ask_config.py
```

预期：差异只包括新增 `policy_ask` 配置、脚本配置加载/常量初始化，以及配置加载单元测试；不包含政策问答检索、LLM 请求、日志写入或异步预热行为修改。

- [ ] **Step 5: 不执行 Git 提交**

除非用户在该次请求中明确授权，否则不运行任何 Git 写操作。
