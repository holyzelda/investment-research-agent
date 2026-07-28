"""报告模型池适配器：只发送已构造的冻结章节上下文。"""
from __future__ import annotations

import asyncio

from app.core.config.settings import MiddlePlatformConfig
from app.modules.middle_platform.application.token_cache import MiddlePlatformTokenCache, middle_platform_token_cache
from app.modules.middle_platform.infrastructure.http_client import MiddlePlatformHttpClient
from app.modules.report.application.frozen_section_context import render_section_message
from app.modules.report.domain.ports import ReportAiPort


class ModelPoolReportAiClient(ReportAiPort):
    def __init__(
        self,
        config: MiddlePlatformConfig,
        *,
        client: MiddlePlatformHttpClient | None = None,
        token_cache: MiddlePlatformTokenCache | None = None,
    ):
        self._config = config
        self._client = client or MiddlePlatformHttpClient(config)
        self._token_cache = token_cache or middle_platform_token_cache
        self._token_tasks: dict[tuple[str, str], asyncio.Task[str]] = {}

    async def _issue_and_cache_token(
        self, token_key: tuple[str, str], *, user_id: str, username: str
    ) -> str:
        issued = await self._client.issue_token(user_id=user_id, user_name=username)
        self._token_cache.put(token_key, issued.value, issued.expires_in)
        return issued.value

    async def _get_access_token(self, *, user_id: str, username: str) -> str:
        token_key = (self._config.app_id, user_id)
        token = self._token_cache.get(token_key)
        if token is not None:
            return token

        task = self._token_tasks.get(token_key)
        if task is None:
            task = asyncio.create_task(self._issue_and_cache_token(
                token_key, user_id=user_id, username=username
            ))
            self._token_tasks[token_key] = task

        try:
            return await asyncio.shield(task)
        finally:
            if task.done() and self._token_tasks.get(token_key) is task:
                self._token_tasks.pop(token_key, None)

    async def generate_section(
        self, rule: dict, context: dict, *, user_id: str = "", username: str = ""
    ) -> str:
        token = await self._get_access_token(user_id=user_id, username=username)
        return await self._client.chat_report_model(
            access_token=token,
            payload={
                "source_app_id": self._config.app_id,
                "end_user_id": user_id,
                "user_name": username,
                "message": render_section_message(rule, context),
                "model_name": self._config.report_model_name,
            },
        )
