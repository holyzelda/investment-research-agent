"""calculation 领域 · 参数字典聚合。

封装 param_dict.json 的查询：按来源筛选、按写入方向筛选、取默认值等。
字典本身是数据契约（infrastructure/data/param_dict.json），本聚合提供领域语义访问。
"""
from dataclasses import dataclass
from typing import Optional

from app.modules.calculation.domain.models import Direction, ParamSource


@dataclass(frozen=True)
class ParamSpec:
    """单个参数的规格（param_dict.json.parameters 的一项）。"""
    id: str
    cn: str
    category: str
    source: str
    model_cell: Optional[str]
    f: int
    g: int
    writable: bool
    direction: str
    api_cell: Optional[str]
    default: object
    unit: str
    dtype: str
    zone: Optional[str] = None       # Batch5 调整区分区（仅调整区相关参数标注）
    control: Optional[str] = None    # slider | dynamic_slider | fixed（无则该参数不进调整区）
    min: Optional[float] = None      # control=slider 的滑块下限
    max: Optional[float] = None      # control=slider 的滑块上限
    step: Optional[float] = None     # control=slider/dynamic_slider 的滑块步长
    options: Optional[list[dict]] = None  # control=select 的枚举选项

    @classmethod
    def from_dict(cls, d: dict) -> "ParamSpec":
        return cls(
            id=d["id"], cn=d["cn"], category=d.get("category", ""),
            source=d["source"], model_cell=d.get("model_cell"),
            f=int(d.get("f", 0)), g=int(d.get("g", 0)),
            writable=bool(d.get("writable", False)),
            direction=d.get("direction", ""), api_cell=d.get("api_cell"),
            default=d.get("default"), unit=d.get("unit", ""), dtype=d.get("dtype", ""),
            zone=d.get("zone"), control=d.get("control"),
            min=d.get("min"), max=d.get("max"), step=d.get("step"),
            options=d.get("options"),
        )


class ParamDictionary:
    """参数字典聚合：以 ParamSpec 列表构造，提供查询。"""

    def __init__(self, specs: list[ParamSpec]):
        self._specs = specs
        self._by_id = {s.id: s for s in specs}

    @classmethod
    def from_raw(cls, raw: dict) -> "ParamDictionary":
        return cls([ParamSpec.from_dict(p) for p in raw.get("parameters", [])])

    def __len__(self) -> int:
        return len(self._specs)

    def all(self) -> list[ParamSpec]:
        return list(self._specs)

    def get(self, param_id: str) -> Optional[ParamSpec]:
        return self._by_id.get(param_id)

    def by_source(self, source: ParamSource) -> list[ParamSpec]:
        return [s for s in self._specs if s.source == source.value]

    def writable_inputs(self) -> list[ParamSpec]:
        """需写入 API_INPUT 的参数（writable=True 且 direction=input）。

        注意：F 列只管页面展示，不决定是否写入——表2开关 F=0 但仍写入。
        """
        return [s for s in self._specs if s.writable and s.direction == Direction.INPUT.value]

    def outputs(self) -> list[ParamSpec]:
        """读结果项（含财务/环形/折线 + 地区成本三项，方案A 均经 API_OUTPUT 读回）。"""
        return [s for s in self._specs if s.direction == Direction.OUTPUT.value]

    def displayable(self) -> list[ParamSpec]:
        """页面展示项（F=1）。"""
        return [s for s in self._specs if s.f == 1]

    def defaults(self) -> dict:
        """系统默认值映射（source=default 的 id→default）。"""
        return {s.id: s.default for s in self.by_source(ParamSource.DEFAULT)}
