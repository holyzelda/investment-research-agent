"""从会话上传上下文的 19 个 K 聚合结果读取现货均价。"""
from __future__ import annotations

from decimal import Decimal

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.ports import SpotPriceAlgo
from app.modules.calculation.domain.spot_pricing import k_from_inputs


class ConversationSpotPriceAlgo(SpotPriceAlgo):
    """会话自定义电价适配器；不访问公共预计算表。"""

    def __init__(self, context, coefficients: dict, *, force_compute: bool = True):
        self._context = context
        self._coefficients = coefficients or {}
        self.always_compute = force_compute

    @property
    def source_metadata(self) -> dict:
        context = self._context
        return {
            "source": "conversation_upload",
            "contextId": context.id,
            "fileName": context.file_name,
            "fileHash": context.file_sha256,
            "validDays": context.valid_day_count,
            "skippedDays": context.skipped_day_count,
            "startDate": context.start_date.isoformat(),
            "endDate": context.end_date.isoformat(),
            "algorithmVersion": context.algorithm_version,
        }

    @property
    def source_warnings(self) -> list[str]:
        return list(self._context.warnings or [])

    def compute(
        self, province, node_name, capacity_mwh, power_mw, daily_cycles, *, city=None
    ):
        k = k_from_inputs(
            Decimal(str(capacity_mwh)),
            Decimal(str(power_mw)),
            Decimal(str(daily_cycles)),
        )
        result = (self._context.k_results or {}).get(str(k))
        if result is None:
            raise ValidationException(
                f"当前项目参数对应的现货计算档位 K={k} 不受支持，请使用2小时或4小时系统"
            )
        slots = int(result.get("slotCount") or 0)
        if slots <= 0:
            return None, None
        avg_charge = Decimal(str(result["chargeSum"])) / slots
        avg_discharge = Decimal(str(result["dischargeSum"])) / slots
        coefficient = self._coefficients.get(province)
        charge_factor = Decimal(str(coefficient.charge)) if coefficient else Decimal(1)
        discharge_factor = Decimal(str(coefficient.discharge)) if coefficient else Decimal(1)
        return (
            float(avg_charge * charge_factor / 1000),
            float(avg_discharge * discharge_factor / 1000),
        )
