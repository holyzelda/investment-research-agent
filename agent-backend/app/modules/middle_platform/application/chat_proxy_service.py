"""中台对话代理：本应用会话与中台 session 的关联及 SSE 透传。

两套会话标识：
- 本应用 conversation_id（UUID）：会话与快照归属；中台回调 /ir/calc/tasks 时经 header 注入。
- 中台 session_id：中台自有会话标识，首轮为空，session_start 事件回写映射列后多轮回填。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import MiddlePlatformConfig
from app.core.exceptions import ValidationException
from app.modules.calculation.application.conversation_history_service import ConversationHistoryService
from app.modules.calculation.infrastructure.persistence.orm import ConversationORM
from app.modules.middle_platform.application.token_cache import (
    MiddlePlatformTokenCache,
    middle_platform_token_cache,
)
from app.modules.middle_platform.infrastructure.http_client import MiddlePlatformHttpClient
from app.modules.platform_access.domain.models import CurrentUser


@dataclass(frozen=True)
class ChatStream:
    conversation_id: str
    chunks: AsyncIterator[bytes]


class ChatProxyService:
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
        self._history = ConversationHistoryService()

    async def start_chat(
        self,
        *,
        session: AsyncSession,
        user: CurrentUser,
        message: str,
        conversation_id: str | None,
    ) -> ChatStream:
        content = message.strip()
        if not content:
            raise ValidationException("消息不能为空")

        if conversation_id is None:
            conversation = ConversationORM(
                user_id=user.user_id,
                username=user.username,
                title=content[:30],
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
        else:
            conversation = await self._history.require_active_conversation(
                session,
                conversation_id=conversation_id,
                user_id=user.user_id,
            )

        token_key = (self._config.app_id, user.user_id)
        token = self._token_cache.get(token_key)
        if token is None:
            issued = await self._client.issue_token(
                user_id=user.user_id,
                user_name=user.username,
            )
            token = issued.value
            self._token_cache.put(token_key, token, issued.expires_in)

        payload = {
            "session_id": conversation.middle_platform_session_id,
            "injected_domain": None,
            "entry_type": "open_chat",
            "pinned_domain": None,
            "page_context": None,
            "source_system": self._config.app_id,
            "end_user_id": user.user_id,
            "end_user_name": user.username,
            "app_id": self._config.app_id,
            "message": content,
            "locale": "zh-CN",
            "header": {
                "username": quote(user.username, safe=""),
                "userid": user.user_id,
                "X-IR-Conversation-Id": conversation.id,
            },
        }
        return ChatStream(
            conversation_id=conversation.id,
            chunks=self._relay(
                session=session,
                conversation=conversation,
                token=token,
                payload=payload,
            ),
        )

    async def _relay(
        self,
        *,
        session: AsyncSession,
        conversation: ConversationORM,
        token: str,
        payload: dict,
    ) -> AsyncIterator[bytes]:
        buffer = b""
        async for chunk in self._client.stream_chat(access_token=token, payload=payload):
            buffer += chunk
            while True:
                separator = b"\r\n\r\n" if b"\r\n\r\n" in buffer else b"\n\n"
                if separator not in buffer:
                    break
                record, buffer = buffer.split(separator, 1)
                error = await self._capture_session_start(
                    session=session,
                    conversation=conversation,
                    record=record.replace(b"\r\n", b"\n"),
                )
                if error is not None:
                    yield error
                    return
                yield record + separator
        if buffer:
            error = await self._capture_session_start(
                session=session,
                conversation=conversation,
                record=buffer.replace(b"\r\n", b"\n"),
            )
            if error is not None:
                yield error
                return
            yield buffer

    async def _capture_session_start(
        self,
        *,
        session: AsyncSession,
        conversation: ConversationORM,
        record: bytes,
    ) -> bytes | None:
        """在 session_start 事件抓取中台 session_id 并写回映射列（不与本应用 UUID 比对）。"""
        try:
            lines = record.decode("utf-8").split("\n")
        except UnicodeDecodeError:
            return None
        event = next((line[7:].strip() for line in lines if line.startswith("event:")), None)
        if event != "session_start":
            return None
        raw_data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
        try:
            session_id = json.loads(raw_data)["session"]["session_id"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return self._error_frame("中台会话协议异常")
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 255:
            return self._error_frame("中台会话协议异常")
        if conversation.middle_platform_session_id != session_id:
            conversation.middle_platform_session_id = session_id
            session.add(conversation)
            await session.commit()
        return None

    @staticmethod
    def _error_frame(message: str) -> bytes:
        body = json.dumps({"code": 500, "msg": message, "data": None}, ensure_ascii=False)
        return f"event: error\ndata: {body}\n\n".encode("utf-8")
