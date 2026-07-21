"""Nacos 业务配置装载与服务发现。

启动顺序固定为：拉取远端业务配置并合并到 Settings，随后注册当前服务。
Nacos 未启用、不可达或未返回有效 YAML 时，保留本地 application.yml 和既有环境变量配置。
"""
from __future__ import annotations

import inspect
import socket
from typing import Any

import yaml
from loguru import logger

from app.core.config.settings import (
    clear_nacos_overrides,
    get_settings,
    reload_settings,
    set_nacos_overrides,
)

_nacos_cache: dict[str, Any] = {}
_nacos_client: NacosClient | Any | None = None
_registered_instance: dict[str, Any] | None = None


def get_nacos_cache() -> dict[str, Any]:
    return _nacos_cache


def set_nacos_cache(config: dict[str, Any]) -> None:
    global _nacos_cache
    _nacos_cache = config or {}


def is_nacos_enabled() -> bool:
    return get_settings().nacos.enabled


def _datasource_data_id() -> str:
    settings = get_settings()
    return f"{settings.app.name}-{settings.nacos.profile}.yml"


def get_local_ip() -> str:
    """获取 Nacos 可连接的本机地址；无法判断时使用 loopback。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class NacosClient:
    """只封装本服务需要的 v2 SDK 配置与命名操作。"""

    def __init__(self, config_service: Any, naming_service: Any, group: str):
        self._config_service = config_service
        self._naming_service = naming_service
        self._group = group
        from v2.nacos import ConfigParam, DeregisterInstanceParam, RegisterInstanceParam  # type: ignore

        self._config_param = ConfigParam
        self._register_param = RegisterInstanceParam
        self._deregister_param = DeregisterInstanceParam

    @classmethod
    async def create(cls) -> NacosClient:
        from v2.nacos import ClientConfig, NacosConfigService, NacosNamingService  # type: ignore

        nacos = get_settings().nacos
        client_config = ClientConfig(
            server_addresses=nacos.server_addr,
            namespace_id=nacos.namespace,
        )
        config_service = await NacosConfigService.create_config_service(client_config)
        naming_service = await NacosNamingService.create_naming_service(client_config)
        logger.info(f"Nacos 客户端已连接：{nacos.server_addr}")
        return cls(config_service, naming_service, nacos.group)

    async def get_config(self, data_id: str, group: str) -> str | None:
        return await self._config_service.get_config(self._config_param(data_id=data_id, group=group))

    async def register_service(
        self, service_name: str, host: str, port: int, metadata: dict[str, str]
    ) -> bool:
        result = await self._naming_service.register_instance(
            self._register_param(
                ip=host,
                port=port,
                service_name=service_name,
                group_name=self._group,
                metadata=metadata,
            )
        )
        return bool(result)

    async def deregister_service(self, service_name: str, host: str, port: int) -> bool:
        result = await self._naming_service.deregister_instance(
            self._deregister_param(
                ip=host,
                port=port,
                service_name=service_name,
                group_name=self._group,
            )
        )
        return bool(result)

    async def close(self) -> None:
        await _call_optional(self._config_service, "shutdown")
        proxy = getattr(self._naming_service, "grpc_client_proxy", None)
        await _call_optional(proxy, "close_client")
        updater = getattr(self._naming_service, "service_info_updater", None)
        await _call_optional(updater, "stop")


async def _call_optional(target: Any, name: str) -> None:
    method = getattr(target, name, None)
    if method is None:
        return
    result = method()
    if inspect.isawaitable(result):
        await result


async def get_nacos_client() -> NacosClient:
    global _nacos_client
    if _nacos_client is None:
        _nacos_client = await NacosClient.create()
    return _nacos_client


async def _resolve_nacos_client() -> NacosClient | Any:
    client = get_nacos_client()
    if inspect.isawaitable(client):
        return await client
    return client


def _load_local_config() -> None:
    set_nacos_cache({})
    clear_nacos_overrides()
    settings = reload_settings()
    logger.info(f"使用本地数据源配置：{settings.database.url.split('@')[-1]}")


async def _register_service(client: NacosClient | Any) -> None:
    global _registered_instance
    settings = get_settings()
    instance = {
        "service_name": settings.nacos.service_name,
        "host": get_local_ip(),
        "port": settings.app.port,
    }
    result = await client.register_service(
        **instance,
        metadata={"version": settings.app.version, "context_path": "/"},
    )
    if result:
        _registered_instance = instance
        logger.info(
            f"Nacos 服务注册成功：{instance['service_name']} at "
            f"{instance['host']}:{instance['port']}"
        )
    else:
        logger.error(f"Nacos 服务注册失败：{instance['service_name']}")


async def init_nacos_config() -> None:
    """装载 Nacos 业务配置，随后注册服务；任何配置失败均降级到本地。"""
    global _nacos_client
    if not is_nacos_enabled():
        logger.info("Nacos 未启用，使用本地配置（application.yml / 环境变量）")
        _load_local_config()
        return

    try:
        client = await _resolve_nacos_client()
        _nacos_client = client
        data_id = _datasource_data_id()
        content = await client.get_config(data_id, get_settings().nacos.group)
    except ImportError:
        logger.warning("nacos-sdk-python 未安装，回退本地配置")
        _load_local_config()
        return
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Nacos 配置装载失败：{exc}，回退本地配置")
        _load_local_config()
        return

    if content:
        try:
            parsed = yaml.safe_load(content)
            if not isinstance(parsed, dict):
                raise ValueError("Nacos 配置根节点必须是对象")
        except (yaml.YAMLError, ValueError) as exc:
            logger.warning(f"Nacos 配置格式无效：{exc}，回退本地配置")
            _load_local_config()
        else:
            set_nacos_cache(parsed)
            set_nacos_overrides(parsed)
            reload_settings()
            logger.info(f"从 Nacos 加载配置成功：data_id={data_id}")
    else:
        logger.warning(f"Nacos 未返回配置：data_id={data_id}，回退本地配置")
        _load_local_config()

    try:
        await _register_service(client)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Nacos 服务注册失败：{exc}")


async def cleanup_nacos() -> None:
    """注销本进程已注册的实例并关闭 Nacos 客户端。"""
    global _nacos_client, _registered_instance
    client = _nacos_client
    instance = _registered_instance
    _registered_instance = None
    _nacos_client = None
    if client is None:
        return

    try:
        if instance is not None:
            result = await client.deregister_service(**instance)
            if result:
                logger.info("Nacos 服务注销成功")
            else:
                logger.error("Nacos 服务注销失败")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Nacos 服务注销失败：{exc}")
    finally:
        try:
            await client.close()
            logger.info("Nacos 客户端已关闭")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"关闭 Nacos 客户端失败：{exc}")
