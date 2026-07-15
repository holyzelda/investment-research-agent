"""calculation 应用层 · 参数组装用例（PRD US-1.1 参数四来源组装）。

输入：最小项目信息（省份/容量/功率 + 可选节点/电压）
输出：AssembledParams —— 写入 API_INPUT 的 payload + 各省收益结构开关 + 组装告警

组装规则（PRD US-1.1 规则3/4）：
- ①对话抽取：功率/容量/省份/节点/电压
- ②系统默认：EPC/贷款/运维/达成率/年限/换电… （取字典 default）
- ③电价库二次计算：现货充/放均价（spot_algo）
- ④各省收益结构按省：开关(9) + 参与项下游明细（中长期/调频/干预 两档插值；租赁单价/达成率）
- ⑤中长期均价(常量表, 仅宁夏, 来源后端 json)：写入 API_INPUT
- F 列只管展示，不决定写入：收益结构开关 F=0 仍写入 API_INPUT
- 地区成本三项由模型『地区』sheet 按省算出，经 API_OUTPUT 读回，不在本组装器处理
"""
from dataclasses import dataclass, field
from typing import Optional

from app.modules.calculation.domain import services
from app.modules.calculation.domain.models import ProjectBasics, ProvinceRevenueProfile
from app.modules.calculation.domain.param_dictionary import ParamDictionary
from app.modules.calculation.domain.ports import (
    MidLongPriceProvider,
    RevenueStructureReader,
    SpotPriceAlgo,
)

# 各省收益结构开关 param_id -> ProvinceRevenueProfile 属性名
_SWITCH_MAP = {
    "switch_mid_long": "mid_long",
    "switch_spot": "spot",
    "switch_frequency": "frequency",
    "switch_capacity": "capacity",
    "switch_subsidy": "subsidy",
    "switch_lease": "lease",
    "switch_intervention": "intervention",
    "switch_collect_grid_fee": "collect_grid_fee",
    "switch_return_grid_fee": "return_grid_fee",
}


@dataclass
class AssembledParams:
    """组装结果。"""
    api_input: dict = field(default_factory=dict)          # 写入 API_INPUT（param_id -> 值）
    switches: dict = field(default_factory=dict)           # 各省收益结构开关（用于收益类显隐）
    warnings: list = field(default_factory=list)           # 组装告警（省份缺失/未知等）


class ParamAssembler:
    """参数组装器（依赖端口，便于单测注入 mock）。"""

    def __init__(
        self,
        param_dict: ParamDictionary,
        revenue_structure: RevenueStructureReader,
        mid_long: MidLongPriceProvider,
        spot: SpotPriceAlgo,
    ):
        self._dict = param_dict
        self._revenue = revenue_structure
        self._mid_long = mid_long
        self._spot = spot

    def assemble(self, basics: ProjectBasics) -> AssembledParams:
        result = AssembledParams()
        cap, pwr = basics.capacity_mwh, basics.power_mw

        # ① 对话抽取
        result.api_input["power_mw"] = pwr
        result.api_input["capacity_mwh"] = cap
        result.api_input["province"] = basics.province
        result.api_input["voltage_kv"] = basics.voltage_kv
        if basics.node_name:  # 用户没提节点则不写入、不展示
            result.api_input["node_name"] = basics.node_name

        # ② 系统默认值
        for pid, dv in self._dict.defaults().items():
            result.api_input[pid] = dv

        # ③ 电价库二次计算（现货充/放均价）
        daily_cycles = result.api_input.get("daily_cycles", 1)
        spot_c, spot_d = self._spot.compute(
            basics.province, basics.node_name, cap, pwr, daily_cycles)
        result.api_input["spot_charge_avg"] = spot_c
        result.api_input["spot_discharge_avg"] = spot_d

        # ④ 各省收益结构按省
        profile = self._revenue.get_profile(basics.province)
        if profile is None:
            result.warnings.append(f"省份[{basics.province}]不在《各省收益结构》，收益类明细暂缺")
        else:
            self._assemble_revenue_structure(result, profile, cap, pwr)

        # ⑤ 中长期充/放均价（常量表，仅宁夏有值，来源后端 json）→ 写入 API_INPUT
        ml_c, ml_d = self._mid_long.get_prices(basics.province)
        result.api_input["mid_long_charge_avg"] = ml_c
        result.api_input["mid_long_discharge_avg"] = ml_d

        # 地区成本三项（充电成本/放电返还/损耗）由模型『地区』sheet 按省算出，
        # 经 API_OUTPUT 读回展示，组装阶段不处理。

        return result

    def _assemble_revenue_structure(
        self, result: AssembledParams, profile: ProvinceRevenueProfile, cap: float, pwr: float
    ) -> None:
        # 开关（F=0 但仍写入 API_INPUT）
        for pid, attr in _SWITCH_MAP.items():
            val = getattr(profile, attr)
            result.switches[pid] = val
            result.api_input[pid] = val

        # 参与项下游明细（开关=1 才取）
        if profile.is_on("mid_long"):
            result.api_input["mid_long_energy_revenue_first_year_tax"] = \
                services.mid_long_first_year_revenue(profile.mid_long_tier, cap, pwr)
        if profile.is_on("frequency"):
            result.api_input["frequency_first_year_revenue"] = \
                services.frequency_first_year_revenue(profile.frequency_tier, cap, pwr)
        if profile.is_on("intervention"):
            result.api_input["intervention_first_year_revenue"] = \
                services.intervention_first_year_revenue(profile.intervention_tier, cap, pwr)
        if profile.is_on("lease"):
            result.api_input["lease_unit_price"] = profile.lease_unit_price
            rate = profile.lease_achievement_rate
            if rate is None:  # 各省收益结构缺则回落字典默认 0.9
                spec = self._dict.get("lease_achievement_rate")
                rate = spec.default if spec else None
            result.api_input["lease_achievement_rate"] = rate
