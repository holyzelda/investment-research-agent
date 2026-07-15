"""calculation 应用层 · 输出映射器。

把飞书 API_OUTPUT（param_id → 值，含地区成本三项）+ 组装结果里的基本信息/告警，
映射成前端消费的 CalculationResult（结果三模块）。

output param_id 与 param_dict.json 的 output 规格一一对应；本映射器只做
"归一化字典 → 结构化 DTO"，不做任何计算。
"""
from typing import Optional

from app.modules.calculation.application.param_assembler import AssembledParams
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.domain.result import (
    AdvancedResult,
    BasicInfo,
    CalculationResult,
    CashflowLines,
    FinancialMetrics,
    RevenueDonut,
)


def _f(out: dict, key: str) -> Optional[float]:
    v = out.get(key)
    return None if v is None else float(v)


def _seq(out: dict, key: str) -> list:
    v = out.get(key)
    return list(v) if isinstance(v, (list, tuple)) else []


def map_output_to_result(
    basics: ProjectBasics,
    assembled: AssembledParams,
    api_output: dict,
    *,
    version: Optional[str] = None,
    request_id: Optional[str] = None,
) -> CalculationResult:
    basic = BasicInfo(
        province=basics.province,
        capacity_mwh=basics.capacity_mwh,
        power_mw=basics.power_mw,
        node_name=basics.node_name,
        charge_cost=_f(api_output, "charge_cost"),
        discharge_return=_f(api_output, "discharge_return"),
        loss_cost=_f(api_output, "loss_cost"),
    )

    financial = FinancialMetrics(
        project_irr=_f(api_output, "project_irr"),
        project_static_payback=_f(api_output, "project_static_payback"),
        capital_irr=_f(api_output, "capital_irr"),
        capital_static_payback=_f(api_output, "capital_static_payback"),
        average_profit=_f(api_output, "average_profit"),
    )

    donut = RevenueDonut(
        total_revenue=_f(api_output, "first_year_total_revenue"),
        energy_revenue=_f(api_output, "first_year_energy_revenue"),
        capacity_revenue=_f(api_output, "first_year_capacity_revenue"),
        frequency_revenue=_f(api_output, "first_year_frequency_revenue"),
        lease_revenue=_f(api_output, "first_year_lease_revenue"),
        intervention_revenue=_f(api_output, "first_year_intervention_revenue"),
        subsidy_revenue=_f(api_output, "first_year_subsidy_revenue"),
    )
    lines = CashflowLines(
        main_business_cost=_seq(api_output, "main_business_cost"),
        current_principal_interest=_seq(api_output, "current_principal_interest"),
        capital_net_cashflow=_seq(api_output, "capital_net_cashflow"),
        total_invest_net_cashflow_after_tax=_seq(api_output, "total_invest_net_cashflow_after_tax"),
    )

    return CalculationResult(
        basic_info=basic,
        financial=financial,
        advanced=AdvancedResult(donut=donut, lines=lines),
        version=version,
        request_id=request_id,
        warnings=list(assembled.warnings),
    )
