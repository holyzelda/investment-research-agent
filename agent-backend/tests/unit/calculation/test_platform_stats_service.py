from unittest.mock import AsyncMock

import pytest

from app.modules.calculation.application.platform_stats_service import get_platform_stats


@pytest.mark.asyncio
async def test_adds_platform_usage_to_historical_baselines():
    session = AsyncMock()
    session.scalar.side_effect = [9, 3, 4]

    result = await get_platform_stats(session)

    assert result["calculationCount"] == 1295
    assert result["projectCount"] == 131
    assert result["reportCount"] == 260
    assert result["actual"] == {"calculationCount": 9, "projectCount": 3, "reportCount": 4}


@pytest.mark.asyncio
async def test_treats_empty_database_counts_as_zero():
    session = AsyncMock()
    session.scalar.side_effect = [None, None, None]

    result = await get_platform_stats(session)

    assert result["calculationCount"] == 1286
    assert result["projectCount"] == 128
    assert result["reportCount"] == 256
