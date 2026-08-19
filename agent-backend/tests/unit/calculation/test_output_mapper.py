"""输出映射器 · 单测（API_OUTPUT dict → CalculationResult）。"""
from app.modules.calculation.application.output_mapper import map_output_to_result
from app.modules.calculation.application.result_view import to_report_payload
from app.modules.calculation.application.param_assembler import AssembledParams
from app.modules.calculation.domain.models import ProjectBasics


def _basics(node=None):
    return ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200, node_name=node)


def _assembled():
    return AssembledParams()


SAMPLE = {
    "project_irr": 8.5, "capital_irr": 12.3, "average_profit": 3200.0, "average_revenue": 4500.5,
    "first_year_total_revenue": 8600.0, "first_year_energy_revenue": 5200.0,
    "first_year_intervention_revenue": 200.0,
    "cashflow_debt_service_coverage_ratio": [1, 2, 3],
}


def test_maps_financial():
    r = map_output_to_result(_basics(), _assembled(), SAMPLE)
    assert r.financial.project_irr == 8.5
    assert r.financial.capital_irr == 12.3
    assert r.financial.average_profit == 3200.0
    assert r.financial.average_revenue == 4500.5
    assert to_report_payload(r)["financial"]["averageRevenue"] == 4500.5


def test_maps_donut_and_intervention_key():
    r = map_output_to_result(_basics(), _assembled(), SAMPLE)
    assert r.advanced.donut.total_revenue == 8600.0
    assert r.advanced.donut.energy_revenue == 5200.0
    # 干预 key 用 intervention（翻译订正后的契约）
    assert r.advanced.donut.intervention_revenue == 200.0


def test_maps_cashflow_debt_service_coverage_and_trims_trailing_blanks():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"cashflow_debt_service_coverage_ratio": [1.2, 0, None, "1.5", "", None]},
    )

    assert result.advanced.debt_service_coverage.cashflow_ratio == [1.2, 0.0, None, 1.5]


def test_maps_all_blank_cashflow_debt_service_coverage_to_empty_list():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"cashflow_debt_service_coverage_ratio": [None, "", None]},
    )

    assert result.advanced.debt_service_coverage.cashflow_ratio == []


def test_report_payload_uses_debt_service_coverage_camel_case_contract():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"cashflow_debt_service_coverage_ratio": [1.2, None, 1.4]},
    )

    assert to_report_payload(result)["advanced"]["debtServiceCoverage"] == {
        "cashflowRatio": [1.2, None, 1.4],
    }


def test_basic_info_from_basics_and_region_output():
    r = map_output_to_result(
        _basics(node="兰州东"),
        _assembled(),
        {**SAMPLE, "charge_cost": 0.3, "discharge_return": 0.05, "loss_cost": 0.02, "actual_spread": 0.41},
    )
    assert r.basic_info.province == "甘肃"
    assert r.basic_info.node_name == "兰州东"
    assert r.basic_info.charge_cost == 0.3
    assert r.basic_info.actual_spread == 0.41
    assert to_report_payload(r)["basicInfo"]["actualSpread"] == 0.41


def test_maps_report_only_outputs_into_their_calculation_domain_groups():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {
            "transmission_price": 0.0123,
            "line_loss_fee": 0.0045,
            "system_operation_fee": 0.0067,
            "government_fund_surcharge": 0.0089,
            "equity_ratio": 0.2,
            "annual_operation_days": 330,
            "total_investment_roi": 7.8,
        },
    )

    assert result.basic_info.transmission_price == 0.0123
    assert result.basic_info.line_loss_fee == 0.0045
    assert result.basic_info.system_operation_fee == 0.0067
    assert result.basic_info.government_fund_surcharge == 0.0089
    assert result.boundary.equity_ratio == 0.2
    assert result.boundary.annual_operation_days == 330.0
    assert result.financial.total_investment_roi == 7.8


def test_maps_and_serializes_frozen_report_boundary_outputs():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {
            "repayment_method": "等额本息",
            "discount_rate": 0.04,
            "energy_revenue_vat_rate": 0.13,
            "ancillary_service_vat_rate": 0.13,
            "capacity_compensation_vat_rate": 0.13,
            "capacity_lease_vat_rate": 0.06,
            "subsidy_vat_rate": 0.13,
            "intervention_compensation_vat_rate": 0.09,
            "income_tax_rate": 0.25,
        },
    )

    assert result.boundary.repayment_method == "等额本息"
    assert result.boundary.discount_rate == 0.04
    assert result.boundary.intervention_compensation_vat_rate == 0.09
    assert to_report_payload(result)["boundary"]["incomeTaxRate"] == 0.25


def test_maps_blank_and_feishu_error_boundary_outputs_to_none():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"repayment_method": "#VALUE!", "discount_rate": "", "income_tax_rate": "#N/A"},
    )

    assert result.boundary.repayment_method is None
    assert result.boundary.discount_rate is None
    assert result.boundary.income_tax_rate is None


def test_maps_feishu_error_values_to_none_without_failing_calculation():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"charge_cost": "#N/A", "total_investment_roi": "#DIV/0!"},
    )

    assert result.basic_info.charge_cost is None
    assert result.financial.total_investment_roi is None


def test_report_payload_serializes_new_calculation_fields():
    result = map_output_to_result(
        _basics(),
        _assembled(),
        {"transmission_price": 0.0123, "equity_ratio": 0.2, "total_investment_roi": 7.8},
    )

    payload = to_report_payload(result)
    assert payload["basicInfo"]["transmissionPrice"] == 0.0123
    assert payload["boundary"] == {
        "equityRatio": 0.2,
        "annualOperationDays": None,
        "repaymentMethod": None,
        "discountRate": None,
        "energyRevenueVatRate": None,
        "ancillaryServiceVatRate": None,
        "capacityCompensationVatRate": None,
        "capacityLeaseVatRate": None,
        "subsidyVatRate": None,
        "interventionCompensationVatRate": None,
        "incomeTaxRate": None,
    }
    assert payload["financial"]["totalInvestmentRoi"] == 7.8


def test_missing_output_is_none():
    r = map_output_to_result(_basics(), _assembled(), {})
    assert r.financial.project_irr is None
    assert r.advanced.donut.total_revenue is None
