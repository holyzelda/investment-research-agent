"""正式报告载荷：只由已冻结测算快照确定性构建。"""
from datetime import date
from types import SimpleNamespace

from app.modules.report.application.report_builder import build_report_payload
from app.modules.report.application.report_rules import MISSING_DATA_TEXT


def _snapshots(*, report_sources=None, basic_info=None):
    return {
        "task": SimpleNamespace(id=42, version="V3"),
        "input_snapshot": SimpleNamespace(payload={
            "minInput": {"province": "甘肃", "powerMw": 200, "capacityMwh": 800},
            "apiInput": {"province": "甘肃", "operation_years": 20, "switch_spot": 1},
        }),
        "data_snapshot": SimpleNamespace(payload={
            "switches": {"spot": 1, "capacity": 0, "frequency": None},
            "warnings": ["已冻结的提示"],
            "reportSources": report_sources or {},
        }),
        "result_snapshot": SimpleNamespace(payload={
            "basicInfo": basic_info or {
                "province": "甘肃", "nodeName": "兰州东", "powerMw": 200.0, "capacityMwh": 800.0,
            },
            "financial": {"projectIrr": 8.5},
        }),
    }


def test_builds_default_project_name_market_mapping_and_frozen_chart_data():
    frozen_sources = {
        "operationYears": 20,
        "provinceSources": {
            "available": True,
            "energy": {"地区": "甘肃", "新能源装机": 123},
            "marketStatus": {"地区": "甘肃", "现货市场": 1, "辅助服务市场": None},
        },
        "charts": {
            "available": True,
            "series": {"debtServiceCoverage": [1.2, None, 1.4]},
            "sensitivity": {"baseline": 1.5, "optimistic": 1.7, "pessimistic": 1.1},
        },
    }
    snapshots = _snapshots(report_sources=frozen_sources)

    payload = build_report_payload(**snapshots, generated_on=date(2026, 7, 23))

    assert payload["title"] == "甘肃200MW/800MWh储能项目测算方案"
    assert payload["generatedDate"] == "2026-07-23"
    assert payload["source"] == {"taskId": 42, "version": "V3"}
    assert payload["project"]["durationHours"] == 4
    assert payload["policyEnvironment"] == {
        "marketStatus": {"现货市场": "已启动", "辅助服务市场": "未启动"},
        "projectImpact": {"spot": "纳入测算", "capacity": "不纳入测算", "frequency": "不纳入测算"},
        "available": True,
    }
    assert payload["charts"] == {
        "operationYears": 20,
        "available": True,
        "series": {"debtServiceCoverage": [1.2, None, 1.4]},
        "sensitivity": {"baseline": 1.5, "optimistic": 1.7, "pessimistic": 1.1},
    }
    assert payload["aiSections"] == {}


def test_hides_unavailable_province_data_but_keeps_frozen_calculation_data():
    snapshots = _snapshots(report_sources={
        "operationYears": 15,
        "provinceSources": {"available": False, "energy": {"地区": "甘肃"}},
        "charts": {"available": False, "series": {"debtServiceCoverage": [1.2]}},
    })

    payload = build_report_payload(**snapshots, generated_on=date(2026, 7, 23))

    assert payload["marketSupplyDemand"] == {}
    assert payload["policyEnvironment"]["available"] is False
    assert payload["charts"]["available"] is False
    assert payload["charts"]["series"] == {"debtServiceCoverage": [1.2]}
    assert payload["calculation"]["input"] == snapshots["input_snapshot"].payload["apiInput"]
    assert payload["missingDataText"] == MISSING_DATA_TEXT
