"""测算完成时冻结正式报告专用来源；读取失败不得影响测算完成。"""
from __future__ import annotations

from app.core.config.settings import FeishuConfig


_CHART_ROWS = {
    "debtServiceCoverage": 3,
    "freeCashflow": 6,
    "operatingCashflow": 7,
    "principal": 8,
    "interest": 9,
    "netProfit": 11,
    "depreciationAmortization": 12,
}


async def freeze_report_sources(gateway, *, doc_token: str, api_input: dict, config: FeishuConfig) -> dict:
    """返回可脱离飞书的报告来源；网关不支持或读取失败时记录不可用状态。"""
    operation_years = api_input.get("operation_years", 15)
    end_column = "Q" if operation_years == 15 else "V"
    base = {
        "operationYears": operation_years,
        "provinceSources": {"available": False, "energy": {}, "marketStatus": {}, "error": None},
        "charts": {"available": False, "series": {}, "sensitivity": {}, "error": None},
    }
    reader = getattr(gateway, "read_report_sources", None)
    if reader is None:
        base["provinceSources"]["error"] = "report_source_reader_unavailable"
        base["charts"]["error"] = "report_source_reader_unavailable"
        return base
    try:
        raw = await reader(
            doc_token=doc_token,
            province=api_input.get("province"),
            energy_sheet=config.report_energy_structure_sheet,
            energy_range=config.report_energy_structure_range,
            market_sheet=config.report_market_status_sheet,
            market_range=config.report_market_status_range,
            chart_sheet=config.report_chart_sheet,
            chart_end_column=end_column,
        )
        base.update(raw)
        return base
    except Exception as exc:  # 报告辅助资料不得阻断测算
        message = str(exc)[:200]
        base["provinceSources"]["error"] = message
        base["charts"]["error"] = message
        return base
