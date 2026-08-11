import importlib
import sys
from types import SimpleNamespace

import pytest


MODULE_NAME = "tools.policy_ask"


def _settings():
    feishu = SimpleNamespace(
        app_id="cli-test",
        app_secret="secret",
        index_token="index-token",
        # 必须覆盖 tools.policy_ask._REQUIRED_PROVINCES 的全部省份，
        # 少一个就会在 import 时抛 RuntimeError；该常量扩省时同步这里。
        province_tokens={"蒙西": "mx", "宁夏": "nx", "甘肃": "gs", "陕西": "sx", "山西": "sax"},
        cross_province_token="",
        domain="feishu.example.test",
    )
    llm = SimpleNamespace(
        base_url="https://llm.example.test",
        api_key="llm-key",
        model="test-model",
    )
    anysearch = SimpleNamespace(api_key="", tavily_api_key="")
    base = SimpleNamespace(token="", table="")
    return SimpleNamespace(
        policy_ask=SimpleNamespace(feishu=feishu, llm=llm, anysearch=anysearch, base=base)
    )


def _import_with_settings(monkeypatch, settings):
    monkeypatch.setattr("app.core.config.settings.get_settings", lambda: settings)
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


@pytest.fixture(autouse=True)
def clear_policy_ask_module():
    sys.modules.pop(MODULE_NAME, None)
    yield
    sys.modules.pop(MODULE_NAME, None)


def test_policy_ask_maps_values_from_settings(monkeypatch):
    module = _import_with_settings(monkeypatch, _settings())

    assert module.APP_ID == "cli-test"
    assert module.PROVINCES == {"蒙西": "mx", "宁夏": "nx", "甘肃": "gs", "陕西": "sx", "山西": "sax"}
    assert module.LLM_API_KEY == "llm-key"
    assert module.ANYSEARCH_API_KEY == ""
    assert module.FEISHU_DOMAIN == "feishu.example.test"


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
