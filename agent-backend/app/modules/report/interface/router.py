"""正式报告 REST 与持久化进度事件接口。"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session, get_sessionmaker
from app.modules.platform_access.domain.models import CurrentUser, UserScope
from app.modules.platform_access.interface.deps import get_current_user, get_user_scope
from app.modules.report.application.factory import build_report_generation_service
from app.modules.trial_quota.application.trial_quota_service import TrialQuotaService
from app.modules.trial_quota.application.trial_role_service import TrialRoleService
from app.modules.trial_quota.interface.deps import (
    get_trial_quota_service,
    get_trial_role_service,
)

router = APIRouter(prefix="/ir", tags=["report"])


async def _run_in_background(report_task_id: int) -> None:
    """后台执行必须独占会话，不能持有创建请求的 session。"""
    async with get_sessionmaker()() as session:
        await build_report_generation_service().run(session, report_task_id=report_task_id)


@router.post("/calc/tasks/{task_id}/report")
async def create_report(
    task_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    trial_role: TrialRoleService = Depends(get_trial_role_service),
    trial_quota: TrialQuotaService = Depends(get_trial_quota_service),
):
    service = build_report_generation_service()
    is_trial = await trial_role.is_trial(user.user_id)
    data = await service.start(
        session,
        task_id=task_id,
        user_id=user.user_id,
        username=user.username,
        is_trial=is_trial,
        trial_quota=trial_quota,
    )
    if data.pop("shouldRun", False):
        asyncio.create_task(_run_in_background(data["reportTaskId"]))
    return ok(data)


@router.get("/report-tasks/{report_task_id}")
async def get_report_task(
    report_task_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    data = await build_report_generation_service().get_task(
        session, report_task_id=report_task_id, user_id=user.user_id
    )
    return ok(data)


@router.get("/report-tasks/{report_task_id}/events")
async def stream_report_events(
    report_task_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    async def events():
        emitted_steps = 0
        while True:
            async with get_sessionmaker()() as session:
                data = await build_report_generation_service().get_task(
                    session, report_task_id=report_task_id, user_id=user.user_id
                )
            for step in data["steps"][emitted_steps:]:
                yield f"event: step\ndata: {json.dumps(step, ensure_ascii=False)}\n\n"
            emitted_steps = len(data["steps"])
            if data["status"] in {"completed", "failed"}:
                event = "complete" if data["status"] == "completed" else "failed"
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
):
    """只读正式报告。管理员可读本组织在用成员的报告；生成类接口仍限本人。"""
    report = await build_report_generation_service().get_report(
        session, report_id=report_id, user_id=user.user_id,
        readable_user_ids=scope.user_ids,
    )
    return ok(report.payload)
