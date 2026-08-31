"""参数字典聚合 · 单测。"""
from app.modules.calculation.domain.models import Direction, ParamSource
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository


def _dict():
    return JsonParamDictRepository().load()


def test_dictionary_loads():
    d = _dict()
    assert len(d) == 68  # 6对话+10默认（含贷款年限）+2现货+9开关+5明细+2中长期均价+4地区/基础输出+30输出

def test_city_is_app_side_metadata_without_api_mapping():
    city = _dict().get("city")
    assert city is not None
    assert city.source == ParamSource.DIALOG.value
    assert city.api_cell is None
    assert city.writable is True and city.direction == Direction.INPUT.value

    """表2开关 F=0，但仍应写入 API_INPUT（F 列只管展示）。"""
    d = _dict()
    sw = d.get("switch_spot")
    assert sw.f == 0 and sw.writable is True and sw.direction == Direction.INPUT.value

def test_writable_inputs_include_mid_long_exclude_output():
    d = _dict()
    inputs = d.writable_inputs()
    assert all(s.direction == Direction.INPUT.value and s.writable for s in inputs)
    ids = {s.id for s in inputs}
    # 中长期均价来源后端 json，现写入 API_INPUT
    assert "mid_long_charge_avg" in ids
    # 输出项（含地区成本三项）不在写入集合
    assert "charge_cost" not in ids
    assert "project_irr" not in ids
    # 表2开关在写入集合
    assert "switch_spot" in ids

def test_reclassified_params_directions():
    """中长期均价改为 input（写 API_INPUT）；地区成本三项改为 output（读 API_OUTPUT）。"""
    d = _dict()
    assert d.get("mid_long_charge_avg").direction == Direction.INPUT.value
    assert d.get("mid_long_charge_avg").api_cell == "API_INPUT!B32"
    assert d.get("mid_long_discharge_avg").api_cell == "API_INPUT!B33"
    assert d.get("charge_cost").direction == Direction.OUTPUT.value
    assert d.get("charge_cost").api_cell == "API_OUTPUT!B14"
    assert d.get("loss_cost").api_cell == "API_OUTPUT!B16"
    assert d.get("actual_spread").direction == Direction.OUTPUT.value
    assert d.get("actual_spread").api_cell == "API_OUTPUT!B34"

def test_defaults_present():
    d = _dict()
    defaults = d.defaults()
    assert defaults["epc_unit_price"] == 0.75
    assert defaults["operation_years"] == 15
    assert defaults["loan_rate"] == 0.04
    assert defaults["loan_years"] == 10


def test_operation_years_is_a_template_selection_without_api_input_mapping():
    spec = _dict().get("operation_years")
    assert spec.control == "select"
    assert spec.options == [
        {"value": 15, "label": "15年"},
        {"value": 20, "label": "20年"},
    ]
    assert spec.api_cell is None

def test_battery_replace_cost_variants_by_operation_years():
    """换电成本按运营期分档：15年固定0，20年默认0.3、slider 0~1 步长0.01。"""
    d = _dict()
    spec = d.get("battery_replace_cost")
    assert spec.variants == {
        "15": {"control": "fixed", "default": 0},
        "20": {"control": "slider", "default": 0.3, "min": 0, "max": 1, "step": 0.01},
    }
    assert d.variant("battery_replace_cost", 20)["default"] == 0.3
    assert d.variant("battery_replace_cost", 20)["control"] == "slider"
    assert d.variant("battery_replace_cost", 15)["control"] == "fixed"
    assert d.variant("battery_replace_cost", 21) is None
    assert d.variant("operation_years", 20) is None  # 无 variants 的参数返回 None

def test_corrected_cells():
    """位置订正核对。"""
    d = _dict()
    assert d.get("maint_cost").model_cell == "输入1-基础参数!D75"
    assert d.get("opex_cost").model_cell == "输入1-基础参数!D77"
    assert d.get("switch_spot").model_cell == "输入1-基础参数!D37"
    assert d.get("first_year_energy_revenue").model_cell == "营业收入、税金及附加!C6"


def test_maintenance_and_operations_cost_ranges_are_capped_at_one_cent_per_wh():
    d = _dict()
    assert d.get("maint_cost").max == 0.02
    assert d.get("opex_cost").max == 0.02
    loan_years = d.get("loan_years")
    assert loan_years.api_cell == "API_INPUT!B34"
    assert loan_years.default == 10
    assert loan_years.min == 1 and loan_years.max == 20 and loan_years.step == 1


def test_outputs_count():
    d = _dict()
    assert len(d.outputs()) == 34
    assert [(d.get(pid).api_cell, d.get(pid).dtype) for pid in [
        "repayment_method", "discount_rate", "energy_revenue_vat_rate", "ancillary_service_vat_rate",
        "capacity_compensation_vat_rate", "capacity_lease_vat_rate", "subsidy_vat_rate",
        "intervention_compensation_vat_rate", "income_tax_rate", "average_revenue",
    ]] == [
        ("API_OUTPUT!B24", "string"), ("API_OUTPUT!B25", "float"), ("API_OUTPUT!B26", "float"),
        ("API_OUTPUT!B27", "float"), ("API_OUTPUT!B28", "float"), ("API_OUTPUT!B29", "float"),
        ("API_OUTPUT!B30", "float"), ("API_OUTPUT!B31", "float"), ("API_OUTPUT!B32", "float"),
        ("API_OUTPUT!B33", "float"),
    ]
