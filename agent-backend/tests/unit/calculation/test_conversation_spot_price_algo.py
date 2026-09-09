from datetime import date
from types import SimpleNamespace

import pytest

from app.core.config.settings import ProvincePriceCoefficient
from app.core.exceptions import ValidationException
from app.modules.calculation.infrastructure.conversation_spot_price_algo import (
    ConversationSpotPriceAlgo,
)


def _context():
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
