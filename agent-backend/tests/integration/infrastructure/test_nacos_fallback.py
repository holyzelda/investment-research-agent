"""Nacos 配置装载、回退和服务发现的隔离测试。"""
import asyncio

import pytest

from app.core.config import settings as settings_module
from app.core.config.settings import get_settings, reload_settings
from app.infrastructure.nacos import client as nacos_module


class FakeNacosClient:
    def __init__(self, content: str | None):
        self.content = content
        self.register_calls: list[dict] = []
        self.deregister_calls: list[dict] = []
        self.closed = False

    async def get_config(self, data_id: str, group: str) -> str | None:
        self.data_id = data_id
        self.group = group
        return self.content

    async def register_service(self, **kwargs) -> bool:
        self.register_calls.append(kwargs)
        return True

    async def deregister_service(self, **kwargs) -> bool:
        self.deregister_calls.append(kwargs)
        return True

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def reset_nacos_runtime(monkeypatch):
    asyncio.run(nacos_module.cleanup_nacos())
    settings_module.clear_nacos_overrides()
    monkeypatch.setenv("NACOS_ENABLED", "false")
    reload_settings()
    yield
    asyncio.run(nacos_module.cleanup_nacos())
    settings_module.clear_nacos_overrides()
    reload_settings()


def test_nacos_disabled_uses_local_without_error():
    asyncio.run(nacos_module.init_nacos_config())

    assert get_settings().database.url.startswith("sqlite+aiosqlite")


def test_nacos_remote_business_config_has_highest_priority(monkeypatch):
    monkeypatch.setenv("NACOS_ENABLED", "true")
    monkeypatch.delenv("IR_DB_URL")
    monkeypatch.setenv("IR_FEISHU_ENABLED", "false")
    fake_client = FakeNacosClient(
        """
database:
  url: mysql+aiomysql://example_user:example_password@database.example.invalid:3306/ir_agent
feishu:
  enabled: true
  app_id: remote-app-id
policy_ask:
  feishu:
    app_id: remote-policy-app
  llm:
    api_key: remote-policy-key
"""
    )
    monkeypatch.setattr(nacos_module, "get_nacos_client", lambda: fake_client)
    monkeypatch.setattr(nacos_module, "get_local_ip", lambda: "internal-6-73.example.invalid")
    reload_settings()

    asyncio.run(nacos_module.init_nacos_config())

    settings = get_settings()
    assert fake_client.data_id == "ir-agent-test.yml"
    assert settings.database.url == "mysql+aiomysql://example_user:example_password@database.example.invalid:3306/ir_agent"
    assert settings.feishu.enabled is True
    assert settings.feishu.app_id == "remote-app-id"
    assert settings.policy_ask.feishu.app_id == "remote-policy-app"
    assert settings.policy_ask.llm.api_key == "remote-policy-key"
    assert settings.policy_ask.feishu.index_token
    assert settings.policy_ask.llm.model
    assert fake_client.register_calls == [
        {
            "service_name": "ir-agent",
            "host": "internal-6-73.example.invalid",
            "port": 9089,
            "metadata": {"version": "0.1.0", "context_path": "/"},
        }
    ]


def test_nacos_empty_config_falls_back_to_local_and_registers_service(monkeypatch):
    monkeypatch.setenv("NACOS_ENABLED", "true")
    monkeypatch.setenv("IR_DB_URL", "sqlite+aiosqlite:///fallback.db")
    fake_client = FakeNacosClient(None)
    monkeypatch.setattr(nacos_module, "get_nacos_client", lambda: fake_client)
    monkeypatch.setattr(nacos_module, "get_local_ip", lambda: "internal-6-74.example.invalid")
    reload_settings()

    asyncio.run(nacos_module.init_nacos_config())

    assert get_settings().database.url == "sqlite+aiosqlite:///fallback.db"
    assert fake_client.register_calls[0]["host"] == "internal-6-74.example.invalid"


def test_cleanup_deregisters_registered_instance_and_closes_client(monkeypatch):
    monkeypatch.setenv("NACOS_ENABLED", "true")
    fake_client = FakeNacosClient(None)
    monkeypatch.setattr(nacos_module, "get_nacos_client", lambda: fake_client)
    monkeypatch.setattr(nacos_module, "get_local_ip", lambda: "internal-6-75.example.invalid")
    reload_settings()

    asyncio.run(nacos_module.init_nacos_config())
    asyncio.run(nacos_module.cleanup_nacos())

    assert fake_client.deregister_calls == [
        {"service_name": "ir-agent", "host": "internal-6-75.example.invalid", "port": 9089}
    ]
    assert fake_client.closed is True
