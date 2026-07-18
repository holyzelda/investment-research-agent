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
    "project_irr": 8.5, "capital_irr": 12.3, "average_profit": 3200.0,
    "first_year_total_revenue": 8600.0, "first_year_energy_revenue": 5200.0,
    "first_year_intervention_revenue": 200.0,
    "cashflow_debt_service_coverage_ratio": [1, 2, 3],
}


def test_maps_financial():
    r = map_output_to_result(_basics(), _assembled(), SAMPLE)
    assert r.financial.project_irr == 8.5
    assert r.financial.capital_irr == 12.3
    assert r.financial.average_profit == 3200.0


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
        {**SAMPLE, "charge_cost": 0.3, "discharge_return": 0.05, "loss_cost": 0.02},
    )
    assert r.basic_info.province == "甘肃"
    assert r.basic_info.node_name == "兰州东"
    assert r.basic_info.charge_cost == 0.3


def test_missing_output_is_none():
    r = map_output_to_result(_basics(), _assembled(), {})
    assert r.financial.project_irr is None
    assert r.advanced.donut.total_revenue is None
