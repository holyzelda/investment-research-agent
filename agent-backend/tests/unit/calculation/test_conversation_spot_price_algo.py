from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config.settings import ProvincePriceCoefficient
from app.core.exceptions import ValidationException
from app.modules.calculation.infrastructure.conversation_spot_price_algo import (
    ConversationSpotPriceAlgo,
)
from app.modules.calculation.domain.spot_pricing import day_optimal_by_k


def _context(*, price_mode="both", raw_prices=None):
    return SimpleNamespace(
        id="context-1",
        file_name="spot.xlsx",
        file_sha256="hash",
        valid_day_count=365,
        skipped_day_count=0,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        algorithm_version="spot-dp-v1",
        warnings=[],
        price_mode=price_mode,
        raw_prices=raw_prices,
        k_results={
            "8": {"chargeSum": "800", "dischargeSum": "4000", "slotCount": 8},
        },
    )


def test_reads_k_result_applies_province_coefficients_and_unit_conversion():
    algo = ConversationSpotPriceAlgo(
        _context(),
        {"甘肃": ProvincePriceCoefficient(charge=0.8, discharge=0.5)},
    )

    charge, discharge = algo.compute("甘肃", None, 200, 100, 1)

    assert charge == 0.08
    assert discharge == 0.25
    assert algo.source_metadata["source"] == "conversation_upload"


def test_rejects_k_outside_uploaded_business_set():
    with pytest.raises(ValidationException, match="K=12"):
        ConversationSpotPriceAlgo(_context(), {}).compute("甘肃", None, 300, 100, 1)


def _curve(low, high):
    return [Decimal(str(low if index < 48 else high)) for index in range(96)]


def _raw(curve):
    return {"2025-01-01": [str(value) for value in curve]}


def _raw_days(*curves):
    return {
        date(2025, 1, index + 1).isoformat(): [str(value) for value in curve]
        for index, curve in enumerate(curves)
    }


class _PublicRepository:
    def __init__(self, curve):
        self.curve = curve
        self.calls = []

    def fetch_daily_prices(self, area, mode, start, end):
        self.calls.append((area, mode, start, end))
        return {date(2025, 1, 1): self.curve}


def test_both_mode_uses_uploaded_curve_and_computes_only_requested_k():
    uploaded = _curve(100, 500)
    algo = ConversationSpotPriceAlgo(
        _context(raw_prices=_raw(uploaded)),
        {},
    )

    charge, discharge = algo.compute("甘肃", None, 200, 100, 1)
    expected_charge, expected_discharge, slots = day_optimal_by_k(
        uploaded, k_values=[8]
    )[8]

    assert charge == float(expected_charge / slots / 1000)
    assert discharge == float(expected_discharge / slots / 1000)
    assert algo.source_metadata["calculationDays"] == 1


def test_charge_only_mode_joins_uploaded_charge_with_province_curve_without_city():
    uploaded = _curve(100, 500)
    province = _curve(200, 800)
    repository = _PublicRepository(province)
    algo = ConversationSpotPriceAlgo(
        _context(price_mode="charge_only", raw_prices=_raw(uploaded)),
        {},
        province_repository=repository,
    )

    charge, discharge = algo.compute("甘肃", None, 200, 100, 1)
    expected_charge, expected_discharge, slots = day_optimal_by_k(
        uploaded, k_values=[8], discharge_prices=province
    )[8]

    assert charge == float(expected_charge / slots / 1000)
    assert discharge == float(expected_discharge / slots / 1000)
    assert repository.calls[0][0:2] == ("甘肃", "日前")


def test_discharge_only_henan_routes_public_charge_to_unified_settlement_point():
    uploaded = _curve(100, 500)
    public = _curve(200, 800)
    repository = _PublicRepository(public)
    algo = ConversationSpotPriceAlgo(
        _context(price_mode="discharge_only", raw_prices=_raw(uploaded)),
        {},
        henan_repository=repository,
    )

    charge, discharge = algo.compute("河南", None, 200, 100, 1, city="郑州")
    expected_charge, expected_discharge, slots = day_optimal_by_k(
        public, k_values=[8], discharge_prices=uploaded
    )[8]

    assert charge == float(expected_charge / slots / 1000)
    assert discharge == float(expected_discharge / slots / 1000)
    assert repository.calls[0][0:2] == ("河南", "统一结算点")


def test_single_side_henan_requires_city():
    with pytest.raises(ValidationException, match="必须提供城市"):
        ConversationSpotPriceAlgo(
            _context(price_mode="charge_only", raw_prices=_raw(_curve(100, 500))),
            {},
            henan_repository=_PublicRepository(_curve(200, 800)),
        ).compute("河南", None, 200, 100, 1)


def test_parallel_daily_calculation_matches_serial_result():
    first = _curve(100, 500)
    second = list(reversed(_curve(250, 700)))
    raw_prices = _raw_days(first, second)

    serial = ConversationSpotPriceAlgo(
        _context(raw_prices=raw_prices), {}, workers=1
    ).compute("甘肃", None, 200, 100, 1)
    parallel = ConversationSpotPriceAlgo(
        _context(raw_prices=raw_prices), {}, workers=2
    ).compute("甘肃", None, 200, 100, 1)

    assert parallel == serial
