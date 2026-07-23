"""报告专用飞书资料在测算成功时冻结。"""
import pytest

from app.core.config.settings import FeishuConfig
from app.modules.calculation.application.report_source_freezer import freeze_report_sources


class ReportSourceReader:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def read_report_sources(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(("operation_years", "expected_end", "expected_count"), [(15, "Q", 15), (20, "V", 20)])
async def test_freezes_the_operation_period_specific_chart_source(operation_years, expected_end, expected_count):
    source = {
        "operationYears": operation_years,
        "provinceSources": {"available": True, "energy": {"地区": "甘肃"}, "marketStatus": {}, "error": None},
        "charts": {"available": True, "series": {"debtServiceCoverage": [None] * expected_count}, "sensitivity": {}, "error": None},
    }
    gateway = ReportSourceReader(result=source)

    frozen = await freeze_report_sources(
        gateway,
        doc_token="frozen-copy",
        api_input={"province": "甘肃", "operation_years": operation_years},
        config=FeishuConfig(),
    )

    assert gateway.calls[0]["chart_end_column"] == expected_end
    assert frozen == source


@pytest.mark.asyncio
async def test_report_source_read_failure_is_frozen_as_unavailable_instead_of_breaking_calculation():
    frozen = await freeze_report_sources(
        ReportSourceReader(error=RuntimeError("读取失败")),
        doc_token="frozen-copy",
        api_input={"province": "甘肃", "operation_years": 15},
        config=FeishuConfig(),
    )

    assert frozen["provinceSources"] == {"available": False, "energy": {}, "marketStatus": {}, "error": "读取失败"}
    assert frozen["charts"] == {"available": False, "series": {}, "sensitivity": {}, "error": "读取失败"}
