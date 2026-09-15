"""会话上传曲线与公共原始曲线的联合现货电价计算。"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ValidationException
from app.modules.calculation.domain.ports import SpotPriceAlgo
from app.modules.calculation.domain.spot_pricing import day_optimal_by_k, k_from_inputs
from app.modules.calculation.infrastructure.henan_spot_import import city_to_region
from app.modules.calculation.infrastructure.spot_price_repo import (
    ProvinceSpotRepository,
    SpotDataError,
    UploadedNodeSpotRepository,
)

PRICE_MODES = {"both", "charge_only", "discharge_only"}


def _calculate_day(job: tuple[list[str], list[str], int, int, int]):
    """进程池 worker：只接收可直接序列化的原始值，避免携带 ORM 和仓储对象。"""
    charge_values, discharge_values, k, min_action_minutes, switch_gap_minutes = job
    charge_prices = [Decimal(value) for value in charge_values]
    discharge_prices = [Decimal(value) for value in discharge_values]
    result = day_optimal_by_k(
        charge_prices,
        k_values=[k],
        min_action_minutes=min_action_minutes,
        switch_gap_minutes=switch_gap_minutes,
        discharge_prices=discharge_prices,
    ).get(k)
    if result is None:
        return None
    charge_sum, discharge_sum, slot_count = result
    return str(charge_sum), str(discharge_sum), slot_count


def _province_source(province: str) -> tuple[str, str]:
    # 与公共预计算任务使用同一份映射，避免把蒙西、江苏等特殊 area 当成省名查询。
    from app.modules.calculation.infrastructure.spot_precompute import (
        PROVINCE_PRECOMPUTE_SPECS,
    )

    normalized = str(province or "").strip().removesuffix("省")
    for area, mode, configured_province in PROVINCE_PRECOMPUTE_SPECS:
        if configured_province == normalized:
            return area, mode
    raise ValidationException(f"省份“{province}”暂无可用的省级原始电价曲线")


def _raw_uploaded_prices(context) -> dict[date, list[Decimal]]:
    result = {}
    for day_text, values in (getattr(context, "raw_prices", None) or {}).items():
        try:
            day = date.fromisoformat(str(day_text))
            prices = [Decimal(str(value)) for value in values]
        except (ValueError, InvalidOperation, TypeError):
            continue
        if len(prices) == 96 and all(price.is_finite() for price in prices):
            result[day] = prices
    return result


class ConversationSpotPriceAlgo(SpotPriceAlgo):
    """固定上传来源；参数依赖变化时只计算当前项目对应的一个 K。"""

    def __init__(
        self,
        context,
        coefficients: dict,
        *,
        province_repository=None,
        henan_repository=None,
        min_action_minutes: int = 30,
        switch_gap_minutes: int = 15,
        workers: int = 1,
    ):
        self._context = context
        self._coefficients = coefficients or {}
        self._province_repository = province_repository
        self._henan_repository = henan_repository
        self._min_action_minutes = min_action_minutes
        self._switch_gap_minutes = switch_gap_minutes
        self._workers = max(1, int(workers))
        self._calculation_days = None
        self._runtime_warnings: list[str] = []

    @property
    def price_mode(self) -> str:
        mode = getattr(self._context, "price_mode", None) or "both"
        return mode if mode in PRICE_MODES else "both"

    @property
    def source_metadata(self) -> dict:
        context = self._context
        metadata = {
            "source": "conversation_upload",
            "contextId": context.id,
            "fileName": context.file_name,
            "fileHash": context.file_sha256,
            "priceMode": self.price_mode,
            "validDays": context.valid_day_count,
            "skippedDays": context.skipped_day_count,
            "startDate": context.start_date.isoformat(),
            "endDate": context.end_date.isoformat(),
            "algorithmVersion": context.algorithm_version,
        }
        if self._calculation_days is not None:
            metadata["calculationDays"] = self._calculation_days
        return metadata

    @property
    def source_warnings(self) -> list[str]:
        return [*(self._context.warnings or []), *self._runtime_warnings]

    def compute(
        self, province, node_name, capacity_mwh, power_mw, daily_cycles, *, city=None
    ):
        k = k_from_inputs(
            Decimal(str(capacity_mwh)),
            Decimal(str(power_mw)),
            Decimal(str(daily_cycles)),
        )
        uploaded = _raw_uploaded_prices(self._context)
        if not uploaded:
            return self._legacy_result(k, province)

        mode = self.price_mode
        if mode == "both":
            charge_days = discharge_days = uploaded
        else:
            public = self._public_prices(
                province,
                city,
                side="discharge" if mode == "charge_only" else "charge",
            )
            if mode == "charge_only":
                charge_days, discharge_days = uploaded, public
            else:
                charge_days, discharge_days = public, uploaded

        common_days = sorted(charge_days.keys() & discharge_days.keys())
        if not common_days:
            raise ValidationException(
                "上传电价与省级电价没有重叠的完整日期，无法进行联合计算"
            )
        omitted = len(uploaded) - len(common_days)
        self._calculation_days = len(common_days)
        self._runtime_warnings = []
        if omitted > 0:
            self._runtime_warnings.append(
                f"有{omitted}个上传电价有效日因省级曲线缺失未参与联合计算"
            )

        jobs = [
            (
                [str(value) for value in charge_days[business_date]],
                [str(value) for value in discharge_days[business_date]],
                k,
                self._min_action_minutes,
                self._switch_gap_minutes,
            )
            for business_date in common_days
        ]
        if self._workers > 1 and len(jobs) > 1:
            chunksize = max(1, len(jobs) // (self._workers * 4))
            with ProcessPoolExecutor(max_workers=self._workers) as executor:
                results = executor.map(_calculate_day, jobs, chunksize=chunksize)
                totals = list(results)
        else:
            totals = [_calculate_day(job) for job in jobs]

        charge_sum = Decimal(0)
        discharge_sum = Decimal(0)
        slot_count = 0
        for result in totals:
            if result is None:
                continue
            day_charge, day_discharge, day_slots = result
            charge_sum += Decimal(day_charge)
            discharge_sum += Decimal(day_discharge)
            slot_count += day_slots
        return self._averages(charge_sum, discharge_sum, slot_count, province)

    def _public_prices(self, province: str, city: str | None, *, side: str):
        start = self._context.start_date
        end = self._context.end_date + timedelta(days=1)
        try:
            normalized_province = str(province or "").strip().removesuffix("省")
            if normalized_province == "河南":
                if not city:
                    raise ValidationException("河南项目使用单边上传电价时必须提供城市")
                try:
                    region = city_to_region(city, strict=True)
                except ValueError as exc:
                    raise ValidationException(str(exc)) from exc
                repository = self._henan_repository or self._build_henan_repository()
                area, station = (
                    ("河南", "统一结算点") if side == "charge" else (region, region)
                )
                return repository.fetch_daily_prices(area, station, start, end)

            area, market_mode = _province_source(province)
            repository = self._province_repository or self._build_province_repository()
            return repository.fetch_daily_prices(area, market_mode, start, end)
        except SpotDataError as exc:
            raise ValidationException(f"无法读取用于联合计算的省级电价：{exc}") from exc

    @staticmethod
    def _build_province_repository():
        from app.core.config.settings import get_settings

        config = get_settings().spot_price
        if not config.province_dsn:
            raise ValidationException("省级原始电价数据源未配置")
        return ProvinceSpotRepository(
            config.province_dsn, config.province_table, config.province_market
        )

    @staticmethod
    def _build_henan_repository():
        from app.core.config.settings import get_settings

        settings = get_settings()
        return UploadedNodeSpotRepository(
            settings.database.url.replace("+aiomysql", "+pymysql"),
            price_type=settings.spot_price.node_price_type,
        )

    def _legacy_result(self, k: int, province: str):
        result = (self._context.k_results or {}).get(str(k))
        if result is None:
            raise ValidationException(
                f"当前项目参数对应的现货计算档位 K={k} 不受支持，请使用2小时或4小时系统"
            )
        return self._averages(
            Decimal(str(result["chargeSum"])),
            Decimal(str(result["dischargeSum"])),
            int(result.get("slotCount") or 0),
            province,
        )

    def _averages(self, charge_sum, discharge_sum, slots: int, province: str):
        if slots <= 0:
            return None, None
        normalized_province = str(province or "").strip().removesuffix("省")
        coefficient = self._coefficients.get(province) or self._coefficients.get(normalized_province)
        charge_factor = Decimal(str(coefficient.charge)) if coefficient else Decimal(1)
        discharge_factor = Decimal(str(coefficient.discharge)) if coefficient else Decimal(1)
        return (
            float(charge_sum / slots * charge_factor / 1000),
            float(discharge_sum / slots * discharge_factor / 1000),
        )
