"""报告任务启动恢复。"""
from sqlalchemy import update

from app.modules.calculation.infrastructure.persistence.orm import ReportGenerationTaskORM


async def mark_interrupted_generations_failed(session) -> int:
    """服务重启后不恢复在途工作，直接让用户重新发起。"""
    result = await session.execute(
        update(ReportGenerationTaskORM)
        .where(ReportGenerationTaskORM.status == "generating")
        .values(
            status="failed",
            current_step=None,
            error_code="report_generation_interrupted",
            error_message="服务重启导致报告生成中断，请重新生成。",
        )
    )
    await session.commit()
    return result.rowcount or 0
