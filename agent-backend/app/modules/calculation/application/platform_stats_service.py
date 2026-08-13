"""首页平台累计统计。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calculation.infrastructure.persistence.orm import CalculationTaskORM, ReportSnapshotORM

PLATFORM_STAT_BASELINE = {"calculationCount": 1286, "projectCount": 128, "reportCount": 256}


async def get_platform_stats(session: AsyncSession) -> dict:
    calculation_count = await session.scalar(select(func.count(CalculationTaskORM.id)))
    project_count = await session.scalar(
        select(func.count(func.distinct(CalculationTaskORM.conversation_id))).where(
            CalculationTaskORM.status == "completed"
        )
    )
    report_count = await session.scalar(select(func.count(ReportSnapshotORM.id)))
    actual = {
        "calculationCount": int(calculation_count or 0),
        "projectCount": int(project_count or 0),
        "reportCount": int(report_count or 0),
    }
    return {
        **{key: PLATFORM_STAT_BASELINE[key] + actual[key] for key in PLATFORM_STAT_BASELINE},
        "baseline": PLATFORM_STAT_BASELINE,
        "actual": actual,
    }
