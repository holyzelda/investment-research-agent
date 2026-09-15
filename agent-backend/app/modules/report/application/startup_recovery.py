"""报告任务启动恢复。"""
from sqlalchemy import select

from app.modules.calculation.infrastructure.persistence.orm import ReportGenerationTaskORM
from app.modules.trial_quota.application.trial_quota_service import TrialQuotaService
from app.modules.trial_quota.infrastructure.persistence.orm import TrialQuotaReservation


async def mark_interrupted_generations_failed(session) -> int:
    """服务重启后不恢复在途工作，直接让用户重新发起。"""
    rows = (await session.execute(
        select(ReportGenerationTaskORM)
        .where(ReportGenerationTaskORM.status == "generating")
        .with_for_update()
    )).scalars().all()
    quota = TrialQuotaService()
    for row in rows:
        if row.trial_quota_reserved and row.trial_quota_usage_date:
            await quota.refund(
                session,
                TrialQuotaReservation(
                    user_id=row.user_id,
                    feature="report",
                    usage_date=row.trial_quota_usage_date,
                ),
                commit=False,
            )
        row.trial_quota_reserved = False
        row.trial_quota_usage_date = None
        row.status = "failed"
        row.current_step = None
        row.error_code = "report_generation_interrupted"
        row.error_message = "服务重启导致报告生成中断，请重新生成。"
    await session.commit()
    return len(rows)
