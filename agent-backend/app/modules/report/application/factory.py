from app.core.config.settings import get_settings
from app.modules.report.application.report_generation_service import ReportGenerationService
from app.modules.report.infrastructure.model_pool_ai_client import ModelPoolReportAiClient


def build_report_generation_service():
    config = get_settings().middle_platform
    return ReportGenerationService(
        ai_client=ModelPoolReportAiClient(config),
        ai_concurrency=config.report_model_concurrency,
    )
