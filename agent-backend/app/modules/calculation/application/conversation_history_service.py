"""Current-user conversation list, replay, soft delete, and task ownership."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
    MessageSnapshotORM,
)


class ConversationHistoryService:
    async def list_active(self, session: AsyncSession, *, user_id: str) -> list[dict]:
        conversations = (await session.execute(
            select(ConversationORM).where(
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalars().all()

        rows = []
        for conversation in conversations:
            latest_message_at = await session.scalar(
                select(func.max(MessageSnapshotORM.created_at)).where(
                    MessageSnapshotORM.conversation_id == conversation.id
                )
            )
            # 仅失败、无任何成功消息的空会话不进入历史列表（回放会是空白）
            if latest_message_at is None:
                continue
            latest_task = (await session.execute(
                select(CalculationTaskORM)
                .where(CalculationTaskORM.conversation_id == conversation.id)
                .order_by(CalculationTaskORM.created_at.desc(), CalculationTaskORM.id.desc())
                .limit(1)
            )).scalar_one_or_none()
            latest_activity = max(
                value for value in (
                    conversation.created_at,
                    latest_task.created_at if latest_task else None,
                    latest_message_at,
                ) if value is not None
            )
            rows.append((latest_activity, conversation, latest_task))

        rows.sort(key=lambda row: (row[0], row[1].id), reverse=True)
        return [
            {
                "conversationId": conversation.id,
                "title": conversation.title,
                "createdAt": conversation.created_at.isoformat(),
                "latestVersion": latest_task.version if latest_task else None,
                "latestStatus": latest_task.status if latest_task else None,
            }
            for _, conversation, latest_task in rows
        ]

    async def get_detail(
        self, session: AsyncSession, *, conversation_id: int, user_id: str
    ) -> dict:
        conversation = await self.require_active_conversation(
            session, conversation_id=conversation_id, user_id=user_id
        )
        messages = (await session.execute(
            select(MessageSnapshotORM)
            .where(MessageSnapshotORM.conversation_id == conversation.id)
            .order_by(MessageSnapshotORM.created_at.asc(), MessageSnapshotORM.id.asc())
        )).scalars().all()
        tasks = (await session.execute(
            select(CalculationTaskORM)
            .where(CalculationTaskORM.conversation_id == conversation.id)
            .order_by(CalculationTaskORM.created_at.asc(), CalculationTaskORM.id.asc())
        )).scalars().all()
        calculation_result_by_task = {
            snapshot.task_id: snapshot.payload
            for snapshot in (await session.execute(
                select(CalculationResultSnapshotORM).where(
                    CalculationResultSnapshotORM.task_id.in_([task.id for task in tasks])
                )
            )).scalars().all()
        } if tasks else {}
        input_by_task = {
            snap.task_id: snap.payload.get("apiInput")
            for snap in (await session.execute(
                select(InputSnapshotORM).where(
                    InputSnapshotORM.task_id.in_([task.id for task in tasks])
                )
            )).scalars().all()
        } if tasks else {}
        return {
            "conversationId": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "messageType": message.message_type,
                    "payload": message.payload,
                    "createdAt": message.created_at.isoformat(),
                }
                for message in messages
            ],
            "versions": [
                {
                    "taskId": task.id,
                    "version": task.version,
                    "status": task.status,
                    "result": calculation_result_by_task.get(task.id),
                    "input": input_by_task.get(task.id),
                }
                for task in tasks
            ],
        }

    async def soft_delete(
        self, session: AsyncSession, *, conversation_id: int, user_id: str
    ) -> dict:
        conversation = await self.require_active_conversation(
            session, conversation_id=conversation_id, user_id=user_id
        )
        conversation.deleted_at = datetime.now()
        await session.commit()
        return {"conversationId": conversation.id, "deleted": True}

    async def require_active_conversation(
        self, session: AsyncSession, *, conversation_id: int, user_id: str
    ) -> ConversationORM:
        conversation = (await session.execute(
            select(ConversationORM).where(
                ConversationORM.id == conversation_id,
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if conversation is None:
            raise NotFoundException("会话不存在")
        return conversation

    async def require_owned_task(
        self, session: AsyncSession, *, task_id: int, user_id: str
    ) -> CalculationTaskORM:
        task = (await session.execute(
            select(CalculationTaskORM)
            .join(
                ConversationORM,
                ConversationORM.id == CalculationTaskORM.conversation_id,
            )
            .where(
                CalculationTaskORM.id == task_id,
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if task is None:
            raise NotFoundException("任务不存在")
        return task
