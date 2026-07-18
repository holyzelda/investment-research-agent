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

    def assemble(
        self,
        basics: ProjectBasics,
        *,
        overrides: Optional[dict] = None,
        previous_input: Optional[dict] = None,
    ) -> AssembledParams:
        """组装一次测算的完整入参。

        overrides：受控参数覆盖（Batch5 参数调整面板提交的当前值），仅接受参数字典中
            g=1 + direction=input + writable=true 的参数 id；其余键一律忽略，null 视为未覆盖。
        previous_input：上一版本冻结的 api_input（同会话重算时传入），用于现货电价依赖判断
            （PRD 2026-07-15 确认）：节点/容量/功率/日均充放电次数任一变化则重新查预计算表
            并忽略本次提交的旧现货电价；均未变化则不查库，继承上一版本价格对，再叠加本次
            用户对现货充/放电价的手工修改（单边/双边均可）。首次测算（previous_input=None）
            视为依赖必然"变化"，始终查库。
        """
        overrides = overrides or {}
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

        # 日均充放电次数：override 先生效（影响现货 K 的取值），暂不写回 api_input，
        # 交由末尾的受控覆盖统一写入，避免重复赋值。
        override_cycles = overrides.get("daily_cycles")
        daily_cycles = override_cycles if override_cycles is not None else result.api_input.get("daily_cycles", 1)

        # ③ 电价库二次计算（现货充/放均价）——依赖未变则继承上一版本，不查库
        deps_changed = self._spot_dependency_changed(previous_input, basics, daily_cycles)
        if not deps_changed:
            spot_c = previous_input.get("spot_charge_avg")
            spot_d = previous_input.get("spot_discharge_avg")
        else:
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

        # ⑥ 受控覆盖（末尾统一应用，覆盖默认值/查表结果/收益结构计算值）。
        # 依赖变化时，重新算出的值不应被面板提交的陈旧 override 覆盖回去：
        # - 现货依赖（节点/容量/功率/日循环）变化 → 忽略陈旧现货 override，用新查表值；
        # - 容量/功率变化 → 两档收益（中长期/调频/干预，按 t=容量/功率插值）已用新值重算，
        #   忽略陈旧的两档收益 override，避免旧数值把新算出的结果覆盖回去。
        ignore_keys = set()
        if deps_changed:
            ignore_keys |= {"spot_charge_avg", "spot_discharge_avg"}
        if self._capacity_power_changed(previous_input, basics):
            ignore_keys |= {
                "mid_long_energy_revenue_first_year_tax",
                "frequency_first_year_revenue",
                "intervention_first_year_revenue",
            }
        self._apply_overrides(result, overrides, ignore_keys)

        return result

    def _capacity_power_changed(self, previous_input: Optional[dict], basics: ProjectBasics) -> bool:
        """容量/功率相对上一版本是否变化（两档收益按 t=容量/功率插值，随之重算）。

        无上一版本基线（首次测算）视为必然变化，理由同 `_spot_dependency_changed`。
        """
        if previous_input is None:
            return True
        return (
            previous_input.get("capacity_mwh") != basics.capacity_mwh
            or previous_input.get("power_mw") != basics.power_mw
        )

    def _spot_dependency_changed(
        self, previous_input: Optional[dict], basics: ProjectBasics, daily_cycles: float,
    ) -> bool:
        """现货电价依赖【节点/容量/功率/日均充放电次数】相对上一版本是否发生变化。

        无上一版本基线（首次测算）视为必然变化。
        """
        if previous_input is None:
            return True
        return (
            previous_input.get("node_name") != basics.node_name
            or previous_input.get("capacity_mwh") != basics.capacity_mwh
            or previous_input.get("power_mw") != basics.power_mw
            or previous_input.get("daily_cycles") != daily_cycles
        )

    def _apply_overrides(self, result: AssembledParams, overrides: dict, ignore_keys: set) -> None:
        """受控覆盖：仅接受 g=1 + writable + direction=input 的白名单参数；null/未知键忽略。"""
        if not overrides:
            return
        writable_g1 = {s.id for s in self._dict.writable_inputs() if s.g == 1}
        for pid, value in overrides.items():
            if pid in ignore_keys or pid not in writable_g1 or value is None:
                continue
            result.api_input[pid] = value

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
