"""正式报告载荷缺失关键项目数据时遵循模板约定。"""
from datetime import date
from types import SimpleNamespace

from app.modules.report.application.report_builder import build_report_payload
from app.modules.report.application.report_rules import MISSING_DATA_TEXT


def test_uses_template_missing_data_text_for_absent_project_identifiers():
    payload = build_report_payload(
        task=SimpleNamespace(id=1, version="V1"),
        input_snapshot=SimpleNamespace(payload={"minInput": {}, "apiInput": {}}),
        data_snapshot=SimpleNamespace(payload={"switches": {}, "warnings": {}, "reportSources": {}}),
        result_snapshot=SimpleNamespace(payload={"basicInfo": {}}),
        generated_on=date(2026, 7, 23),
    )

    assert payload["title"] == f"{MISSING_DATA_TEXT}{MISSING_DATA_TEXT}MW/{MISSING_DATA_TEXT}MWh储能项目报告"
    assert payload["project"]["province"] == MISSING_DATA_TEXT
    assert payload["project"]["powerMw"] == MISSING_DATA_TEXT
    assert payload["project"]["capacityMwh"] == MISSING_DATA_TEXT
    assert payload["project"]["durationHours"] == MISSING_DATA_TEXT
