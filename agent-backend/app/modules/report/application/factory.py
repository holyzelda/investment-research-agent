"""报告应用服务装配。"""
from app.modules.report.application.report_generation_service import ReportGenerationService
from app.modules.report.infrastructure.fake_ai_client import FakeReportAiClient


def build_report_generation_service():
    return ReportGenerationService(ai_client=FakeReportAiClient())
