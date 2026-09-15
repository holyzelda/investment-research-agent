"""Current-user conversation list, replay, soft delete, and task ownership."""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.calculation.application.calculation_share_service import (
    CalculationShareService,
)
from app.modules.calculation.application.error_presenter import (
    public_calc_error_code,
    public_calc_error_message,
)
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationSpotContextORM,
    ConversationORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)


class ConversationHistoryService:
    async def list_active(
        self, session: AsyncSession, *, user_id: str,
        cursor: str | None = None,
        limit: int = 15,
    ) -> tuple[list[dict], str | None]:
        """按最近活动时间游标分页列出活跃会话。

        Returns:
            (items, next_cursor)
            - items: 当前页会话列表，每项含 conversationId / title / createdAt / lastActivityAt
            - next_cursor: 下一页游标字符串（base64 编码），为 None 表示已无更多
        """
        from base64 import b64decode, b64encode

        cursor_activity = None
        cursor_id = None
        if cursor:
            raw = b64decode(cursor).decode("utf-8")
            parts = raw.split("|")
            cursor_activity = datetime.fromisoformat(parts[0])
            cursor_id = parts[1]

        query = (
            select(ConversationORM)
            .where(
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )
        if cursor_activity and cursor_id:
            query = query.where(
                (ConversationORM.last_activity_at < cursor_activity)
                | (
                    (ConversationORM.last_activity_at == cursor_activity)
                    & (ConversationORM.id < cursor_id)
                )
            )

        # last_activity_at 可能为 NULL（存量旧数据），用 created_at 降序兜底
        # MySQL 中 DESC 排序默认 NULL 在最后，无需 nulls_last()
        query = query.order_by(
            ConversationORM.last_activity_at.desc(),
            ConversationORM.id.desc(),
        ).limit(limit + 1)  # 多取1条判断是否还有更多

        conversations = (await session.execute(query)).scalars().all()

        has_more = len(conversations) > limit
        if has_more:
            conversations = conversations[:limit]

        items = [
            {
                "conversationId": c.id,
                "title": c.title,
                "createdAt": c.created_at.isoformat(),
                "lastActivityAt": (
                    c.last_activity_at or c.created_at
                ).isoformat(),
            }
            for c in conversations
        ]

        next_cursor = None
        if has_more and conversations:
            last = conversations[-1]
            if last.last_activity_at is not None and last.id is not None:
                raw = f"{last.last_activity_at.isoformat()}|{last.id}"
                next_cursor = b64encode(raw.encode("utf-8")).decode("utf-8")

        return items, next_cursor

    async def get_detail(
        self, session: AsyncSession, *, conversation_id: str, user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> dict:
        conversation = await self.require_active_conversation(
            session, conversation_id=conversation_id, user_id=user_id,
            readable_user_ids=readable_user_ids,
        )
        messages = (await session.execute(
            select(MessageSnapshotORM)
            .where(MessageSnapshotORM.conversation_id == conversation.id)
            .order_by(MessageSnapshotORM.created_at.asc(), MessageSnapshotORM.id.asc())
        )).scalars().all()
        tasks = (await session.execute(
            select(CalculationTaskORM)
            .where(
                CalculationTaskORM.conversation_id == conversation.id,
                CalculationTaskORM.status == "completed",
            )
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
            snap.task_id: snap.payload.get("changeMeta") or {}
            for snap in (await session.execute(
                select(InputSnapshotORM).where(
                    InputSnapshotORM.task_id.in_([task.id for task in tasks])
                )
            )).scalars().all()
        } if tasks else {}
        reports = (await session.execute(
            select(ReportSnapshotORM).where(ReportSnapshotORM.conversation_id == conversation.id)
            .order_by(ReportSnapshotORM.created_at.desc(), ReportSnapshotORM.id.desc())
        )).scalars().all()
        generations = {
            generation.task_id: generation
            for generation in (await session.execute(
                select(ReportGenerationTaskORM).where(
                    ReportGenerationTaskORM.conversation_id == conversation.id
                )
            )).scalars().all()
        }
        report_by_task = {report.task_id: report for report in reports}
        detail = {
            "conversationId": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": message.role,
                    "content": (
                        f"测算失败：{public_calc_error_message(
                            message.content,
                            (message.payload or {}).get("error_code"),
                        )}"
                        if message.message_type == "calculation_error"
                        else message.content
                    ),
                    "messageType": message.message_type,
                    "payload": (
                        {
                            **(message.payload or {}),
                            "error_code": public_calc_error_code(
                                (message.payload or {}).get("error_code"),
                                message.content,
                            ),
                        }
                        if message.message_type == "calculation_error"
                        else message.payload
                    ),
                    "createdAt": message.created_at.isoformat(),
                }
                for message in messages
            ],
            "versions": [
                {
                    "taskId": task.id,
                    "version": task.version,
                    "status": task.status,
                    "card": self._result_card(calculation_result_by_task.get(task.id), task.version, task.created_at),
                    "changeMeta": input_by_task.get(task.id, {}),
                    "calculatedAt": task.created_at.isoformat(),
                    **({"report": summary} if (summary := self._report_summary(
                        report_by_task.get(task.id), generations.get(task.id), task.version
                    )) else {}),
                }
                for task in tasks
            ],
        }
        spot_context = (await session.execute(
            select(ConversationSpotContextORM).where(
                ConversationSpotContextORM.conversation_id == conversation.id,
            )
        )).scalar_one_or_none()
        if spot_context is not None:
            effective_status = (
                "expired"
                if spot_context.status != "ready"
                or (
                    spot_context.expires_at is not None
                    and spot_context.expires_at <= datetime.now()
                )
                else "ready"
            )
            detail["spotContext"] = {
                "status": effective_status,
                "fileName": spot_context.file_name,
                "fileSha256": spot_context.file_sha256,
                "priceUnit": spot_context.price_unit,
                "priceMode": getattr(spot_context, "price_mode", None) or "both",
                "validDays": spot_context.valid_day_count,
                "skippedDays": spot_context.skipped_day_count,
                "startDate": spot_context.start_date.isoformat(),
                "endDate": spot_context.end_date.isoformat(),
                "kCount": len(spot_context.k_results or {}) if effective_status == "ready" else 0,
                "warnings": list(spot_context.warnings or []),
                "expiresAt": spot_context.expires_at.isoformat()
                if spot_context.expires_at
                else None,
            }
        if reports or generations:
            detail["reports"] = [
                self._report_summary(report, generations.get(report.task_id), next(
                    (task.version for task in tasks if task.id == report.task_id), None
                ))
                for report in reports
            ]
        return detail

    @staticmethod
    def _result_card(payload: dict | None, version: str, calculated_at: datetime) -> dict:
        """历史滚动展示所需的结果卡，不包含完整快照内部字段。"""
        payload = payload or {}
        basic = payload.get("basicInfo") or {}
        financial = payload.get("financial") or {}
        advanced = payload.get("advanced") or {}
        donut = advanced.get("donut") or {}
        coverage = advanced.get("debtServiceCoverage") or {}
        return {
            "version": payload.get("version") or version,
            "warnings": payload.get("warnings") or [],
            "basicInfo": {
                key: basic.get(key)
                for key in (
                    "province", "city", "nodeName", "capacityMwh", "powerMw",
                    "chargeCost", "dischargeReturn", "lossCost", "actualSpread",
                )
            },
            "financial": {
                key: financial.get(key)
                for key in (
                    "projectIrr", "projectStaticPayback", "capitalIrr",
                    "capitalStaticPayback", "averageProfit",
                )
            },
            "advanced": {
                "donut": {
                    key: donut.get(key)
                    for key in (
                        "totalRevenue", "energyRevenue", "capacityRevenue",
                        "frequencyRevenue", "leaseRevenue", "interventionRevenue",
                        "subsidyRevenue",
                    )
                },
                "debtServiceCoverage": {
                    "cashflowRatio": coverage.get("cashflowRatio") or [],
                },
            },
            "calculatedAt": calculated_at.isoformat(),
        }

    @staticmethod
    def _report_summary(report, generation, version):
        if report is not None:
            return {
                "reportId": report.report_id,
                "taskId": report.task_id,
                "version": version,
                "status": "completed",
                "title": report.payload.get("title"),
                "createdAt": report.created_at.isoformat(),
            }
        if generation is not None:
            return {
                "reportTaskId": generation.id,
                "taskId": generation.task_id,
                "version": version,
                "status": generation.status,
                "title": None,
                "createdAt": generation.created_at.isoformat(),
            }
        return None

    async def get_task_input(
        self, session: AsyncSession, *, task_id: int, user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> dict:
        """读取指定成功版本的冻结入参；只读快照，不访问飞书。"""
        task = await self.require_owned_task(
            session, task_id=task_id, user_id=user_id,
            readable_user_ids=readable_user_ids,
        )
        if task.status != "completed":
            raise NotFoundException("该任务暂无可用冻结入参")
        snapshot = (await session.execute(
            select(InputSnapshotORM).where(InputSnapshotORM.task_id == task.id)
        )).scalar_one_or_none()
        if snapshot is None or not snapshot.payload:
            raise NotFoundException("该任务暂无冻结入参")
        return self._task_input_payload(task, snapshot)

    async def get_task_inputs(
        self, session: AsyncSession, *, task_ids: Sequence[int], user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> list[dict]:
        """批量读取可读成功任务的冻结入参；不可用任务静默跳过。"""
        ids = list(dict.fromkeys(task_ids))
        if not ids:
            return []
        tasks = (await session.execute(
            select(CalculationTaskORM)
            .join(ConversationORM, ConversationORM.id == CalculationTaskORM.conversation_id)
            .where(
                CalculationTaskORM.id.in_(ids),
                CalculationTaskORM.status == "completed",
                ConversationORM.user_id.in_(list(readable_user_ids or [user_id])),
                ConversationORM.deleted_at.is_(None),
            )
        )).scalars().all()
        task_by_id = {task.id: task for task in tasks}
        snapshots = (await session.execute(
            select(InputSnapshotORM).where(InputSnapshotORM.task_id.in_(list(task_by_id)))
        )).scalars().all() if task_by_id else []
        snapshot_by_task = {
            snapshot.task_id: snapshot
            for snapshot in snapshots
            if snapshot.payload
        }
        return [
            self._task_input_payload(task_by_id[task_id], snapshot_by_task[task_id])
            for task_id in ids
            if task_id in task_by_id and task_id in snapshot_by_task
        ]

    @staticmethod
    def _task_input_payload(task: CalculationTaskORM, snapshot: InputSnapshotORM) -> dict:
        payload = snapshot.payload
        return {
            "taskId": task.id,
            "conversationId": task.conversation_id,
            "version": task.version,
            "input": payload.get("apiInput") or {},
            "changeMeta": payload.get("changeMeta") or {},
        }

    async def soft_delete(
        self, session: AsyncSession, *, conversation_id: str, user_id: str,
    ) -> tuple[dict, list[str]]:
        """软删除会话并撤销关联分享，返回待后台清理的飞书副本 token。"""
        conversation = await self.require_active_conversation(
            session, conversation_id=conversation_id, user_id=user_id
        )
        deleted_conversation_id = conversation.id

        # 撤销该会话的所有有效分享
        revoked = await CalculationShareService().revoke_by_conversation(
            session, conversation_id=conversation_id,
        )
        if revoked:
            logger.info("已撤销会话关联的 {} 个分享 conversation_id={}", revoked, conversation_id)

        # 一个会话可有多个版本；去重避免同一副本被重复删除。
        doc_tokens = [token for token in (await session.scalars(
            select(CalculationTaskORM.feishu_copy_url).where(
                CalculationTaskORM.conversation_id == conversation.id,
                CalculationTaskORM.feishu_copy_url.is_not(None),
            )
        )).all() if token]
        doc_tokens = list(dict.fromkeys(doc_tokens))
        await session.execute(
            delete(ConversationSpotContextORM).where(
                ConversationSpotContextORM.conversation_id == conversation.id
            )
        )
        conversation.deleted_at = datetime.now()
        await session.commit()
        return {"conversationId": deleted_conversation_id, "deleted": True}, doc_tokens

    async def rename(
        self, session: AsyncSession, *, conversation_id: str, user_id: str, title: str
    ) -> dict:
        cleaned = (title or "").strip()
        if not cleaned:
            raise ValidationException("会话标题不能为空")
        if len(cleaned) > 255:
            raise ValidationException("会话标题不能超过 255 个字符")
        conversation = await self.require_active_conversation(
            session, conversation_id=conversation_id, user_id=user_id
        )
        conversation.title = cleaned
        await session.commit()
        return {"conversationId": conversation.id, "title": conversation.title}

    async def append_message(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        role: str,
        content: str,
        message_type: str = "text",
        payload: dict | None = None,
    ) -> MessageSnapshotORM | None:
        cleaned = (content or "").strip()
        if not cleaned:
            return None
        message = MessageSnapshotORM(
            conversation_id=conversation_id,
            role=role,
            content=cleaned,
            message_type=message_type,
            payload=payload,
        )
        session.add(message)
        # 更新会话最近活动时间
        await session.execute(
            ConversationORM.__table__.update()
            .where(ConversationORM.id == conversation_id)
            .values(last_activity_at=func.now())
        )
        await session.commit()
        await session.refresh(message)
        return message

    async def append_calculation_error(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        error_message: str,
        task_id: int | None = None,
        error_code: str | int | None = None,
    ) -> MessageSnapshotORM | None:
        cleaned = (error_message or "").strip()
        if not cleaned:
            cleaned = "未知错误"
        safe_message = public_calc_error_message(cleaned, error_code)
        content = safe_message if safe_message.startswith("测算失败：") else f"测算失败：{safe_message}"
        payload = {"event_type": "calculation_error"}
        if task_id is not None:
            payload["task_id"] = task_id
        if error_code is not None:
            payload["error_code"] = public_calc_error_code(error_code, cleaned)
        return await self.append_message(
            session,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            message_type="calculation_error",
            payload=payload,
        )

    async def attach_answer_to_calculation(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        task_id: int,
        answer_text: str,
    ) -> bool:
        cleaned = (answer_text or "").strip()
        if not cleaned:
            return False
        message = (await session.execute(
            select(MessageSnapshotORM).where(
                MessageSnapshotORM.conversation_id == conversation_id,
                MessageSnapshotORM.message_type == "calculation_completed",
                MessageSnapshotORM.payload["task_id"].as_integer() == task_id,
            ).order_by(MessageSnapshotORM.created_at.desc(), MessageSnapshotORM.id.desc())
        )).scalars().first()
        if message is None:
            error_message = (await session.execute(
                select(MessageSnapshotORM).where(
                    MessageSnapshotORM.conversation_id == conversation_id,
                    MessageSnapshotORM.message_type == "calculation_error",
                    MessageSnapshotORM.payload["task_id"].as_integer() == task_id,
                ).order_by(MessageSnapshotORM.created_at.desc(), MessageSnapshotORM.id.desc())
            )).scalars().first()
            return error_message is not None
        payload = dict(message.payload or {})
        payload["answer_text"] = cleaned
        message.payload = payload
        await session.commit()
        return True

    async def require_active_conversation(
        self, session: AsyncSession, *, conversation_id: str, user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> ConversationORM:
        """默认只放行本人；readable_user_ids 仅供管理员只读查看组织成员的历史使用。

        写操作（重命名、删除、追加测算）一律不传该参数，归属边界保持不变。
        """
        conversation = (await session.execute(
            select(ConversationORM).where(
                ConversationORM.id == conversation_id,
                ConversationORM.user_id.in_(list(readable_user_ids or [user_id])),
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if conversation is None:
            raise NotFoundException("会话不存在")
        return conversation

    async def require_owned_task(
        self, session: AsyncSession, *, task_id: int, user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> CalculationTaskORM:
        task = (await session.execute(
            select(CalculationTaskORM)
            .join(
                ConversationORM,
                ConversationORM.id == CalculationTaskORM.conversation_id,
            )
            .where(
                CalculationTaskORM.id == task_id,
                ConversationORM.user_id.in_(list(readable_user_ids or [user_id])),
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if task is None:
            raise NotFoundException("任务不存在")
        return task
