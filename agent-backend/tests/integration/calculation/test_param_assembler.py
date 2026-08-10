"""参数组装器 · 集成测试（真实 stub 数据源，覆盖 PRD US-1.1 场景）。"""
import pytest

from app.core.exceptions import ValidationException
from app.modules.calculation.application.factory import build_param_assembler
from app.modules.calculation.domain.models import ProjectBasics


def _assemble(province, cap, pwr, node=None):
    asm = build_param_assembler()
    return asm.assemble(ProjectBasics(province=province, capacity_mwh=cap, power_mw=pwr, node_name=node))


class TestGansu:
    """PRD US-1.3 场景3：甘肃 中长期0/现货1/调频1/容量1，仅取现货+调频明细。"""

    def test_switches(self):
        r = _assemble("甘肃", 800, 200)
        assert r.switches["switch_spot"] == 1
        assert r.switches["switch_frequency"] == 1
        assert r.switches["switch_mid_long"] == 0

    def test_mid_long_not_taken_when_switch_off(self):
        r = _assemble("甘肃", 800, 200)
        # 中长期开关=0 → 不取明细
        assert "mid_long_energy_revenue_first_year_tax" not in r.api_input

    def test_frequency_taken_but_tier_empty_returns_none(self):
        # 甘肃调频开关=1，但表2两档为空 → 明细写入但值为 None
        r = _assemble("甘肃", 800, 200)
        assert "frequency_first_year_revenue" in r.api_input
        assert r.api_input["frequency_first_year_revenue"] is None

    def test_switches_written_to_api_input(self):
        """F=0 开关仍写入 API_INPUT。"""
        r = _assemble("甘肃", 800, 200)
        assert r.api_input["switch_spot"] == 1


class TestNingxia:
    """宁夏：全市场参与 + 两档齐全，明细应算出数值。"""

    def test_mid_long_computed(self):
        # 宁夏中长期240/480，t=800/200=4 → base=240+(480-240)*(4-2)/2=480；系数=800/(100*4)=2 → 960
        r = _assemble("宁夏", 800, 200)
        assert r.api_input["mid_long_energy_revenue_first_year_tax"] == 960.0

    def test_lease_taken(self):
        r = _assemble("宁夏", 800, 200)
        assert r.api_input["lease_unit_price"] == 20
        assert r.api_input["lease_achievement_rate"] == 0.9

    def test_intervention_computed(self):
        # 宁夏干预开关=1，两档330/540，t=4 → base=330+(540-330)*(4-2)/2=540；系数=800/(100*4)=2 → 1080
        r = _assemble("宁夏", 800, 200)
        assert r.switches["switch_intervention"] == 1
        assert r.api_input["intervention_first_year_revenue"] == 1080.0

    def test_mid_long_price_written_to_api_input(self):
        # 常量表宁夏占位为 null（数值待业务给），但键应写入 API_INPUT（来源后端 json）
        r = _assemble("宁夏", 800, 200)
        assert "mid_long_charge_avg" in r.api_input
        assert "mid_long_discharge_avg" in r.api_input


class TestCommon:
    def test_dialog_and_defaults(self):
        r = _assemble("甘肃", 800, 200, node="兰州东")
        assert r.api_input["power_mw"] == 200
        assert r.api_input["capacity_mwh"] == 800
        assert r.api_input["province"] == "甘肃"
        assert r.api_input["node_name"] == "兰州东"
        assert r.api_input["voltage_kv"] == 220
        assert r.api_input["epc_unit_price"] == 0.75  # 默认

    def test_node_omitted_when_absent(self):
        r = _assemble("甘肃", 800, 200)  # 无节点
        assert "node_name" not in r.api_input

    def test_spot_flows_from_injected_algo(self):
        # 组装器把注入的 spot 算法结果透传进 api_input；默认(未开启)为 None
        class _FakeSpot:
            def compute(self, province, node_name, capacity_mwh, power_mw, daily_cycles):
                return 0.05, 0.51
        asm = build_param_assembler(spot=_FakeSpot())
        r = asm.assemble(ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200))
        assert r.api_input["spot_charge_avg"] == 0.05
        assert r.api_input["spot_discharge_avg"] == 0.51

    def test_spot_none_when_disabled(self):
        # 测试环境 spot_price.enabled=false → NullSpotPriceAlgo → None
        r = _assemble("甘肃", 800, 200)
        assert r.api_input["spot_charge_avg"] is None
        assert r.api_input["spot_discharge_avg"] is None

    def test_unknown_province_warns(self):
        r = _assemble("火星省", 800, 200)
        assert any("火星省" in w for w in r.warnings)
        # 对话抽取与默认值仍应组装
        assert r.api_input["power_mw"] == 200
    def test_operation_years_override_is_frozen(self):
        asm = build_param_assembler()
        r = asm.assemble(
            ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200),
            overrides={"operation_years": 20},
        )
        assert r.api_input["operation_years"] == 20

    @pytest.mark.parametrize("value", [14, 16, 21, "20"])
    def test_invalid_non_null_operation_years_override_is_rejected(self, value):
        asm = build_param_assembler()
        with pytest.raises(ValidationException, match="项目运营期仅支持15年或20年"):
            asm.assemble(
                ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200),
                overrides={"operation_years": value},
            )

    def test_null_operation_years_override_is_ignored(self):
        asm = build_param_assembler()
        r = asm.assemble(
            ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200),
            overrides={"operation_years": None},
        )
        assert r.api_input["operation_years"] == 15


class _CountingSpot:
    """记录调用参数的假现货算法，供 override/依赖判断测试断言是否真的查了库。"""

    def __init__(self, charge=0.2, discharge=0.6):
        self.calls = []
        self._charge = charge
        self._discharge = discharge

    def compute(self, province, node_name, capacity_mwh, power_mw, daily_cycles):
        self.calls.append({
            "province": province, "node_name": node_name,
            "capacity_mwh": capacity_mwh, "power_mw": power_mw, "daily_cycles": daily_cycles,
        })
        return self._charge, self._discharge


class TestParamOverrides:
    """Batch5：受控 param_overrides + 现货依赖重查/继承（用户 2026-07-15 确认规则）。"""

    def _basics(self, node="祥泰站", cap=800, pwr=200):
        return ProjectBasics(province="甘肃", capacity_mwh=cap, power_mw=pwr, node_name=node)

    def test_first_calc_always_queries_spot_ignoring_any_override(self):
        """无上一版本基线（previous_input=None）时，始终查库；忽略任何现货 override（防御性）。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"spot_charge_avg": 9.9})
        assert len(spot.calls) == 1
        assert r.api_input["spot_charge_avg"] == 0.2  # 查库结果，非 override 的 9.9

    def test_dependencies_unchanged_no_override_inherits_previous_prices(self):
        """节点/容量/功率/日循环均未变，且本次未改电价 → 不查库，沿用上一版本价格对。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        r = asm.assemble(self._basics(), previous_input=previous)
        assert spot.calls == []
        assert r.api_input["spot_charge_avg"] == 0.22
        assert r.api_input["spot_discharge_avg"] == 0.61

    def test_dependencies_unchanged_single_side_override_keeps_other_inherited(self):
        """只改充电价：不查库；放电价继续沿用上一版本。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        r = asm.assemble(self._basics(), overrides={"spot_charge_avg": 0.30}, previous_input=previous)
        assert spot.calls == []
        assert r.api_input["spot_charge_avg"] == 0.30
        assert r.api_input["spot_discharge_avg"] == 0.61

    def test_third_version_inherits_second_versions_manual_price(self):
        """V3 相对 V2 依赖未变、V3 本身未再修改电价 → 继承 V2 的手工电价（而非 V1 的库查值）。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        v2_frozen = {  # V2 的冻结输入：用户在 V2 手工把充电价改成了 0.30
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.30, "spot_discharge_avg": 0.61,
        }
        r = asm.assemble(self._basics(), previous_input=v2_frozen)  # V3：无 override
        assert spot.calls == []
        assert r.api_input["spot_charge_avg"] == 0.30
        assert r.api_input["spot_discharge_avg"] == 0.61

    def test_node_change_requeries_and_ignores_stale_panel_price(self):
        """节点变化 → 依赖变化，重新查库并覆盖，忽略本次提交的旧电价 override。"""
        spot = _CountingSpot(charge=0.5, discharge=0.9)
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        r = asm.assemble(
            self._basics(node="新节点"),
            overrides={"spot_charge_avg": 0.22, "spot_discharge_avg": 0.61},  # 面板里的旧值
            previous_input=previous,
        )
        assert len(spot.calls) == 1
        assert spot.calls[0]["node_name"] == "新节点"
        assert r.api_input["spot_charge_avg"] == 0.5
        assert r.api_input["spot_discharge_avg"] == 0.9

    def test_capacity_change_requeries(self):
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        asm.assemble(self._basics(cap=400), previous_input=previous)
        assert len(spot.calls) == 1

    def test_power_change_requeries(self):
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        asm.assemble(self._basics(pwr=100), previous_input=previous)
        assert len(spot.calls) == 1

    def test_daily_cycles_override_changes_dependency_and_is_passed_to_spot_query(self):
        """日循环通过 override 修改 → 依赖变化，重新查库，且以 override 值参与查询。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200, "daily_cycles": 1,
            "spot_charge_avg": 0.22, "spot_discharge_avg": 0.61,
        }
        r = asm.assemble(self._basics(), overrides={"daily_cycles": 1.5}, previous_input=previous)
        assert len(spot.calls) == 1
        assert spot.calls[0]["daily_cycles"] == 1.5
        assert r.api_input["daily_cycles"] == 1.5

    def test_non_spot_override_applies_regardless_of_dependency_state(self):
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"epc_unit_price": 0.80, "loan_rate": 0.039})
        assert r.api_input["epc_unit_price"] == 0.80
        assert r.api_input["loan_rate"] == 0.039

    def test_province_cannot_be_overridden(self):
        """省份 g=0，不在受控白名单内；即便传入 override 也不生效。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"province": "宁夏"})
        assert r.api_input["province"] == "甘肃"

    def test_unknown_override_key_ignored(self):
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"not_a_real_param": 1})
        assert "not_a_real_param" not in r.api_input

    def test_output_only_param_cannot_be_overridden(self):
        """输出项（direction=output）不可写入，即便传了 override。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"project_irr": 99})
        assert "project_irr" not in r.api_input

    def test_null_override_treated_as_not_overridden(self):
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics(), overrides={"epc_unit_price": None})
        assert r.api_input["epc_unit_price"] == 0.75  # 默认值未被 null 覆盖

    def test_lease_override_applies_after_revenue_structure_computation(self):
        """宁夏租赁开关=1，正常算出 20；override 应覆盖计算结果，而非被计算结果覆盖回去。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(
            ProjectBasics(province="宁夏", capacity_mwh=800, power_mw=200),
            overrides={"lease_unit_price": 33.0},
        )
        assert r.api_input["lease_unit_price"] == 33.0

    def test_capacity_change_recomputes_two_tier_revenue_ignoring_stale_override(self):
        """容量变化 → 两档收益（中长期/调频/干预）按新 t 重算；面板提交的陈旧值必须被忽略。

        宁夏 800/200（t=4）中长期算出 960.0（既有集成测试锁定的数值）；容量改为 400（t=2）
        后应按新 t 重算为不同数值，即便本次仍提交了旧的 960.0 作为 override。
        """
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "province": "宁夏", "node_name": None, "capacity_mwh": 800, "power_mw": 200,
            "daily_cycles": 1, "spot_charge_avg": 0.2, "spot_discharge_avg": 0.6,
            "mid_long_energy_revenue_first_year_tax": 960.0,
        }
        r = asm.assemble(
            ProjectBasics(province="宁夏", capacity_mwh=400, power_mw=200),
            overrides={"mid_long_energy_revenue_first_year_tax": 960.0},  # 面板陈旧值
            previous_input=previous,
        )
        # t=800/200=4 时基准为 960.0；t=400/200=2 时应为按两档下限插值的另一数值，不等于 960.0
        assert r.api_input["mid_long_energy_revenue_first_year_tax"] != 960.0

    def test_capacity_unchanged_honors_two_tier_revenue_override(self):
        """容量/功率均未变化时，两档收益的手工 override 应正常生效（不被忽略）。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "province": "宁夏", "node_name": None, "capacity_mwh": 800, "power_mw": 200,
            "daily_cycles": 1, "spot_charge_avg": 0.2, "spot_discharge_avg": 0.6,
            "mid_long_energy_revenue_first_year_tax": 960.0,
        }
        r = asm.assemble(
            ProjectBasics(province="宁夏", capacity_mwh=800, power_mw=200),
            overrides={"mid_long_energy_revenue_first_year_tax": 1200.0},
            previous_input=previous,
        )
        assert r.api_input["mid_long_energy_revenue_first_year_tax"] == 1200.0


class TestModifyParameterSeeding:
    """对话"修改参数并重新测算"：同会话有上一版本冻结入参时，本次未提交的高级参数沿用上一版值。"""

    def _basics(self, cap=800, pwr=200, node="祥泰站"):
        return ProjectBasics(province="甘肃", capacity_mwh=cap, power_mw=pwr, node_name=node)

    def test_non_spot_params_inherit_previous_version_when_not_overridden(self):
        """V2 只改功率：未提及的 EPC/贷款等高级参数沿用 V1 冻结值，而非字典默认值。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        v1_frozen = {
            "province": "甘肃", "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200,
            "daily_cycles": 1, "spot_charge_avg": 0.2, "spot_discharge_avg": 0.6,
            "epc_unit_price": 0.85, "loan_rate": 0.042, "loan_years": 12,
            "maint_cost": 15.0, "opex_cost": 28.0, "strategy_achievement_rate": 0.9,
            "capacity_achievement_rate": 0.95, "lease_achievement_rate": 0.92,
            "battery_replace_cost": 60.0, "operation_years": 20,
        }
        r = asm.assemble(
            self._basics(pwr=300),  # 本次仅改功率
            previous_input=v1_frozen,
        )
        assert r.api_input["power_mw"] == 300
        assert r.api_input["capacity_mwh"] == 800
        # 未覆盖的高级参数沿用上一版冻结值
        assert r.api_input["epc_unit_price"] == 0.85
        assert r.api_input["loan_rate"] == 0.042
        assert r.api_input["loan_years"] == 12
        assert r.api_input["maint_cost"] == 15.0
        assert r.api_input["opex_cost"] == 28.0
        assert r.api_input["strategy_achievement_rate"] == 0.9
        assert r.api_input["capacity_achievement_rate"] == 0.95
        assert r.api_input["battery_replace_cost"] == 60.0
        assert r.api_input["operation_years"] == 20

    def test_explicit_override_still_wins_over_previous_seed(self):
        """本次显式提交的高级参数覆盖上一版冻结值（override 优先于种子）。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "province": "甘肃", "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200,
            "daily_cycles": 1, "spot_charge_avg": 0.2, "spot_discharge_avg": 0.6,
            "epc_unit_price": 0.85, "loan_rate": 0.042, "loan_years": 12,
        }
        r = asm.assemble(
            self._basics(),
            overrides={"epc_unit_price": 0.95, "loan_rate": 0.036},
            previous_input=previous,
        )
        assert r.api_input["epc_unit_price"] == 0.95
        assert r.api_input["loan_rate"] == 0.036
        # 未提交的参数仍沿用上一版
        assert r.api_input["loan_years"] == 12

    def test_no_previous_input_falls_back_to_dict_defaults(self):
        """首次测算（previous_input=None）行为不变：高级参数取字典默认值。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        r = asm.assemble(self._basics())
        assert r.api_input["epc_unit_price"] == 0.75  # 字典默认
        assert r.api_input["loan_rate"] == 0.04
        assert r.api_input["loan_years"] == 10

    def test_previous_seed_none_falls_back_to_dict_default(self):
        """上一版冻结入参缺某个参数时，回落到字典默认值。"""
        spot = _CountingSpot()
        asm = build_param_assembler(spot=spot)
        previous = {
            "province": "甘肃", "node_name": "祥泰站", "capacity_mwh": 800, "power_mw": 200,
            "daily_cycles": 1, "spot_charge_avg": 0.2, "spot_discharge_avg": 0.6,
            "epc_unit_price": 0.85,  # loan_rate 未出现在上一版
        }
        r = asm.assemble(self._basics(), previous_input=previous)
        assert r.api_input["epc_unit_price"] == 0.85
        assert r.api_input["loan_rate"] == 0.04  # 回落到字典默认


class TestBatteryReplaceCostByOperationYears:
    """换电成本随运营期（variants）：15年固定0 / 20年默认0.3、首切用默认、同档沿用、覆盖优先。"""

    def _basics(self, cap=800, pwr=200):
        return ProjectBasics(province="甘肃", capacity_mwh=cap, power_mw=pwr)

    def test_15_year_default_is_zero(self):
        """默认运营期（未传/15）换电成本恒为 0。"""
        r = build_param_assembler().assemble(self._basics())
        assert r.api_input["battery_replace_cost"] == 0

    def test_first_switch_to_20_uses_variant_default(self):
        """首次切到20年（无上一版）→ 用分档默认 0.3，不继承 15 年的 0。"""
        r = build_param_assembler().assemble(
            self._basics(), overrides={"operation_years": 20},
        )
        assert r.api_input["operation_years"] == 20
        assert r.api_input["battery_replace_cost"] == 0.3

    def test_switch_from_15_year_previous_uses_variant_default(self):
        """上一版是15年（换电0）→ 本次切到20年用默认 0.3，不继承上一版 0。"""
        previous = {
            "operation_years": 15, "battery_replace_cost": 0,
        }
        r = build_param_assembler().assemble(
            self._basics(), overrides={"operation_years": 20}, previous_input=previous,
        )
        assert r.api_input["battery_replace_cost"] == 0.3

    def test_20_to_20_inherits_previous_value(self):
        """上一版已是20年 → 未提交换电成本时沿用上一版值（用户值）。"""
        previous = {
            "operation_years": 20, "battery_replace_cost": 0.5,
        }
        r = build_param_assembler().assemble(
            self._basics(), overrides={"operation_years": 20}, previous_input=previous,
        )
        assert r.api_input["battery_replace_cost"] == 0.5

    def test_20_year_override_wins(self):
        """20年档用户显式提交换电成本 → 以用户值为准。"""
        r = build_param_assembler().assemble(
            self._basics(), overrides={"operation_years": 20, "battery_replace_cost": 0.6},
        )
        assert r.api_input["battery_replace_cost"] == 0.6

    def test_15_year_override_is_ignored_and_forced_to_zero(self):
        """15年档即便提交非0换电成本也被忽略，恒为 0（后端兜底，防中台/直接 API 绕过）。"""
        r = build_param_assembler().assemble(
            self._basics(), overrides={"battery_replace_cost": 0.6},
        )
        assert r.api_input["battery_replace_cost"] == 0

    def test_switch_back_to_15_forces_zero_discarding_previous(self):
        """20年用户值切回15年 → 强制归 0 并丢弃用户值。"""
        previous = {
            "operation_years": 20, "battery_replace_cost": 0.5,
        }
        r = build_param_assembler().assemble(
            self._basics(), overrides={"operation_years": 15}, previous_input=previous,
        )
        assert r.api_input["battery_replace_cost"] == 0

    def test_explicit_zero_battery_on_switch_to_20_is_honored(self):
        """用户显式要求换电成本保持 0 并切到 20 年 → 以用户值为准得到 0
        （override 里存在即视为用户提了值；中台侧由 ir_agent.yaml 保证切运营期时不搬运基线换电成本）。"""
        previous = {"operation_years": 15, "battery_replace_cost": 0}
        r = build_param_assembler().assemble(
            self._basics(),
            overrides={"operation_years": 20, "battery_replace_cost": 0},
            previous_input=previous,
        )
        assert r.api_input["operation_years"] == 20
        assert r.api_input["battery_replace_cost"] == 0

    def test_explicit_new_battery_value_while_switching_to_20_is_honored(self):
        """对话链路：切换运营期到20且用户显式给换电成本 0.6（≠上一版 0）→ 以用户值为准。"""
        previous = {"operation_years": 15, "battery_replace_cost": 0}
        r = build_param_assembler().assemble(
            self._basics(),
            overrides={"operation_years": 20, "battery_replace_cost": 0.6},
            previous_input=previous,
        )
        assert r.api_input["battery_replace_cost"] == 0.6

