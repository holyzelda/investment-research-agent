"""测算台账：可见范围内已完成测算的可筛选查询（只读快照，不改库表）。

一行 = 一次已完成测算（ir_calculation_task.status == "completed"）：
- 会话名称取 ir_conversation.title 实时值（用户改名后台账同步变化）；
- 测算时间取任务 created_at（成功任务在测算完成、快照落库后才建记录）；
- 省份/规模/节点取入参快照，财务指标取结果快照；
- 报告状态按 task_id 关联报告快照与报告生成任务。

可见范围由 UserScope 给出：普通用户只有本人，管理员是本组织在用成员。
发起人昵称取用户管理中心实时值，只在管理员视角随行返回。
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)
from app.modules.platform_access.domain.models import UserScope

MAX_PAGE_SIZE = 100


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _end_of_day(value: date) -> datetime:
    """结束日期按闭区间处理：包含当天全部记录。"""
    return datetime.combine(value, time.max)


def _province_of(input_payload: Optional[dict], result_payload: Optional[dict]) -> Optional[str]:
    """省份优先取结果快照（展示口径），回退到冻结入参。"""
    basic = (result_payload or {}).get("basicInfo") or {}
    if basic.get("province"):
        return basic["province"]
    api_input = (input_payload or {}).get("apiInput") or {}
    min_input = (input_payload or {}).get("minInput") or {}
    return api_input.get("province") or min_input.get("province")


class CalculationLedgerService:
    """已完成测算的台账查询：列表分页 + 可见范围内的省份选项。"""

    def _visible_completed_tasks(self, user_ids: list[str]):
        return (
            select(CalculationTaskORM, ConversationORM)
            .join(ConversationORM, ConversationORM.id == CalculationTaskORM.conversation_id)
            .where(
                ConversationORM.user_id.in_(user_ids),
                ConversationORM.deleted_at.is_(None),
                CalculationTaskORM.status == "completed",
            )
        )

    async def _snapshots_for(self, session: AsyncSession, task_ids: list[int]) -> dict:
        if not task_ids:
            return {}
        inputs = {
            snapshot.task_id: snapshot.payload
            for snapshot in (await session.execute(
                select(InputSnapshotORM).where(InputSnapshotORM.task_id.in_(task_ids))
            )).scalars().all()
        }
        results = {
            snapshot.task_id: snapshot.payload
            for snapshot in (await session.execute(
                select(CalculationResultSnapshotORM).where(
                    CalculationResultSnapshotORM.task_id.in_(task_ids)
                )
            )).scalars().all()
        }
        return {
            task_id: (inputs.get(task_id), results.get(task_id))
            for task_id in task_ids
        }

    async def list_provinces(self, session: AsyncSession, *, scope: UserScope) -> list[str]:
        """筛选项只给可见范围内实际测算过的省份，避免筛出空结果。"""
        task_ids = (await session.execute(
            self._visible_completed_tasks(scope.user_ids)
            .with_only_columns(CalculationTaskORM.id)
        )).scalars().all()
        snapshots = await self._snapshots_for(session, list(task_ids))
        provinces = {
            province
            for input_payload, result_payload in snapshots.values()
            if (province := _province_of(input_payload, result_payload))
        }
        return sorted(provinces)

    async def list_records(
        self,
        session: AsyncSession,
        *,
        scope: UserScope,
        initiator_user_ids: Optional[list[str]] = None,
        keyword: Optional[str] = None,
        provinces: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        page = max(page, 1)
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

        user_ids = scope.visible_ids(initiator_user_ids)
        if not user_ids:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}

        query = self._visible_completed_tasks(user_ids)
        if keyword and (cleaned := keyword.strip()):
            # 关键词命中会话名称或发起人昵称；昵称只在用户管理中心，先反查成 user_id 再下推。
            # 普通用户看不到发起人列，按昵称匹配会莫名返回全部记录，故只对管理员生效。
            matched_users = [
                user.user_id for user in scope.users if cleaned in user.nick_name
            ] if scope.is_admin else []
            title_match = ConversationORM.title.like(f"%{cleaned}%")
            query = query.where(
                or_(title_match, ConversationORM.user_id.in_(matched_users))
                if matched_users else title_match
            )
        if start_date is not None:
            query = query.where(CalculationTaskORM.created_at >= _start_of_day(start_date))
        if end_date is not None:
            query = query.where(CalculationTaskORM.created_at <= _end_of_day(end_date))

        rows = (await session.execute(
            query.order_by(CalculationTaskORM.created_at.desc(), CalculationTaskORM.id.desc())
        )).all()
        if not rows:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}

        task_ids = [task.id for task, _ in rows]
        snapshots = await self._snapshots_for(session, task_ids)
        reports = await self._report_status_by_task(session, task_ids)

        # 省份只存在于 JSON 快照，跨 MySQL/sqlite 无法可靠下推为 SQL 条件，故在应用层过滤后分页。
        selected = {province for province in (provinces or []) if province}
        records = []
        for task, conversation in rows:
            input_payload, result_payload = snapshots.get(task.id, (None, None))
            province = _province_of(input_payload, result_payload)
            if selected and province not in selected:
                continue
            record = self._serialize(
                task, conversation, input_payload, result_payload, reports.get(task.id),
            )
            if scope.is_admin:
                # 发起人只在管理员视角出现；普通用户台账不该多出这一列。
                record["initiator"] = {
                    "userId": conversation.user_id,
                    "nickName": scope.nick_name_of(conversation.user_id) or conversation.username,
                }
            records.append(record)

        offset = (page - 1) * page_size
        return {
            "items": records[offset:offset + page_size],
            "total": len(records),
            "page": page,
            "pageSize": page_size,
        }

    async def _report_status_by_task(self, session: AsyncSession, task_ids: list[int]) -> dict:
        """已生成报告优先；否则取生成任务状态（生成中 / 生成失败）。"""
        statuses: dict[int, dict] = {}
        generations = (await session.execute(
            select(ReportGenerationTaskORM).where(ReportGenerationTaskORM.task_id.in_(task_ids))
        )).scalars().all()
        for generation in generations:
            statuses[generation.task_id] = {
                "status": generation.status,
                "reportId": generation.report_id,
            }
        reports = (await session.execute(
            select(ReportSnapshotORM).where(ReportSnapshotORM.task_id.in_(task_ids))
        )).scalars().all()
        for report in reports:
            statuses[report.task_id] = {"status": "completed", "reportId": report.report_id}
        return statuses

    @staticmethod
    def _serialize(task, conversation, input_payload, result_payload, report) -> dict:
        api_input = (input_payload or {}).get("apiInput") or {}
        min_input = (input_payload or {}).get("minInput") or {}
        basic = (result_payload or {}).get("basicInfo") or {}
        financial = (result_payload or {}).get("financial") or {}
        report = report or {}
        return {
            "taskId": task.id,
            "conversationId": task.conversation_id,
            "title": conversation.title,
            "version": task.version,
            "calculatedAt": task.created_at.isoformat(),
            "province": _province_of(input_payload, result_payload),
            "city": basic.get("city") or api_input.get("city") or min_input.get("city"),
            "nodeName": basic.get("nodeName") or api_input.get("node_name") or min_input.get("nodeName"),
            "powerMw": basic.get("powerMw", api_input.get("power_mw")),
            "capacityMwh": basic.get("capacityMwh", api_input.get("capacity_mwh")),
            "projectIrr": financial.get("projectIrr"),
            "projectStaticPayback": financial.get("projectStaticPayback"),
            "report": {
                "status": report.get("status") or "not_generated",
                "reportId": report.get("reportId"),
            },
        }
