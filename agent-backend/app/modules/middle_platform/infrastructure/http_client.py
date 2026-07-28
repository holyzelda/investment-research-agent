"""智能体中台 HTTP 调用。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from app.core.config.settings import MiddlePlatformConfig
from app.core.exceptions import ValidationException


@dataclass(frozen=True)
class PlatformAccessToken:
    value: str
    expires_in: int


class MiddlePlatformHttpClient:
    def __init__(self, config: MiddlePlatformConfig):
        self._config = config

    async def issue_token(self, *, user_id: str, user_name: str) -> PlatformAccessToken:
        if not self._config.app_secret:
            raise ValidationException("中台 app_secret 未配置")

        async with httpx.AsyncClient() as client:
            response = await client.post(self._config.auth_token_url, json={
                "app_id": self._config.app_id,
                "app_secret": self._config.app_secret,
                "user_id": user_id,
                "user_name": user_name,
            })
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or {}
        token = data.get("access_token")
        expires_in = data.get("expires_in")
        if body.get("code") != 200 or not token or not isinstance(expires_in, int) or expires_in <= 0:
            raise ValidationException("中台令牌获取失败")
        return PlatformAccessToken(value=token, expires_in=expires_in)

    async def chat_report_model(self, *, access_token: str, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=self._config.report_model_timeout_seconds) as client:
            response = await client.post(
                self._config.report_model_url,
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        text = body.get("data").get("content")
        if body.get("code") != 200 or not isinstance(text, str) or not text.strip():
            raise ValidationException(
                f"中台模型池响应无有效正文：code={body.get('code')} msg={body.get('msg')}"
            )
        return text.strip()

    async def stream_chat(self, *, access_token: str, payload: dict) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                self._config.chat_url,
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_raw():
                    yield chunk
