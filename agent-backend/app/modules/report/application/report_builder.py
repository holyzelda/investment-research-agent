"""从已冻结的测算快照构建正式报告载荷。"""
from __future__ import annotations

from datetime import date

from app.modules.report.application.project_naming import (
    build_report_project_name,
    build_report_title,
)
from app.modules.report.application.report_rules import (
    MISSING_DATA_TEXT,
    REPORT_SCHEMA_VERSION,
    REPORT_STRUCTURE_VERSION,
)


def _difference(left, right) -> float | None:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return round(left - right, 4)
    return None


_POLICY_SWITCHES = (
    ("中长期市场", "switch_mid_long"),
    ("现货市场", "switch_spot"),
    ("容量补偿", "switch_capacity"),
    ("调频市场", "switch_frequency"),
    ("租赁市场", "switch_lease"),
    ("补贴政策", "switch_subsidy"),
    ("干预补偿", "switch_intervention"),
    ("过网费优惠政策", "switch_return_grid_fee"),
)


def _market_supply_demand(energy: dict) -> dict:
    return {
        "energyStructure": energy.get("能源结构"),
        "storage": energy.get("储能"),
        "generation": energy.get("发电情况"),
        "consumption": energy.get("用电情况"),
        "developmentPlan": energy.get("能源发展规划"),
    }


def build_report_payload(*, task, input_snapshot, data_snapshot, result_snapshot, generated_on=None) -> dict:
    """只消费任务快照，不读取飞书、当前配置或实时结果。"""
    api_input = input_snapshot.payload.get("apiInput", {})
    minimum = input_snapshot.payload.get("minInput", {})
    result = result_snapshot.payload
    basic = result.get("basicInfo", {})
    reports = data_snapshot.payload.get("reportSources", {})
    province = basic.get("province") or minimum.get("province") or MISSING_DATA_TEXT
    power = basic.get("powerMw") or minimum.get("powerMw") or MISSING_DATA_TEXT
    capacity = basic.get("capacityMwh") or minimum.get("capacityMwh") or MISSING_DATA_TEXT
    node_name = basic.get("nodeName") or minimum.get("nodeName") or api_input.get("node_name")
    city = basic.get("city") or api_input.get("city") or minimum.get("city")
    display_location = node_name or city
    duration = capacity / power if isinstance(capacity, (int, float)) and isinstance(power, (int, float)) and power else MISSING_DATA_TEXT
    title = build_report_title(province, display_location, power, capacity)
    project_name = build_report_project_name(province, display_location, power, capacity)
    sources = reports.get("provinceSources", {})
    charts = reports.get("charts", {})
    switches = data_snapshot.payload.get("switches", {})
    market_status = {
        key: "已启动" if value == 1 else "未启动"
        for key, value in (sources.get("marketStatus") or {}).items()
        if key != "地区"
    }
    market_impact = {
        key: "纳入测算" if value == 1 else "不纳入测算"
        for key, value in switches.items()
    }
    policy_rows = [
        {"name": name, "enabled": switches.get(switch_key) == 1}
        for name, switch_key in _POLICY_SWITCHES
    ]
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "structureVersion": REPORT_STRUCTURE_VERSION,
        "title": title,
        "generatedDate": (generated_on or date.today()).isoformat(),
        "source": {"taskId": task.id, "version": task.version},
        "project": {
            "name": project_name,
            "province": province,
            "city": city,
            "nodeName": basic.get("nodeName") or city or province,
            "powerMw": power,
            "capacityMwh": capacity,
            "durationHours": duration,
            "preparer": "西安奇点能源股份有限公司",
            "projectType": "源网侧",
            "singularityRole": "设备商+运营商",
            "owner": None,
            "expectedOperationDate": None,
            "ownerBackground": None,
        },
        "marketSupplyDemand": _market_supply_demand(sources.get("energy") or {}) if sources.get("available") else {},
        "policyEnvironment": {
            "rows": policy_rows,
            "marketStatus": market_status,
            "projectImpact": market_impact,
            "available": bool(sources.get("available")),
        },
        "marketOperations": {
            "spotChargePrice": api_input.get("spot_charge_avg"),
            "spotDischargePrice": api_input.get("spot_discharge_avg"),
            "spotSpread": _difference(api_input.get("spot_discharge_avg"), api_input.get("spot_charge_avg")),
            "transmissionPrice": basic.get("transmissionPrice"),
            "lineLossFee": basic.get("lineLossFee"),
            "systemOperationFee": basic.get("systemOperationFee"),
            "governmentFundSurcharge": basic.get("governmentFundSurcharge"),
            "chargeCost": basic.get("chargeCost"),
            "dischargeReturn": basic.get("dischargeReturn"),
            "lossCost": basic.get("lossCost"),
            "actualSpread": basic.get("actualSpread"),
            "degreeLossCost": _difference(basic.get("chargeCost"), basic.get("dischargeReturn")),
        },
        "measurementBoundary": {
            "epcUnitPrice": api_input.get("epc_unit_price"),
            "batteryReplaceCost": api_input.get("battery_replace_cost"),
            "equityRatio": result.get("boundary", {}).get("equityRatio"),
            "strategyAchievementRate": api_input.get("strategy_achievement_rate"),
            "annualOperationDays": result.get("boundary", {}).get("annualOperationDays"),
            "loanRate": api_input.get("loan_rate"),
            "loanYears": api_input.get("loan_years"),
            "operationYears": api_input.get("operation_years", 15),
            "repaymentMethod": result.get("boundary", {}).get("repaymentMethod"),
            "discountRate": result.get("boundary", {}).get("discountRate"),
            "energyRevenueVatRate": result.get("boundary", {}).get("energyRevenueVatRate"),
            "ancillaryServiceVatRate": result.get("boundary", {}).get("ancillaryServiceVatRate"),
            "capacityCompensationVatRate": result.get("boundary", {}).get("capacityCompensationVatRate"),
            "capacityLeaseVatRate": result.get("boundary", {}).get("capacityLeaseVatRate"),
            "subsidyVatRate": result.get("boundary", {}).get("subsidyVatRate"),
            "interventionCompensationVatRate": result.get("boundary", {}).get("interventionCompensationVatRate"),
            "incomeTaxRate": result.get("boundary", {}).get("incomeTaxRate"),
        },
        "financialMetrics": {
            "projectIrr": result.get("financial", {}).get("projectIrr"),
            "capitalIrr": result.get("financial", {}).get("capitalIrr"),
            "projectStaticPayback": result.get("financial", {}).get("projectStaticPayback"),
            "averageProfit": result.get("financial", {}).get("averageProfit"),
            "averageRevenue": result.get("financial", {}).get("averageRevenue"),
            "totalInvestmentRoi": result.get("financial", {}).get("totalInvestmentRoi"),
        },
        "calculation": {
            "input": api_input,
            "result": result,
            "warnings": data_snapshot.payload.get("warnings", []),
        },
        "charts": {
            "operationYears": reports.get("operationYears", api_input.get("operation_years", 15)),
            "available": bool(charts.get("available")),
            "series": charts.get("series", {}),
            "sensitivity": charts.get("sensitivity", {}),
        },
        "aiSections": {},
        "missingDataText": MISSING_DATA_TEXT,
    }
