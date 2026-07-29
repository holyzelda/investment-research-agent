from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundException
from app.modules.index_map.application.index_map_service import IndexMapService


@pytest.mark.asyncio
async def test_mock_overview_uses_excel_derived_summary_without_database_session():
    overview = await IndexMapService().get_overview(None, period="2026-07")

    assert overview.national_average == Decimal("89.2")
    assert overview.leader.province_name == "山西"
    assert overview.leader.index_score == 93
    assert [item.province_name for item in overview.investment_heat] == [
        "山西", "宁夏", "蒙西", "甘肃", "陕西",
    ]
    assert overview.opened_grade_counts == {"S": 2, "A": 3, "B": 0}
    assert overview.high_potential_count == 6


@pytest.mark.asyncio
async def test_mock_province_detail_returns_excel_derived_payload_and_validates_keys():
    detail = await IndexMapService().get_province_detail(None, period="2026-07", province_code="NMG")

    assert detail.summary.province_name == "蒙西"
    assert detail.payload["investmentAdvice"] == "优先布局·抢抓优质区域"
    assert detail.payload["maturity"]["scores"] == [
        {"key": "energy", "label": "电能量市场", "score": 60},
        {"key": "discharge", "label": "放电量补贴", "score": 40},
    ]
    assert detail.payload["installedStructure"]["totalGw"] == 168.87

    with pytest.raises(NotFoundException):
        await IndexMapService().get_overview(None, period="missing")
    with pytest.raises(NotFoundException):
        await IndexMapService().get_province_detail(None, period="2026-07", province_code="missing")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("province_code", "renewable", "wind", "solar", "thermal", "storage"),
    [
        ("SX", 48.01, 35.95, 62.81, 51.21, 2.04),
        ("NX", 65.44, 26.26, 73.74, 34.05, 11.12),
        ("NMG", 55.87, 53.49, 46.51, 33.75, 9.14),
        ("GS", 64.61, 51.06, 42.45, 27.43, 8.12),
        ("SN", 45.99, 29.24, 70.76, 49.33, 0.08),
    ],
)
async def test_mock_province_detail_uses_excel_installed_structure_shares(
    province_code, renewable, wind, solar, thermal, storage,
):
    detail = await IndexMapService().get_province_detail(
        None, period="2026-07", province_code=province_code,
    )
    items = {item["key"]: item for item in detail.payload["installedStructure"]["items"]}

    assert items["renewable"]["share"] == renewable
    assert items["renewable"]["windShare"] == wind
    assert items["renewable"]["solarShare"] == solar
    assert items["thermal"]["share"] == thermal
    assert items["storage"]["share"] == storage
