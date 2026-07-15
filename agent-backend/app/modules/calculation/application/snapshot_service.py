"""calculation 应用层 · 快照服务（7 类快照持久化 + report_snapshot 组装）。

一次成功测算独立落 7 类快照（不覆盖历史）：
- conversation（会话，归属 user_id/username；由 create_conversation 建，跨多次测算复用）
- calculation_task（版本/状态/request_id/param_hash/飞书副本）
- input_snapshot（最小入参 + 冻结 API_INPUT）
- data_snapshot（各省收益结构开关/组装告警等取数中间态）
- feishu_io_snapshot（API_INPUT/OUTPUT/META 全量）
- report_snapshot（渲染就绪三模块，历史展示唯一数据源，含环形/折线底层数值）
- message_snapshot（对话回放，user/assistant）

report_snapshot 用 to_report_payload 组装——仅凭它即可重建结果三模块，不依赖飞书副本。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calculation.application.param_assembler import AssembledParams
from app.modules.calculation.application.result_view import to_report_payload
from app.modules.calculation.domain.result import CalculationResult
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportSnapshotORM,
)


class SnapshotService:
    async def create_conversation(
        self, session: AsyncSession, *, user_id: str, username: str, title: Optional[str] = None
    ) -> int:
        conv = ConversationORM(user_id=user_id, username=username, title=title)
        session.add(conv)
        await session.flush()
        return conv.id

    async def persist_success(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
        version: str,
        request_id: str,
        param_hash: str,
        doc_token: str,
        assembled: AssembledParams,
        api_output: dict,
        api_meta: dict,
        result: CalculationResult,
        min_input: dict,
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
            },
        ))
        session.add(FeishuIoSnapshotORM(
            task_id=task.id,
            api_input=assembled.api_input,
            api_output=api_output,
            api_meta=api_meta,
        ))
        session.add(ReportSnapshotORM(task_id=task.id, payload=to_report_payload(result)))

        if user_message:
            session.add(MessageSnapshotORM(
                conversation_id=conversation_id, role="user", content=user_message))
        if assistant_message:
            session.add(MessageSnapshotORM(
                conversation_id=conversation_id, role="assistant", content=assistant_message))

        await session.commit()
        return task.id
