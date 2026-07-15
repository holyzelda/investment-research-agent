"""calculation 领域 · 纯计算服务（无 I/O，TDD 主战场）。

两档收益插值公式，来源：表2《各省收益结构》r1 合并单元格描述（用户 2026-07-06 确认）。
记项目时长 t = 容量/功率（h）。两档基准：t2=100/200 档，t4=100/400 档。

- 中长期 D35（C1·D1 公式）：基准按 t 分段插值，× 容量系数
- 调频   D63（G1·H1 公式）：基准按 t 分段插值，× 功率系数（功率/100）
- 干预   D71（O1·P1 公式）：基准按 t 分段插值，× 容量系数（与中长期同型）

容量系数（中长期/干预共用）：
  t < 2 : 容量/200
  t ≥ 2 : 容量/(100*t)
"""
from typing import Optional

from app.modules.calculation.domain.models import TwoTier, duration_hours


def _tier_base_capacity_type(tier: TwoTier, t: float) -> Optional[float]:
    """中长期/干预型基准插值（C/D 或 O/P 两档）。

    t<2 : base = t2
    t>4 : base = t4 + (t4 - t2) * (t - 4) / 2
    2≤t≤4: base = t2 + (t4 - t2) * (t - 2) / 2
    """
    c, d = tier.t2, tier.t4
    if c is None or d is None:
        return None
    if t < 2:
        return float(c)
    if t > 4:
        return float(d) + (float(d) - float(c)) * (t - 4) / 2
    return float(c) + (float(d) - float(c)) * (t - 2) / 2


def _tier_base_power_type(tier: TwoTier, t: float) -> Optional[float]:
    """调频型基准插值（G/H 两档）。

    t<2 : base = t2 * (t / 2)
    t>4 : base = t4
    2≤t≤4: base = t2 + (t4 - t2) * (t - 2) / 2
    """
    g, h = tier.t2, tier.t4
    if g is None or h is None:
        return None
    if t < 2:
        return float(g) * (t / 2)
    if t > 4:
        return float(h)
    return float(g) + (float(h) - float(g)) * (t - 2) / 2


def _capacity_coefficient(capacity_mwh: float, t: float) -> float:
    """容量系数：t<2 → 容量/200；t≥2 → 容量/(100*t)。"""
    if t < 2:
        return capacity_mwh / 200
    return capacity_mwh / (100 * t)


def _capacity_type_first_year_revenue(
    tier: TwoTier, capacity_mwh: float, power_mw: float
) -> Optional[float]:
    """容量型首年收益（中长期/干预同型）= 基准(容量型两档插值) × 容量系数。"""
    t = duration_hours(capacity_mwh, power_mw)
    base = _tier_base_capacity_type(tier, t)
    if base is None:
        return None
    return base * _capacity_coefficient(capacity_mwh, t)


def mid_long_first_year_revenue(
    tier: TwoTier, capacity_mwh: float, power_mw: float
) -> Optional[float]:
    """中长期市场电能量交易收入（首年）D35 = 基准 × 容量系数。"""
    return _capacity_type_first_year_revenue(tier, capacity_mwh, power_mw)


def frequency_first_year_revenue(
    tier: TwoTier, capacity_mwh: float, power_mw: float
) -> Optional[float]:
    """首年调频收益 D63 = 基准 × 功率系数（功率/100）。"""
    t = duration_hours(capacity_mwh, power_mw)
    base = _tier_base_power_type(tier, t)
    if base is None:
        return None
    return base * (power_mw / 100)


def intervention_first_year_revenue(
    tier: TwoTier, capacity_mwh: float, power_mw: float
) -> Optional[float]:
    """首年干预补偿收益 D71 = 基准 × 容量系数（与中长期同型）。"""
    return _capacity_type_first_year_revenue(tier, capacity_mwh, power_mw)
