"""集成测试（Batch 0.3）：Nacos 未启用时优雅降级到本地配置（不抛错）。"""
import asyncio

from app.core.config.settings import get_settings
from app.infrastructure.nacos.client import init_nacos_config, is_nacos_enabled


def test_nacos_disabled_uses_local_without_error():
    assert is_nacos_enabled() is False
    # 不应抛出异常
    asyncio.run(init_nacos_config())
    # 本地数据源可用
    assert get_settings().database.url.startswith("sqlite+aiosqlite")
