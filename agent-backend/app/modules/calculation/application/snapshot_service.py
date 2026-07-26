"""calculation 应用层 · 快照服务（会话、任务与测算结果持久化）。

一次成功测算独立落会话、任务、输入、数据、飞书 I/O、测算结果和对话消息快照。
`calculation_result_snapshot` 用 to_report_payload 组装——仅凭它即可重建结果三模块，不依赖飞书副本。
`report_snapshot` 仅为未来正式报告保留，本服务不写入它。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calculation.application.param_assembler import AssembledParams
from app.modules.calculation.application.result_view import to_report_payload
from app.modules.calculation.domain.result import CalculationResult
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
)


class SnapshotService:
    async def create_conversation(
        self, session: AsyncSession, *, user_id: str, username: str, title: Optional[str] = None
    ) -> str:
        conv = ConversationORM(user_id=user_id, username=username, title=title)
        session.add(conv)
        await session.flush()
        return conv.id

    async def persist_success(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        version: str,
        request_id: str,
        param_hash: str,
        doc_token: str,
        assembled: AssembledParams,
        api_output: dict,
        api_meta: dict,
        result: CalculationResult,
        min_input: dict,
        report_sources: Optional[dict] = None,
        user_message: Optional[str] = None,
        assistant_message: Optional[str] = None,
    ) -> int:
        """落一次成功测算的 6 类快照（conversation 已由调用方建），返回 task_id。"""
        task = CalculationTaskORM(
            conversation_id=conversation_id,
            version=version,
            status="completed",
            request_id=request_id,
            param_hash=param_hash,
            feishu_copy_url=doc_token,
        )
        session.add(task)
        await session.flush()  # 取 task.id

        session.add(InputSnapshotORM(
            task_id=task.id,
            payload={"minInput": min_input, "apiInput": assembled.api_input},
        ))
        session.add(DataSnapshotORM(
            task_id=task.id,
            payload={
                "switches": assembled.switches,
                "warnings": assembled.warnings,
                "reportSources": report_sources or {},
            },
        ))
        session.add(FeishuIoSnapshotORM(
            task_id=task.id,
            api_input=assembled.api_input,
            api_output=api_output,
            api_meta=api_meta,
        ))
        session.add(CalculationResultSnapshotORM(task_id=task.id, payload=to_report_payload(result)))

        if user_message:
            session.add(MessageSnapshotORM(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                message_type="text",
                payload=None,
            ))
        if assistant_message:
            session.add(MessageSnapshotORM(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                message_type="text",
                payload=None,
            ))

        await session.commit()
        return task.id
