"""用户管理中心 HTTP 客户端：按 userId 读组织成员与角色。

只发一次 GET，不带凭据、不缓存。任何异常都返回 None，由调用方降级为"只看自己"——
上游抖动绝不能让用户看不到自己的台账，也绝不能扩大可见范围。
"""
from __future__ import annotations

from typing import Optional

import httpx
from loguru import logger

from app.core.config.settings import UserCenterConfig


class UserCenterClient:
    def __init__(self, config: UserCenterConfig, client: httpx.AsyncClient | None = None):
        self._config = config
        self._client = client  # 注入客户端仅用于测试；生产每次请求自建短连接。

    async def fetch_organization_users(self, user_id: str) -> Optional[list[dict]]:
        """返回上游 data 数组；未接入或调用/响应异常返回 None。"""
        base_url = (self._config.base_url or "").rstrip("/")
        if not base_url and self._client is None:
            return None
        url = f"{base_url}{self._config.users_path}"
        try:
            if self._client is not None:
                response = await self._client.get(url, params={"userId": user_id})
            else:
                async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                    response = await client.get(url, params={"userId": user_id})
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001 —— 任何失败都统一降级，不区分错因
            logger.warning("用户管理中心调用失败，按普通用户处理 user_id={} error={}", user_id, exc)
            return None
        if not isinstance(body, dict) or body.get("code") != 200:
            logger.warning(
                "用户管理中心响应异常，按普通用户处理 user_id={} body={}", user_id, body)
            return None
        data = body.get("data")
        if not isinstance(data, list):
            logger.warning("用户管理中心 data 不是数组，按普通用户处理 user_id={}", user_id)
            return None
        return data
