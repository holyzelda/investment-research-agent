"""参数组装器 · 集成测试（真实 stub 数据源，覆盖 PRD US-1.1 场景）。"""
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
