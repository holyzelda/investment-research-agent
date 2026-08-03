# 政策问答统一 Nacos 配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `tools/policy_ask.py` 使用统一 `Settings` 配置，使本地读取 YAML、测试/生产启动后读取对应 Nacos profile 的覆盖值。

**Architecture:** 在 `settings.py` 新增嵌套 Pydantic 模型并将 `policy_ask` 纳入 `_build_settings()` 的已深度合并配置。策略脚本仅将 `get_settings().policy_ask` 映射为既有常量，并在导入期校验业务必填字段；现有 Nacos 初始化完成后才启动脚本预热，因此不需要脚本读取 Nacos 缓存或判断运行环境。

**Tech Stack:** Python 3、Pydantic、PyYAML、pytest、现有 Nacos 配置客户端。

---

## 文件结构

- 修改 `agent-backend/app/core/config/settings.py`：定义 `PolicyAsk*Config` 模型，将本地 YAML/Nacos 合并结果构造成 `Settings.policy_ask`。
- 修改 `agent-backend/tools/policy_ask.py`：移除自主 YAML 读取，改为读取 `get_settings().policy_ask` 并校验必填业务字段。
- 修改 `agent-backend/tests/unit/test_settings.py`：覆盖本地值的暴露与 Nacos 覆盖优先级。
- 修改 `agent-backend/tests/unit/tools/test_policy_ask_config.py`：覆盖 Settings 到脚本常量的映射和配置缺失的导入期错误。
- 修改 `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py`：在真实 Nacos 初始化路径中验证 `policy_ask` 覆盖。

### Task 1: 为 Settings 的 policy_ask 模型编写失败测试

**Files:**
- Modify: `agent-backend/tests/unit/test_settings.py:58-69`
- Modify: `agent-backend/app/core/config/settings.py:224-343`

- [ ] **Step 1: 在 `test_settings.py` 的 `test_nacos_business_configuration_overrides_explicit_business_environment` 后追加 Nacos 覆盖测试**

```python

def test_nacos_overrides_policy_ask_configuration():
    settings_module.set_nacos_overrides({
        "policy_ask": {
            "feishu": {"app_id": "remote-policy-app"},
            "llm": {"api_key": "remote-policy-key"},
        }
    })

    settings = reload_settings()

    assert settings.policy_ask.feishu.app_id == "remote-policy-app"
    assert settings.policy_ask.llm.api_key == "remote-policy-key"
    assert settings.policy_ask.feishu.index_token
    assert settings.policy_ask.llm.model

    settings_module.clear_nacos_overrides()
    get_settings.cache_clear()
```

- [ ] **Step 2: 运行测试并确认它因缺少 `policy_ask` 属性失败**

从 `agent-backend/` 运行：

```bash
..\.mypython\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\test_settings.py::test_nacos_overrides_policy_ask_configuration', '-q']))"
```

预期：失败，提示 `Settings` 没有 `policy_ask` 属性。

- [ ] **Step 3: 在 `settings.py` 的 `SpotPriceConfig` 后定义政策问答配置模型**

```python
class PolicyAskFeishuConfig(BaseModel):
    app_id: str = ""
    app_secret: str = ""
    index_token: str = ""
    province_tokens: dict[str, str] = Field(default_factory=dict)
    cross_province_token: str = ""


class PolicyAskLlmConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class PolicyAskAnysearchConfig(BaseModel):
    api_key: str = ""


class PolicyAskBaseConfig(BaseModel):
    token: str = ""
    table: str = ""


class PolicyAskConfig(BaseModel):
    feishu: PolicyAskFeishuConfig = Field(default_factory=PolicyAskFeishuConfig)
    llm: PolicyAskLlmConfig = Field(default_factory=PolicyAskLlmConfig)
    anysearch: PolicyAskAnysearchConfig = Field(default_factory=PolicyAskAnysearchConfig)
    base: PolicyAskBaseConfig = Field(default_factory=PolicyAskBaseConfig)
```

在 `Settings` 中增加：

```python
    policy_ask: PolicyAskConfig = Field(default_factory=PolicyAskConfig)
```

在 `_build_settings()`、构造 `spot_price` 后添加：

```python
    _pad = PolicyAskConfig()
    policy_ask = PolicyAskConfig(
        feishu=PolicyAskFeishuConfig(
            app_id=_nested(y, ["policy_ask", "feishu", "app_id"], _pad.feishu.app_id),
            app_secret=_nested(y, ["policy_ask", "feishu", "app_secret"], _pad.feishu.app_secret),
            index_token=_nested(y, ["policy_ask", "feishu", "index_token"], _pad.feishu.index_token),
            province_tokens=_nested(y, ["policy_ask", "feishu", "province_tokens"], _pad.feishu.province_tokens),
            cross_province_token=_nested(y, ["policy_ask", "feishu", "cross_province_token"], _pad.feishu.cross_province_token),
        ),
        llm=PolicyAskLlmConfig(
            base_url=_nested(y, ["policy_ask", "llm", "base_url"], _pad.llm.base_url),
            api_key=_nested(y, ["policy_ask", "llm", "api_key"], _pad.llm.api_key),
            model=_nested(y, ["policy_ask", "llm", "model"], _pad.llm.model),
        ),
        anysearch=PolicyAskAnysearchConfig(
            api_key=_nested(y, ["policy_ask", "anysearch", "api_key"], _pad.anysearch.api_key),
        ),
        base=PolicyAskBaseConfig(
            token=_nested(y, ["policy_ask", "base", "token"], _pad.base.token),
            table=_nested(y, ["policy_ask", "base", "table"], _pad.base.table),
        ),
    )
```

将返回语句修改为：

```python
    return Settings(
        app=app, log=log, database=database, nacos=nacos, cors=cors,
        calc=calc, middle_platform=middle_platform, feishu=feishu,
        spot_price=spot_price, policy_ask=policy_ask,
    )
```

- [ ] **Step 4: 运行新增单元测试并确认通过**

重复 Step 2 的命令。

预期：1 个测试通过。

- [ ] **Step 5: 不执行 Git 提交**

遵守项目规则，不运行 `git add`、`git commit` 或 `git push`。

### Task 2: 用 Settings 驱动 policy_ask 并保留必填校验

**Files:**
- Modify: `agent-backend/tests/unit/tools/test_policy_ask_config.py:1-98`
- Modify: `agent-backend/tools/policy_ask.py:7-103`

- [ ] **Step 1: 用模块导入测试替换现有 YAML 辅助函数测试**

将 `test_policy_ask_config.py` 替换为：

```python
import importlib
import sys
from types import SimpleNamespace

import pytest


MODULE_NAME = "tools.policy_ask"


def _settings(**overrides):
    feishu = SimpleNamespace(
        app_id="cli-test",
        app_secret="secret",
        index_token="index-token",
        province_tokens={"蒙西": "mx", "宁夏": "nx", "甘肃": "gs"},
        cross_province_token="",
    )
    llm = SimpleNamespace(
        base_url="https://llm.example.test",
        api_key="llm-key",
        model="test-model",
    )
    anysearch = SimpleNamespace(api_key="")
    base = SimpleNamespace(token="", table="")
    policy_ask = SimpleNamespace(feishu=feishu, llm=llm, anysearch=anysearch, base=base)
    for key, value in overrides.items():
        setattr(policy_ask, key, value)
    return SimpleNamespace(policy_ask=policy_ask)


def _import_with_settings(monkeypatch, settings):
    monkeypatch.setattr("app.core.config.settings.get_settings", lambda: settings)
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def test_policy_ask_maps_values_from_settings(monkeypatch):
    module = _import_with_settings(monkeypatch, _settings())

    assert module.APP_ID == "cli-test"
    assert module.PROVINCES == {"蒙西": "mx", "宁夏": "nx", "甘肃": "gs"}
    assert module.LLM_API_KEY == "llm-key"
    assert module.ANYSEARCH_API_KEY == ""


def test_policy_ask_rejects_missing_llm_api_key(monkeypatch):
    settings = _settings()
    settings.policy_ask.llm.api_key = ""

    with pytest.raises(RuntimeError, match=r"policy_ask\.llm\.api_key"):
        _import_with_settings(monkeypatch, settings)


def test_policy_ask_rejects_missing_province_token(monkeypatch):
    settings = _settings()
    del settings.policy_ask.feishu.province_tokens["甘肃"]

    with pytest.raises(RuntimeError, match=r"policy_ask\.feishu\.province_tokens\.甘肃"):
        _import_with_settings(monkeypatch, settings)
```

并在每个测试结束前增加 `sys.modules.pop(MODULE_NAME, None)` 清理，避免模块全局状态泄露。

- [ ] **Step 2: 运行测试并确认因脚本仍读取本地 YAML 而失败**

从 `agent-backend/` 运行：

```bash
..\.mypython\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\tools\test_policy_ask_config.py', '-q']))"
```

预期：失败，原因是 `tools.policy_ask` 尚未从 `get_settings()` 映射配置。

- [ ] **Step 3: 移除脚本的 YAML 文件加载，改用 `get_settings().policy_ask`**

在 `tools/policy_ask.py` 删除：

```python
import yaml
```

并添加：

```python
from app.core.config.settings import get_settings
```

删除 `CONFIG_PATH`、`_read_policy_ask_config()` 以及 YAML 解析相关代码。保留 `_REQUIRED_PROVINCES`，将 `_required_config_value` 替换为：

```python
def _required_config_value(value, path):
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"政策问答配置缺少必填项：policy_ask.{path}")
    return value.strip()
```

将常量初始化替换为：

```python
_policy_ask = get_settings().policy_ask

APP_ID = _required_config_value(_policy_ask.feishu.app_id, "feishu.app_id")
APP_SECRET = _required_config_value(_policy_ask.feishu.app_secret, "feishu.app_secret")
INDEX_TOKEN = _required_config_value(_policy_ask.feishu.index_token, "feishu.index_token")
PROVINCES = {}
for _province in _REQUIRED_PROVINCES:
    _token = _policy_ask.feishu.province_tokens.get(_province)
    PROVINCES[_province] = _required_config_value(_token, f"feishu.province_tokens.{_province}")
CROSS_PROVINCE_TOKEN = str(_policy_ask.feishu.cross_province_token or "").strip()
ANYSEARCH_API_KEY = str(_policy_ask.anysearch.api_key or "").strip()
LLM_BASE_URL = _required_config_value(_policy_ask.llm.base_url, "llm.base_url")
LLM_API_KEY = _required_config_value(_policy_ask.llm.api_key, "llm.api_key")
LLM_MODEL = _required_config_value(_policy_ask.llm.model, "llm.model")
BASE_TOKEN = str(_policy_ask.base.token or "").strip()
BASE_TABLE = str(_policy_ask.base.table or "").strip()
```

- [ ] **Step 4: 运行策略脚本配置测试并确认通过**

重复 Step 2 命令。

预期：3 个测试通过。

- [ ] **Step 5: 不执行 Git 提交**

不执行 Git 写操作。

### Task 3: 在 Nacos 初始化路径验证 policy_ask 覆盖

**Files:**
- Modify: `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py:53-85`
- Test: `agent-backend/tests/unit/test_settings.py`
- Test: `agent-backend/tests/unit/tools/test_policy_ask_config.py`
- Test: `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py`
- Test: `agent-backend/tests/unit/policy_market/test_policy_ask_loader.py`
- Test: `agent-backend/tests/unit/policy_market/test_policy_ask_executor.py`

- [ ] **Step 1: 扩展远端业务配置固定夹具并断言最终 policy_ask 值**

在 `FakeNacosClient` 的 YAML 内容里增加：

```yaml
policy_ask:
  feishu:
    app_id: remote-policy-app
  llm:
    api_key: remote-policy-key
```

并在现有飞书断言后追加：

```python
    assert settings.policy_ask.feishu.app_id == "remote-policy-app"
    assert settings.policy_ask.llm.api_key == "remote-policy-key"
    assert settings.policy_ask.feishu.index_token
    assert settings.policy_ask.llm.model
```

- [ ] **Step 2: 运行该集成测试并确认 Nacos 覆盖链路通过**

从 `agent-backend/` 运行：

```bash
..\.mypython\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([r'F:\qjcode\investment-research-agent\agent-backend\tests\integration\infrastructure\test_nacos_fallback.py::test_nacos_remote_business_config_has_highest_priority', '-q']))"
```

预期：1 个测试通过，且 Data ID 仍为 `ir-agent-test.yml`。

- [ ] **Step 3: 运行完整相关回归集**

从 `agent-backend/` 运行：

```bash
..\.mypython\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\test_settings.py', r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\tools\test_policy_ask_config.py', r'F:\qjcode\investment-research-agent\agent-backend\tests\integration\infrastructure\test_nacos_fallback.py', r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\policy_market\test_policy_ask_loader.py', r'F:\qjcode\investment-research-agent\agent-backend\tests\unit\policy_market\test_policy_ask_executor.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：全部通过。

- [ ] **Step 4: 验证本地配置冒烟导入**

从 `agent-backend/` 运行：

```bash
..\.mypython\Scripts\python.exe -c "import sys; import tools.policy_ask as policy_ask; assert set(policy_ask.PROVINCES) == {'蒙西', '宁夏', '甘肃'}; assert policy_ask.LLM_BASE_URL; assert policy_ask.LLM_API_KEY; print('policy_ask 通过统一 Settings 加载成功', file=sys.stderr)"
```

预期：输出 `policy_ask 通过统一 Settings 加载成功`，且不发起外部网络请求。

- [ ] **Step 5: 审查差异并保持未提交状态**

从仓库根目录运行：

```bash
git diff -- agent-backend/app/core/config/settings.py agent-backend/tools/policy_ask.py agent-backend/tests/unit/test_settings.py agent-backend/tests/unit/tools/test_policy_ask_config.py agent-backend/tests/integration/infrastructure/test_nacos_fallback.py
```

预期：仅包含配置模型、策略脚本配置来源和相关测试变动；不包含 Nacos Data ID、策略问答检索、LLM 请求或日志业务逻辑改动。不要执行 Git 写操作。
