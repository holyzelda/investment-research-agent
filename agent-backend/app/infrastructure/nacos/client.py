"""Nacos 配置装载（团队统一栈；未启用/不可用时优雅降级到本地配置）。

启动时调用 init_nacos_config()：
- NACOS_ENABLED=false → 直接使用本地 application.yml/.env（不连接 Nacos）。
- 启用 → 拉取 data_id={app.name}-{profile}.yml，并入配置缓存；失败则回退本地并记录告警。

说明：本实现为本项目自研，仅框架选型（nacos-sdk-python）与团队一致，不复制 trader 代码。
"""
from typing import Any

from loguru import logger

from app.core.config.settings import get_settings

# Nacos 原始配置缓存（供各模块按需读取）
_nacos_cache: dict[str, Any] = {}


def get_nacos_cache() -> dict[str, Any]:
    return _nacos_cache


def set_nacos_cache(cfg: dict[str, Any]) -> None:
    global _nacos_cache
    _nacos_cache = cfg or {}


def is_nacos_enabled() -> bool:
    return get_settings().nacos.enabled


def _datasource_data_id() -> str:
    s = get_settings()
    return f"{s.app.name}-{s.nacos.profile}.yml"


async def init_nacos_config() -> None:
    """初始化 Nacos 配置；未启用时使用本地配置（不抛错）。"""
    if not is_nacos_enabled():
        logger.info("Nacos 未启用，使用本地配置（application.yml / 环境变量）")
        init_database_config_from_env()
        return

    try:
        import yaml
        from v2.nacos import ClientConfig, NacosConfigService, ConfigParam  # type: ignore

        s = get_settings()
        client_config = ClientConfig(server_addresses=s.nacos.server_addr, namespace_id=s.nacos.namespace)
        config_service = await NacosConfigService.create_config_service(client_config)
        data_id = _datasource_data_id()
        content = await config_service.get_config(ConfigParam(data_id=data_id, group=s.nacos.group))
        if content:
            parsed = yaml.safe_load(content) or {}
            set_nacos_cache(parsed)
            logger.info(f"从 Nacos 加载配置成功：data_id={data_id}")
        else:
            logger.warning(f"Nacos 未返回配置：data_id={data_id}，回退本地配置")
            init_database_config_from_env()
    except ImportError:
        logger.warning("nacos-sdk-python 未安装，回退本地配置")
        init_database_config_from_env()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Nacos 配置装载失败：{e}，回退本地配置")
        init_database_config_from_env()


def init_database_config_from_env() -> None:
    """本地/降级：确保数据源配置就绪（当前由 settings 直接从 env/yaml 读取，无需额外动作）。"""
    s = get_settings()
    logger.info(f"使用本地数据源配置：{s.database.url.split('@')[-1]}")


async def cleanup_nacos() -> None:
    """占位：如注册了 Nacos 服务发现，在此注销。当前未启用服务注册。"""
    return None
