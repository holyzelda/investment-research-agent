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
BOUND_TTL = timedelta(days=7)


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
            await session.execute(delete(ConversationSpotContextORM).where(
                ConversationSpotContextORM.conversation_id == conversation_id
            ))
        else:
            await session.execute(delete(ConversationSpotContextORM).where(
                ConversationSpotContextORM.user_id == user_id,
                ConversationSpotContextORM.conversation_id.is_(None),
            ))

        token = secrets.token_urlsafe(32)
        context = ConversationSpotContextORM(
            conversation_id=conversation_id,
            user_id=user_id,
            status="ready",
            context_token_hash=_hash_token(token),
            file_name=parsed.file_name,
            file_sha256=parsed.file_sha256,
            price_unit="CNY/MWh",
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            valid_day_count=parsed.valid_day_count,
            skipped_day_count=parsed.skipped_day_count,
            warnings=parsed.warnings,
            k_results=parsed.k_results,
            algorithm_version=ALGORITHM_VERSION,
            expires_at=datetime.now() + (BOUND_TTL if conversation_id else STAGED_TTL),
        )
        session.add(context)
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
        if context is None or context.expires_at <= datetime.now():
            raise ValidationException("自定义电价文件已失效，请重新上传")
        if context.conversation_id not in (None, conversation_id):
            raise ValidationException("自定义电价文件不属于当前会话")
        if context.conversation_id == conversation_id:
            return context
        await session.execute(delete(ConversationSpotContextORM).where(
            ConversationSpotContextORM.conversation_id == conversation_id
        ))
        context.conversation_id = conversation_id
        context.expires_at = datetime.now() + BOUND_TTL
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
        if context.status != "ready" or context.expires_at <= datetime.now():
            if context.status == "ready":
                context.status = "expired"
                context.k_results = {}
                await session.commit()
            raise ValidationException("本会话的自定义电价文件已失效，请重新上传")
        context.last_used_at = datetime.now()
        context.expires_at = datetime.now() + BOUND_TTL
        await session.commit()
        return context

    async def cleanup_expired(self, session: AsyncSession) -> None:
        now = datetime.now()
        await session.execute(delete(ConversationSpotContextORM).where(
            ConversationSpotContextORM.conversation_id.is_(None),
            ConversationSpotContextORM.expires_at <= now,
        ))
        expired = (await session.execute(select(ConversationSpotContextORM).where(
            ConversationSpotContextORM.conversation_id.is_not(None),
            ConversationSpotContextORM.status == "ready",
            ConversationSpotContextORM.expires_at <= now,
        ))).scalars().all()
        for context in expired:
            context.status = "expired"
            context.k_results = {}
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
        await session.execute(delete(ConversationSpotContextORM).where(
            ConversationSpotContextORM.conversation_id == conversation_id
        ))
        await session.commit()

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
            "validDays": context.valid_day_count,
            "skippedDays": context.skipped_day_count,
            "startDate": context.start_date.isoformat(),
            "endDate": context.end_date.isoformat(),
            "kCount": len(context.k_results or {}),
            "warnings": list(context.warnings or []),
            "expiresAt": context.expires_at.isoformat(),
        }
