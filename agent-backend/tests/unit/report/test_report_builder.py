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
            "averageRevenue": [100, 200, 300],
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
        "averageRevenue": [100, 200, 300],
        "sensitivity": {"baseline": 1.5, "optimistic": 1.7, "pessimistic": 1.1},
    }
    assert payload["aiSections"] == {}


def test_builds_template_facing_operations_boundary_and_financial_sections():
    snapshots = _snapshots(report_sources={"charts": {}})
    snapshots["input_snapshot"].payload["apiInput"].update({
        "epc_unit_price": 0.75,
        "battery_replace_cost": 0.30,
        "strategy_achievement_rate": 0.9,
        "loan_rate": 0.04,
        "loan_years": 10,
    })
    snapshots["result_snapshot"].payload.update({
        "basicInfo": {
            "province": "甘肃", "powerMw": 200, "capacityMwh": 800,
            "chargeCost": 0.3012, "dischargeReturn": 0.0211, "lossCost": 0.0045,
            "transmissionPrice": 0.0123, "lineLossFee": 0.0034,
            "systemOperationFee": 0.0056, "governmentFundSurcharge": 0.0078,
        },
        "boundary": {"equityRatio": 0.2, "annualOperationDays": 330},
        "financial": {
            "projectIrr": 8.5, "capitalIrr": 12.3, "projectStaticPayback": 9.1,
            "averageProfit": 3200, "totalInvestmentRoi": 7.8,
        },
    })
    snapshots["data_snapshot"].payload["reportSources"] = {
        "charts": {"averageRevenue": [100, None, 300]},
    }

    payload = build_report_payload(**snapshots, generated_on=date(2026, 7, 23))

    assert payload["marketOperations"] == {
        "spotChargePrice": None,
        "spotDischargePrice": None,
        "spotSpread": None,
        "transmissionPrice": 0.0123,
        "lineLossFee": 0.0034,
        "systemOperationFee": 0.0056,
        "governmentFundSurcharge": 0.0078,
        "chargeCost": 0.3012,
        "dischargeReturn": 0.0211,
        "lossCost": 0.0045,
        "actualSpread": 0.2801,
    }
    assert payload["measurementBoundary"]["equityRatio"] == 0.2
    assert payload["measurementBoundary"]["annualOperationDays"] == 330
    assert payload["measurementBoundary"]["operationYears"] == 20
    assert payload["financialMetrics"] == {
        "projectIrr": 8.5,
        "capitalIrr": 12.3,
        "projectStaticPayback": 9.1,
        "averageProfit": 3200,
        "averageRevenue": 200.0,
        "totalInvestmentRoi": 7.8,
    }


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
