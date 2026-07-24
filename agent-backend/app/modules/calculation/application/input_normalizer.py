"""测算任务 HTTP 输入归一化；领域层只接收容量与功率。"""
from __future__ import annotations

import math
from typing import Optional

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.models import ProjectBasics

_DEFAULT_POWER_MW = 100.0


def normalize_project_basics(
    *,
    province: str,
    capacity_mwh: Optional[float],
    power_mw: Optional[float],
    duration_hours: Optional[float],
    node_name: Optional[str],
    voltage_kv: int,
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

    return ProjectBasics(
        province=province,
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        node_name=node_name,
        voltage_kv=voltage_kv,
    )
