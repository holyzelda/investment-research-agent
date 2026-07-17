"""tie_line_map 领域 · 联络线值对象（无框架、无 I/O 依赖）。

只承载「跨省跨区联络线」的静态概念：线路名、起讫换流站、端点经纬度、
电压/容量/投运年份等。功率时序不在此表范围内（底表无时序字段），
故本值对象不含任何 MW 时序数据。
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TieLine:
    """一条跨省联络线的静态信息（对应 ir_tie_line_map 一行）。"""

    id: int
    name: str
    start_point: str
    end_point: str
    start_region: str
    end_region: str
    start_longitude: float
    start_latitude: float
    end_longitude: float
    end_latitude: float
    length_text: Optional[str] = None
    voltage_text: Optional[str] = None
    rated_capacity_mw: Optional[int] = None
    operation_year: Optional[int] = None
    coordinate_basis: Optional[str] = None
    data_basis_note: Optional[str] = None
    source_note: Optional[str] = None
