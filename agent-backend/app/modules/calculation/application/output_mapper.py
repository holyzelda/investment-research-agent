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
    BoundaryParams,
    CalculationResult,
    DebtServiceCoverage,
    FinancialMetrics,
    RevenueDonut,
)


def _f(out: dict, key: str) -> Optional[float]:
    v = out.get(key)
    if v is None or (isinstance(v, str) and (not v.strip() or v.startswith("#"))):
        return None
    return float(v)


def _s(out: dict, key: str) -> Optional[str]:
    v = out.get(key)
    if v is None or (isinstance(v, str) and (not v.strip() or v.startswith("#"))):
        return None
    return str(v)


def _ratio_sequence(out: dict, key: str) -> list[float | None]:
    raw = out.get(key)
    if not isinstance(raw, (list, tuple)):
        return []

    values: list[float | None] = [
        None if value is None or value == "" or value == "#DIV/0!" else float(value)
        for value in raw
    ]
    last_value_index = next(
        (index for index in range(len(values) - 1, -1, -1) if values[index] is not None),
        None,
    )
    return [] if last_value_index is None else values[:last_value_index + 1]


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
        transmission_price=_f(api_output, "transmission_price"),
        line_loss_fee=_f(api_output, "line_loss_fee"),
        system_operation_fee=_f(api_output, "system_operation_fee"),
        government_fund_surcharge=_f(api_output, "government_fund_surcharge"),
    )

    financial = FinancialMetrics(
        project_irr=_f(api_output, "project_irr"),
        project_static_payback=_f(api_output, "project_static_payback"),
        capital_irr=_f(api_output, "capital_irr"),
        capital_static_payback=_f(api_output, "capital_static_payback"),
        average_profit=_f(api_output, "average_profit"),
        average_revenue=_f(api_output, "average_revenue"),
        total_investment_roi=_f(api_output, "total_investment_roi"),
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
    debt_service_coverage = DebtServiceCoverage(
        cashflow_ratio=_ratio_sequence(api_output, "cashflow_debt_service_coverage_ratio"),
    )

    return CalculationResult(
        basic_info=basic,
        financial=financial,
        advanced=AdvancedResult(
            donut=donut,
            debt_service_coverage=debt_service_coverage,
        ),
        boundary=BoundaryParams(
            equity_ratio=_f(api_output, "equity_ratio"),
            annual_operation_days=_f(api_output, "annual_operation_days"),
            repayment_method=_s(api_output, "repayment_method"),
            discount_rate=_f(api_output, "discount_rate"),
            energy_revenue_vat_rate=_f(api_output, "energy_revenue_vat_rate"),
            ancillary_service_vat_rate=_f(api_output, "ancillary_service_vat_rate"),
            capacity_compensation_vat_rate=_f(api_output, "capacity_compensation_vat_rate"),
            capacity_lease_vat_rate=_f(api_output, "capacity_lease_vat_rate"),
            subsidy_vat_rate=_f(api_output, "subsidy_vat_rate"),
            intervention_compensation_vat_rate=_f(api_output, "intervention_compensation_vat_rate"),
            income_tax_rate=_f(api_output, "income_tax_rate"),
        ),
        version=version,
        request_id=request_id,
        warnings=list(assembled.warnings),
    )
