"""从已冻结的测算快照构建正式报告载荷。"""
from __future__ import annotations

from datetime import date

from app.modules.report.application.report_rules import (
    MISSING_DATA_TEXT,
    REPORT_SCHEMA_VERSION,
    REPORT_STRUCTURE_VERSION,
)


def _number(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


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
    duration = capacity / power if isinstance(capacity, (int, float)) and isinstance(power, (int, float)) and power else MISSING_DATA_TEXT
    title = f"{province}{_number(power)}MW/{_number(capacity)}MWh储能项目测算方案"
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
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "structureVersion": REPORT_STRUCTURE_VERSION,
        "title": title,
        "generatedDate": (generated_on or date.today()).isoformat(),
        "source": {"taskId": task.id, "version": task.version},
        "project": {
            "province": province,
            "nodeName": basic.get("nodeName") or province,
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
        "marketSupplyDemand": sources.get("energy") if sources.get("available") else {},
        "policyEnvironment": {
            "marketStatus": market_status,
            "projectImpact": market_impact,
            "available": bool(sources.get("available")),
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
