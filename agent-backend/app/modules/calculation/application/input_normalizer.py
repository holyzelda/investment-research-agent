"""测算任务 HTTP 输入归一化；领域层只接收容量与功率。"""
from __future__ import annotations

import math
from typing import Optional

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.models import ProjectBasics

_DEFAULT_POWER_MW = 100.0
_SUPPORTED_DURATIONS = (2.0, 4.0)


def validate_supported_duration(capacity_mwh: float, power_mw: float) -> float:
    duration = capacity_mwh / power_mw
    if not any(
        math.isclose(duration, allowed, rel_tol=1e-9, abs_tol=1e-9)
        for allowed in _SUPPORTED_DURATIONS
    ):
        raise ValidationException("系统时长仅支持2小时或4小时")
    return duration


def normalize_project_basics(
    *,
    province: str,
    capacity_mwh: Optional[float],
    power_mw: Optional[float],
    duration_hours: Optional[float],
    node_name: Optional[str],
    voltage_kv: int,
    city: Optional[str] = None,
) -> ProjectBasics:
    """将容量、功率、时长的有效请求组合归一化为既有项目基础参数。"""
    if capacity_mwh is not None and power_mw is not None:
        if duration_hours is not None and not math.isclose(
            capacity_mwh,
            power_mw * duration_hours,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValidationException("项目容量、功率与时长不一致")
    elif power_mw is not None and duration_hours is not None:
        capacity_mwh = power_mw * duration_hours
    elif capacity_mwh is not None and duration_hours is not None:
        power_mw = capacity_mwh / duration_hours
    elif duration_hours is not None:
        power_mw = _DEFAULT_POWER_MW
        capacity_mwh = power_mw * duration_hours
    else:
        raise ValidationException("请同时提供项目容量和功率，或补充系统时长")

    validate_supported_duration(capacity_mwh, power_mw)
    return ProjectBasics(
        province=province,
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        node_name=node_name,
        voltage_kv=voltage_kv,
        city=city,
    )


def complete_scale_anchors(
    *,
    previous_input: Optional[dict],
    capacity_mwh: Optional[float],
    power_mw: Optional[float],
    duration_hours: Optional[float],
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """同会话修改参数时，用上一版冻结入参补全缺失的规模锚点。

    规则（决策点：单独改容量或功率时直接提取，未改的规模参数沿用上一版，时长派生）：
    - 只给功率 → 容量沿用上一版（改功率 = 改时长，容量保持不变）；
    - 只给容量 → 功率沿用上一版；
    - 只给时长 → 容量沿用上一版，功率由 normalize 按容量/时长推导；
    - 已给容量+功率（或容量/功率+时长）→ 原样返回，由 normalize 处理；
    - 均未给（只改了节点/高级参数）→ 容量、功率、时长全部沿用上一版。
    首次测算（previous_input=None）原样返回，由 normalize 的最小集合校验兜底。
    """
    if previous_input is None:
        return capacity_mwh, power_mw, duration_hours

    prev_cap = previous_input.get("capacity_mwh")
    prev_pwr = previous_input.get("power_mw")
    prev_dur = previous_input.get("duration_hours")

    # 请求已给 ≥2 个规模参数：组合已成立（容量+功率 / 容量+时长 / 功率+时长），
    # 原样返回由 normalize 处理，不得用上一版锚点覆盖用户显式给出的组合。
    given = sum(x is not None for x in (capacity_mwh, power_mw, duration_hours))
    if given >= 2:
        return capacity_mwh, power_mw, duration_hours

    if given == 0:
        # 本次未改任何规模参数：全部沿用上一版
        return prev_cap, prev_pwr, prev_dur

    # 只给了一个规模参数：补全缺失锚点（决策：改功率保容量、改容量保功率、只改时长保容量）
    if power_mw is not None:
        # 只改功率：容量沿用上一版（时长随功率派生）
        return prev_cap, power_mw, duration_hours
    if capacity_mwh is not None:
        # 只改容量：功率沿用上一版（时长随容量派生）
        return capacity_mwh, prev_pwr, duration_hours
    # 只改时长：容量沿用上一版，功率由 normalize 按容量/时长推导（保持容量不变）
    return prev_cap, None, duration_hours
