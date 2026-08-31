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
            "financial": {"projectIrr": 8.5, "averageRevenue": 4500.5},
        }),
    }


def test_builds_henan_city_in_canonical_project_payload():
    snapshots = _snapshots()
    snapshots["input_snapshot"].payload["apiInput"]["city"] = "郑州"
    snapshots["input_snapshot"].payload["minInput"]["city"] = "郑州"
    snapshots["result_snapshot"].payload["basicInfo"].update({
        "province": "河南", "city": "郑州", "nodeName": None,
    })

    payload = build_report_payload(**snapshots)

    assert payload["project"]["city"] == "郑州"
    assert "cityName" not in payload["project"]
    assert payload["title"] == "河南省郑州200MW/800MWh储能项目报告"



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

    assert payload["title"] == "甘肃省兰州东200MW/800MWh储能项目报告"
    assert payload["project"]["name"] == "甘肃省兰州东200MW/800MWh独立储能项目"
    assert payload["generatedDate"] == "2026-07-23"
    assert payload["source"] == {"taskId": 42, "version": "V3"}
    assert payload["project"]["durationHours"] == 4
    assert payload["policyEnvironment"] == {
        "rows": [
            {"name": "中长期市场", "enabled": False},
            {"name": "现货市场", "enabled": False},
            {"name": "容量补偿", "enabled": False},
            {"name": "调频市场", "enabled": False},
            {"name": "租赁市场", "enabled": False},
            {"name": "补贴政策", "enabled": False},
            {"name": "干预补偿", "enabled": False},
            {"name": "过网费优惠政策", "enabled": False},
        ],
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


def test_builds_ordered_template_sources_for_market_supply_and_policy_environment():
    snapshots = _snapshots(report_sources={
        "provinceSources": {
            "available": True,
            "energy": {
                "地区": "甘肃",
                "能源结构": "新能源与火电结构。",
                "储能": "独立储能项目储备。",
                "发电情况": "发电量稳步增长。",
                "用电情况": "全社会用电量增长。",
                "能源发展规划": "规划新增新能源装机。",
            },
        },
    })
    snapshots["data_snapshot"].payload["switches"] = {
        "switch_mid_long": 1,
        "switch_spot": 0,
        "switch_capacity": None,
        "switch_frequency": 1,
        "switch_lease": 0,
        "switch_subsidy": 1,
        "switch_intervention": 0,
        "switch_return_grid_fee": 1,
    }

    payload = build_report_payload(**snapshots)

    assert payload["marketSupplyDemand"] == {
        "energyStructure": "新能源与火电结构。",
        "storage": "独立储能项目储备。",
        "generation": "发电量稳步增长。",
        "consumption": "全社会用电量增长。",
        "developmentPlan": "规划新增新能源装机。",
    }
    assert payload["policyEnvironment"]["rows"] == [
        {"name": "中长期市场", "enabled": True},
        {"name": "现货市场", "enabled": False},
        {"name": "容量补偿", "enabled": False},
        {"name": "调频市场", "enabled": True},
        {"name": "租赁市场", "enabled": False},
        {"name": "补贴政策", "enabled": True},
        {"name": "干预补偿", "enabled": False},
        {"name": "过网费优惠政策", "enabled": True},
    ]


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
            "actualSpread": 0.42,
            "transmissionPrice": 0.0123, "lineLossFee": 0.0034,
            "systemOperationFee": 0.0056, "governmentFundSurcharge": 0.0078,
        },
        "boundary": {
            "equityRatio": 0.2,
            "annualOperationDays": 330,
            "repaymentMethod": "等额本息",
            "discountRate": 0.04,
            "energyRevenueVatRate": 0.13,
            "ancillaryServiceVatRate": 0.13,
            "capacityCompensationVatRate": 0.13,
            "capacityLeaseVatRate": 0.06,
            "subsidyVatRate": 0.13,
            "interventionCompensationVatRate": 0.09,
            "incomeTaxRate": 0.25,
        },
        "financial": {
            "projectIrr": 8.5, "capitalIrr": 12.3, "projectStaticPayback": 9.1,
            "averageProfit": 3200, "averageRevenue": 4500.5, "totalInvestmentRoi": 7.8,
        },
    })
    snapshots["data_snapshot"].payload["reportSources"] = {
        "charts": {},
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
        "actualSpread": 0.42,
        "degreeLossCost": 0.2801,
    }
    assert payload["measurementBoundary"]["equityRatio"] == 0.2
    assert payload["measurementBoundary"]["annualOperationDays"] == 330
    assert payload["measurementBoundary"]["operationYears"] == 20
    assert payload["measurementBoundary"]["repaymentMethod"] == "等额本息"
    assert payload["measurementBoundary"]["discountRate"] == 0.04
    assert payload["measurementBoundary"]["energyRevenueVatRate"] == 0.13
    assert payload["measurementBoundary"]["capacityLeaseVatRate"] == 0.06
    assert payload["measurementBoundary"]["incomeTaxRate"] == 0.25
    assert payload["financialMetrics"] == {
        "projectIrr": 8.5,
        "capitalIrr": 12.3,
        "projectStaticPayback": 9.1,
        "averageProfit": 3200,
        "averageRevenue": 4500.5,
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
