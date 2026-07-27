"""报告模型池适配器：只发送已构造的冻结章节上下文。"""
from __future__ import annotations

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

    async def generate_section(
        self, rule: dict, context: dict, *, user_id: str = "", username: str = ""
    ) -> str:
        token_key = (self._config.app_id, user_id)
        token = self._token_cache.get(token_key)
        if token is None:
            issued = await self._client.issue_token(user_id=user_id, user_name=username)
            token = issued.value
            self._token_cache.put(token_key, token, issued.expires_in)
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
