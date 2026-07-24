"""中台对话代理：本应用会话与中台 session 的关联及 SSE 透传。"""
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
    conversation_id: int
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
        conversation_id: int | None,
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
            "app_id": self._config.app_id,
            "message": (
                f'{content}\n<ir_system_context>{{"conversation_id":{conversation.id}}}'
                "</ir_system_context>"
            ),
            "session_id": conversation.middle_platform_session_id,
            "end_user_id": user.user_id,
            "end_user_name": user.username,
            "locale": "zh-CN",
            "entry_type": "open_chat",
            "pinned_domain": None,
            "page_context": None,
            "header": {
                "userId": user.user_id,
                "username": quote(user.username, safe=""),
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
            while b"\n\n" in buffer:
                record, buffer = buffer.split(b"\n\n", 1)
                record = record.replace(b"\r\n", b"\n")
                error = await self._persist_session_start(
                    session=session,
                    conversation=conversation,
                    record=record,
                )
                if error is not None:
                    yield error
                    return
                yield record + b"\n\n"
        if buffer:
            error = await self._persist_session_start(
                session=session,
                conversation=conversation,
                record=buffer.replace(b"\r\n", b"\n"),
            )
            if error is not None:
                yield error
                return
            yield buffer

    async def _persist_session_start(
        self,
        *,
        session: AsyncSession,
        conversation: ConversationORM,
        record: bytes,
    ) -> bytes | None:
        lines = record.decode("utf-8").split("\n")
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
        if (
            conversation.middle_platform_session_id is not None
            and conversation.middle_platform_session_id != session_id
        ):
            return self._error_frame("中台会话映射冲突")
        if conversation.middle_platform_session_id is None:
            conversation.middle_platform_session_id = session_id
            try:
                await session.commit()
            except Exception:  # noqa: BLE001
                await session.rollback()
                return self._error_frame("中台会话映射保存失败")
        return None

    @staticmethod
    def _error_frame(message: str) -> bytes:
        body = json.dumps({"code": 500, "msg": message, "data": None}, ensure_ascii=False)
        return f"event: error\ndata: {body}\n\n".encode("utf-8")
