from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundException
from app.modules.index_map.application.index_map_service import IndexMapService


@pytest.mark.asyncio
async def test_mock_overview_uses_excel_derived_summary_without_database_session():
    overview = await IndexMapService().get_overview(None, period="2026-07")

    # 10 区域算术均值：(93+92+88+86+80+88+84+73+71+66)/10
    assert overview.national_average == Decimal("82.1")
    assert len(overview.provinces) == 10
    assert overview.leader.province_name == "山西"
    assert overview.leader.index_score == 93
    assert [item.province_name for item in overview.investment_heat] == [
        "山西", "宁夏", "蒙西", "山东", "甘肃",
    ]
    # 同分（山东88、蒙西88）按 province_code 稳定排序：NMG < SD，蒙西在前。
    assert [item.rank for item in overview.investment_heat] == [1, 2, 3, 4, 5]
    assert overview.opened_grade_counts == {"S": 2, "A": 5, "B": 2, "C": 1}
    assert overview.opened_province_count == 10
    # “C 类区域”语义：按已开通的 C 类区域计数，与摘要第四张卡片一致。
    assert overview.high_potential_count == 1
    # 收益稳定榜按 annualized_return 降序取前 5，并携带分数供前端展示。
    assert [(item.province_name, item.annualized_return, item.rank) for item in overview.return_stability] == [
        ("宁夏", Decimal("98"), 1),
        ("山西", Decimal("87"), 2),
        ("甘肃", Decimal("85"), 3),
        ("蒙西", Decimal("82"), 4),
        ("山东", Decimal("80"), 5),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("province_code", "province_name", "score", "grade", "map_name"),
    [
        ("SD", "山东", 88, "A", "山东省"),
        ("GD", "广东", 84, "A", "广东省"),
        ("HI", "海南", 73, "B", "海南省"),
        ("HA", "河南", 71, "B", "河南省"),
        ("HE", "河北", 66, "C", "河北省"),
    ],
)
async def test_mock_added_provinces_score_grade_map_name(province_code, province_name, score, grade, map_name):
    detail = await IndexMapService().get_province_detail(None, period="2026-07", province_code=province_code)
    assert detail.summary.province_name == province_name
    assert detail.summary.index_score == score
    assert detail.summary.grade == grade
    assert detail.summary.map_name == map_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("score", "grade"),
    [(100, "S"), (90, "S"), (89, "A"), (80, "A"), (79, "B"), (70, "B"), (69, "C"), (60, "C")],
)
async def test_grade_bands_are_score_driven(score, grade):
    from app.modules.index_map.application.index_map_service import _grade_for_score

    assert _grade_for_score(Decimal(str(score))) == grade


@pytest.mark.asyncio
async def test_hebei_has_no_year_over_year_delta_labels():
    detail = await IndexMapService().get_province_detail(None, period="2026-07", province_code="HE")
    for item in detail.payload["installedStructure"]["items"]:
        assert item["deltaText"] is None


@pytest.mark.asyncio
async def test_hainan_keeps_maturity_but_omits_missing_contribution():
    detail = await IndexMapService().get_province_detail(None, period="2026-07", province_code="HI")
    # 三项成熟度评分保留，贡献度只有 Excel 给出的两项，不伪造缺失的容量补偿贡献。
    assert len(detail.payload["maturity"]["scores"]) == 3
    assert [c["label"] for c in detail.payload["factorContributions"]] == ["电能量市场", "调频市场"]


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
        ("SD", 47.25, 26.33, 73.67, 43.86, 4.76),
        ("GD", 30.57, 76.76, 23.24, 52.1, 5.15),
        ("HI", 50.1, 22.34, 77.66, 35.0, 6.31),
        ("HA", 51.66, 29.88, 70.12, 42.53, 2.04),
        ("HE", 75.8, 44.83, 48.88, 17.48, 3.94),
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
