"""calculation 领域 · 值对象与枚举（无框架、无 I/O 依赖）。

本模块只承载测算主链路的领域概念：
- ParamSource：参数来源（对应 param_dict.json 的 source 字段）
- ProjectBasics：最小项目输入（对话抽取三要素 + 可选节点/电压）
- ProvinceRevenueProfile：某省在表2《各省收益结构》的开关与两档收益基准
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ParamSource(str, Enum):
    """参数来源（与 param_dict.json.source 对齐）。"""
    DIALOG = "dialog"            # 对话抽取
    DEFAULT = "default"          # 系统默认值
    SPOT_ALGO = "spot_algo"      # 电价库二次计算（现货充放均价）
    REVENUE_STRUCTURE = "revenue_structure"  # 各省收益结构表（原代号"表2"）
    CONST_TABLE = "const_table"  # 常量表（中长期均价，仅宁夏）
    OUTPUT = "output"            # 读结果


class Direction(str, Enum):
    INPUT = "input"        # 写入 API_INPUT
    OUTPUT = "output"      # 读取 API_OUTPUT


# 表2开关取值：1=参与 / 0=不参与 / None=未知（空）
SwitchValue = Optional[int]


def duration_hours(capacity_mwh: float, power_mw: float) -> float:
    """项目时长 t = 容量/功率（MWh/MW = h）。两档收益插值的关键自变量。

    功率必须为正，否则时长无意义（守卫住裸 ZeroDivisionError）。
    """
    if power_mw <= 0:
        raise ValueError("功率必须为正，无法计算项目时长")
    return capacity_mwh / power_mw


@dataclass(frozen=True)
class ProjectBasics:
    """最小项目输入（PRD US-1.2：省份/容量/功率 三项必填）。"""
    province: str
    capacity_mwh: float
    power_mw: float
    node_name: Optional[str] = None
    voltage_kv: int = 220


@dataclass(frozen=True)
class TwoTier:
    """两档收益基准：100/200 档（t2）与 100/400 档（t4）。"""
    t2: Optional[float]
    t4: Optional[float]


@dataclass(frozen=True)
class ProvinceRevenueProfile:
    """某省在表2《各省收益结构》的一行：各市场开关 + 两档基准 + 租赁明细。"""
    province: str
    # 开关（1/0/None）
    mid_long: SwitchValue = None
    spot: SwitchValue = None
    frequency: SwitchValue = None
    capacity: SwitchValue = None
    subsidy: SwitchValue = None
    lease: SwitchValue = None
    intervention: SwitchValue = None
    collect_grid_fee: SwitchValue = None
    return_grid_fee: SwitchValue = None
    # 两档收益基准
    mid_long_tier: TwoTier = field(default_factory=lambda: TwoTier(None, None))
    frequency_tier: TwoTier = field(default_factory=lambda: TwoTier(None, None))
    intervention_tier: TwoTier = field(default_factory=lambda: TwoTier(None, None))
    # 租赁明细（L/M 列）
    lease_unit_price: Optional[float] = None
    lease_achievement_rate: Optional[float] = None

    def is_on(self, market: str) -> bool:
        """开关是否为参与（==1）。空/0 均视为不参与。"""
        return getattr(self, market, None) == 1
