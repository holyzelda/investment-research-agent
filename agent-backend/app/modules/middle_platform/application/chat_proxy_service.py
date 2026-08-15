"""中台对话代理：本应用会话与中台 session 的关联及 SSE 透传。

两套会话标识：
- 本应用 conversation_id（UUID）：会话与快照归属；中台回调 /ir/calc/tasks 时经 header 注入。
- 中台 session_id：中台自有会话标识，首轮为空，session_start 事件回写映射列后多轮回填。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config.settings import MiddlePlatformConfig
from app.core.exceptions import ValidationException
from app.infrastructure.database.session import get_sessionmaker
from app.modules.calculation.application.conversation_history_service import ConversationHistoryService
from app.modules.calculation.infrastructure.persistence.orm import ConversationORM
from app.modules.middle_platform.application.error_normalizer import (
    error_message,
    normalize_error_record,
)
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
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    ):
        self._config = config
        self._client = client or MiddlePlatformHttpClient(config)
        self._token_cache = token_cache or middle_platform_token_cache
        self._history = ConversationHistoryService()
        # 流式写入用独立短生命周期会话：请求依赖的 AsyncSession 可能已随请求 teardown。
        # 未注入时取全局 sessionmaker，测试可注入内存库的 sessionmaker。
        self._sessionmaker = sessionmaker or get_sessionmaker()

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
                last_activity_at=datetime.now(),
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

        await self._history.append_message(
            session,
            conversation_id=conversation.id,
            role="user",
            content=content,
        )

        token_key = (self._config.app_id, user.user_id)
        try:
            token = self._token_cache.get(token_key)
            if token is None:
                issued = await self._client.issue_token(
                    user_id=user.user_id,
                    user_name=user.username,
                )
                token = issued.value
                self._token_cache.put(token_key, token, issued.expires_in)
        except Exception:
            await self._history.append_calculation_error(
                session,
                conversation_id=conversation.id,
                error_message="对话服务连接失败，请稍后重试",
                error_code="middle_platform_connection_failed",
            )
            raise

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
        answer_parts: list[str] = []
        task_ids: list[int] = []
        calculation_failed = False
        try:
            async for chunk in self._client.stream_chat(access_token=token, payload=payload):
                buffer += chunk
                while True:
                    separator = b"\r\n\r\n" if b"\r\n\r\n" in buffer else b"\n\n"
                    if separator not in buffer:
                        break
                    record, buffer = buffer.split(separator, 1)
                    normalized = record.replace(b"\r\n", b"\n")
                    error = await self._capture_session_start(
                        session=session,
                        conversation=conversation,
                        record=normalized,
                    )
                    if error is not None:
                        await self._persist_error(
                            conversation_id=conversation.id,
                            error_message="中台会话协议异常",
                            error_code="middle_platform_protocol_error",
                        )
                        yield error
                        return
                    stream_error, frame_failed = self._collect_answer(
                        normalized, answer_parts, task_ids
                    )
                    calculation_failed = calculation_failed or frame_failed
                    if stream_error is not None:
                        await self._persist_error(
                            conversation_id=conversation.id,
                            error_message=stream_error,
                            error_code="middle_platform_error",
                        )
                    outbound = normalize_error_record(normalized)
                    yield outbound + separator
            if buffer:
                normalized = buffer.replace(b"\r\n", b"\n")
                error = await self._capture_session_start(
                    session=session,
                    conversation=conversation,
                    record=normalized,
                )
                if error is not None:
                    await self._persist_error(
                        conversation_id=conversation.id,
                        error_message="中台会话协议异常",
                        error_code="middle_platform_protocol_error",
                    )
                    yield error
                    return
                stream_error, frame_failed = self._collect_answer(
                    normalized, answer_parts, task_ids
                )
                calculation_failed = calculation_failed or frame_failed
                if stream_error is not None:
                    await self._persist_error(
                        conversation_id=conversation.id,
                        error_message=stream_error,
                        error_code="middle_platform_error",
                    )
                yield normalize_error_record(normalized)
        except Exception:
            await self._persist_error(
                conversation_id=conversation.id,
                error_message="对话服务连接中断，请重试",
                error_code="middle_platform_stream_interrupted",
            )
            raise
        if not calculation_failed:
            await self._persist_answer(
                conversation_id=conversation.id,
                answer_text="".join(answer_parts),
                task_ids=task_ids,
            )

    @staticmethod
    def _collect_answer(
        record: bytes, answer_parts: list[str], task_ids: list[int]
    ) -> tuple[str | None, bool]:
        try:
            lines = record.decode("utf-8").split("\n")
            event = next((line[7:].strip() for line in lines if line.startswith("event:")), None)
            raw_data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
            data = json.loads(raw_data)
            inner = data.get("data") if isinstance(data, dict) else None
            if event == "error":
                return error_message(data) or "对话出错", True
            if not isinstance(inner, dict):
                return None, False
            if event == "answer":
                text = inner.get("answer") or ""
                if text:
                    answer_parts.append(text)
                calculation_failed = False
                for item in inner.get("biz") or []:
                    if item.get("tool") == "create_calculation_task":
                        task_data = (item.get("payload") or {}).get("data", {})
                        task_id = task_data.get("taskId")
                        if isinstance(task_id, int):
                            task_ids.append(task_id)
                        calculation_failed = calculation_failed or task_data.get("status") == "failed"
                return None, calculation_failed
            elif event == "question":
                text = inner.get("question_text") or inner.get("text") or ""
                if text:
                    answer_parts.append(text)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
            return None, False
        return None, False

    async def _persist_answer(
        self, *, conversation_id: str, answer_text: str, task_ids: list[int]
    ) -> None:
        cleaned = answer_text.strip()
        if not cleaned:
            return
        try:
            maker = self._sessionmaker
            async with maker() as write_session:
                for task_id in dict.fromkeys(task_ids):
                    if await self._history.attach_answer_to_calculation(
                        write_session,
                        conversation_id=conversation_id,
                        task_id=task_id,
                        answer_text=cleaned,
                    ):
                        return
                await self._history.append_message(
                    write_session,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=cleaned,
                )
        except Exception:
            logger.exception("保存中台 AI 回复失败 conversation_id={}", conversation_id)

    async def _persist_error(
        self, *, conversation_id: str, error_message: str, error_code: str
    ) -> None:
        try:
            maker = self._sessionmaker
            async with maker() as write_session:
                await self._history.append_calculation_error(
                    write_session,
                    conversation_id=conversation_id,
                    error_message=error_message,
                    error_code=error_code,
                )
        except Exception:
            logger.exception("保存中台 AI 错误消息失败 conversation_id={}", conversation_id)

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
