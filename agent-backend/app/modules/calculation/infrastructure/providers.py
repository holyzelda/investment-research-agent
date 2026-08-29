"""calculation 基础设施 · 参数来源提供者。

- ConstMidLongPriceProvider：中长期均价常量（仅宁夏），从 mid_long_price_const.json 读
- NullSpotPriceAlgo：现货取数关闭时的空实现（返回 None，不连库）；开启时用 PrecomputeSpotPriceAlgo

（地区成本三项已改为模型输出，经 API_OUTPUT 读回，不再由本层提供。）
"""
from typing import Optional

from app.modules.calculation.domain.ports import (
    MidLongPriceProvider,
    SpotPriceAlgo,
)
from app.modules.calculation.infrastructure.data_loader import mid_long_const_raw


class ConstMidLongPriceProvider(MidLongPriceProvider):
    """从常量表按省取中长期充/放电均价（当前仅宁夏，其余 None）。"""

    def get_prices(self, province: str) -> tuple[Optional[float], Optional[float]]:
        row = mid_long_const_raw().get("provinces", {}).get(province)
        if row is None:
            return None, None
        return row.get("mid_long_charge_avg"), row.get("mid_long_discharge_avg")


class NullSpotPriceAlgo(SpotPriceAlgo):
    """现货取数关闭（spot_price.enabled=false）时的空实现：不算、不连库，返回 (None, None)。"""

    def compute(
        self, province: str, node_name, capacity_mwh: float, power_mw: float,
        daily_cycles: float, *, city: Optional[str] = None,
    ) -> tuple[Optional[float], Optional[float]]:
        return None, None
