"""会话级自定义现货电价上下文服务。"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.calculation.infrastructure.persistence.orm import (
    ConversationSpotContextORM,
    ConversationORM,
)
from app.modules.calculation.infrastructure.uploaded_spot_context import ALGORITHM_VERSION

STAGED_TTL = timedelta(minutes=30)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SpotContextService:
    async def save_prepared(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        conversation_id: str | None,
        parsed,
    ) -> tuple[str, ConversationSpotContextORM]:
        if conversation_id is not None:
            conversation = (await session.execute(
                select(ConversationORM).where(
                    ConversationORM.id == conversation_id,
                    ConversationORM.user_id == user_id,
                    ConversationORM.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if conversation is None:
                raise NotFoundException("会话不存在")
            existing = (await session.execute(
                select(ConversationSpotContextORM.id).where(
                    ConversationSpotContextORM.conversation_id == conversation_id
                )
            )).scalar_one_or_none()
            if existing is not None:
                raise ValidationException("本会话已上传电价文件，不允许删除或重新上传")

        token = secrets.token_urlsafe(32)
        context = None
        if conversation_id is None:
            staged_contexts = (await session.execute(
                select(ConversationSpotContextORM).where(
                    ConversationSpotContextORM.user_id == user_id,
                    ConversationSpotContextORM.conversation_id.is_(None),
                ).order_by(ConversationSpotContextORM.created_at.desc())
            )).scalars().all()
            if staged_contexts:
                # A staged upload belongs only to the current in-memory page.
                # Replacing it invalidates the previous token without letting
                # an abandoned upload block the next one.
                context = staged_contexts[0]
                for stale_context in staged_contexts[1:]:
                    await session.delete(stale_context)

        if context is None:
            context = ConversationSpotContextORM(
                conversation_id=conversation_id,
                user_id=user_id,
            )
            session.add(context)

        context.conversation_id = conversation_id
        context.user_id = user_id
        context.status = "ready"
        context.context_token_hash = _hash_token(token)
        context.file_name = parsed.file_name
        context.file_sha256 = parsed.file_sha256
        context.price_unit = "CNY/MWh"
        context.price_mode = getattr(parsed, "price_mode", None) or "both"
        context.start_date = parsed.start_date
        context.end_date = parsed.end_date
        context.valid_day_count = parsed.valid_day_count
        context.skipped_day_count = parsed.skipped_day_count
        context.warnings = parsed.warnings
        context.k_results = parsed.k_results
        context.raw_prices = getattr(parsed, "raw_prices", None)
        context.algorithm_version = ALGORITHM_VERSION
        context.expires_at = None if conversation_id else datetime.now() + STAGED_TTL
        await session.commit()
        await session.refresh(context)
        return token, context

    async def bind_token(
        self,
        session: AsyncSession,
        *,
        token: str,
        user_id: str,
        conversation_id: str,
    ) -> ConversationSpotContextORM:
        context = (await session.execute(
            select(ConversationSpotContextORM).where(
                ConversationSpotContextORM.context_token_hash == _hash_token(token),
                ConversationSpotContextORM.user_id == user_id,
                ConversationSpotContextORM.status == "ready",
            )
        )).scalar_one_or_none()
        if context is None or (
            context.conversation_id is None
            and context.expires_at is not None
            and context.expires_at <= datetime.now()
        ):
            raise ValidationException("自定义电价文件已失效，请重新上传")
        if context.conversation_id not in (None, conversation_id):
            raise ValidationException("自定义电价文件不属于当前会话")
        if context.conversation_id == conversation_id:
            return context
        existing = (await session.execute(
            select(ConversationSpotContextORM.id).where(
                ConversationSpotContextORM.conversation_id == conversation_id
            )
        )).scalar_one_or_none()
        if existing is not None:
            raise ValidationException("本会话已上传电价文件，不允许删除或重新上传")
        context.conversation_id = conversation_id
        context.expires_at = None
        await session.commit()
        return context

    async def get_for_conversation(
        self, session: AsyncSession, *, conversation_id: str, user_id: str
    ) -> Optional[ConversationSpotContextORM]:
        context = (await session.execute(
            select(ConversationSpotContextORM).where(
                ConversationSpotContextORM.conversation_id == conversation_id,
                ConversationSpotContextORM.user_id == user_id,
            )
        )).scalar_one_or_none()
        if context is None:
            return None
        if context.status != "ready":
            raise ValidationException("本会话的自定义电价文件不可用")
        context.last_used_at = datetime.now()
        await session.commit()
        return context

    async def cleanup_expired(self, session: AsyncSession) -> None:
        now = datetime.now()
        await session.execute(delete(ConversationSpotContextORM).where(
            ConversationSpotContextORM.conversation_id.is_(None),
            ConversationSpotContextORM.expires_at.is_not(None),
            ConversationSpotContextORM.expires_at <= now,
        ))
        await session.commit()

    async def remove(
        self, session: AsyncSession, *, conversation_id: str, user_id: str
    ) -> None:
        conversation = (await session.execute(
            select(ConversationORM).where(
                ConversationORM.id == conversation_id,
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if conversation is None:
            raise NotFoundException("会话不存在")
        raise ValidationException("本会话的电价文件已锁定，不允许删除")

    async def remove_staged(
        self, session: AsyncSession, *, token: str, user_id: str
    ) -> None:
        await session.execute(delete(ConversationSpotContextORM).where(
            ConversationSpotContextORM.context_token_hash == _hash_token(token),
            ConversationSpotContextORM.user_id == user_id,
            ConversationSpotContextORM.conversation_id.is_(None),
        ))
        await session.commit()

    @staticmethod
    def summary(context: ConversationSpotContextORM) -> dict:
        return {
            "contextToken": None,
            "status": context.status,
            "fileName": context.file_name,
            "fileSha256": context.file_sha256,
            "priceUnit": context.price_unit,
            "priceMode": getattr(context, "price_mode", None) or "both",
            "validDays": context.valid_day_count,
            "skippedDays": context.skipped_day_count,
            "startDate": context.start_date.isoformat(),
            "endDate": context.end_date.isoformat(),
            "kCount": len(context.k_results or {}),
            "warnings": list(context.warnings or []),
            "expiresAt": context.expires_at.isoformat() if context.expires_at else None,
        }
