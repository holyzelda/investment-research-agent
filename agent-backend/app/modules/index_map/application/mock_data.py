"""全国指数地图本地模拟数据。

数据由 my_projects/reference_files/全国投资指数.xlsx 整理，当前用于数据库表尚未投产时的页面联调。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.modules.index_map.domain.models import IndexPeriod, ProvinceIndexDetail, ProvinceIndexSummary

UPDATED_AT = datetime(2026, 7, 28, 10, 0, 0)
PERIOD = IndexPeriod(period="2026-07", label="2026年7月（模拟数据）", updated_at=UPDATED_AT)


def _summary(code: str, name: str, map_name: str, score: int, grade: str, rank: int, stability: int) -> ProvinceIndexSummary:
    return ProvinceIndexSummary(
        province_code=code,
        province_name=name,
        map_name=map_name,
        index_score=Decimal(str(score)),
        grade=grade,
        opened=True,
        rank=rank,
        annualized_return=Decimal(str(stability)),
        updated_at=UPDATED_AT,
    )


PROVINCES = (
    # map_name 必须与前端 china.json 的省级 name 完全一致（全称），否则地图无法着色。
    _summary("SX", "山西", "山西省", 93, "S", 1, 87),
    _summary("NX", "宁夏", "宁夏回族自治区", 92, "S", 2, 98),
    _summary("NMG", "蒙西", "内蒙古自治区", 88, "A", 3, 80),
    _summary("GS", "甘肃", "甘肃省", 86, "A", 4, 85),
    _summary("SN", "陕西", "陕西省", 80, "A", 5, 75),
)


DETAIL_KEYS = {
    "电能量市场": "energy",
    "调频市场": "frequency",
    "干预补偿": "intervention",
    "容量补偿": "capacity",
    "容量租赁": "capacityLease",
    "放电量补贴": "discharge",
}


def _detail(
    *, region: str, advice: str, maturity_summary: str, maturity_scores: list[tuple[str, int]],
    contributions: list[tuple[str, float]], total_gw: float, capacities: list[tuple[str, float, str]],
) -> dict:
    total = sum(value for _, value, _ in capacities)
    return {
        "regionDescription": region,
        "investmentAdvice": advice,
        "maturity": {
            "grade": "A",
            "summary": maturity_summary,
            "scores": [{"key": DETAIL_KEYS.get(label, f"item{index}"), "label": label, "score": score} for index, (label, score) in enumerate(maturity_scores, 1)],
        },
        "factorContributions": [
            {"key": DETAIL_KEYS.get(label, f"item{index}"), "label": label, "value": value, "delta": value}
            for index, (label, value) in enumerate(contributions, 1)
        ],
        "installedStructure": {
            "totalGw": total_gw,
            "items": [
                {
                    "key": f"item{index}", "label": label, "share": round(value / total * 100, 2) if total else 0,
                    "capacityGw": value, "description": description, "deltaText": "—",
                }
                for index, (label, value, description) in enumerate(capacities, 1)
            ],
        },
        "analysisText": maturity_summary,
    }


DETAIL_PAYLOADS = {
    "SX": _detail(
        region="山西", advice="强烈推荐·立即布局",
        maturity_summary="全国唯一落地一次调频商业化省份，现货市场起步早、运行成熟。储能可通过现货价差套利，叠加一次/二次调频增收。",
        maturity_scores=[("电能量市场", 50), ("调频市场", 50)],
        contributions=[("电能量市场", 47.08), ("调频市场", 52.92)], total_gw=164.14,
        capacities=[("新能源", 78.81, "风电 28.33 · 光伏 49.50"), ("火电", 84.05, "火电装机"), ("储能", 3.35, "新型储能")],
    ),
    "NX": _detail(
        region="宁夏", advice="强烈推荐·加速落地",
        maturity_summary="宁夏储能可双向参与中长期市场，通过跨周期价差套利；省内网架通畅，输电阻塞风险低。",
        maturity_scores=[("电能量市场", 54), ("调频市场", 30), ("干预补偿", 4), ("容量补偿", 10), ("容量租赁", 2)],
        contributions=[("电能量市场", 53.22), ("调频市场", 13.77), ("干预补偿", 8.69), ("容量补偿", 11.96), ("容量租赁", 12.36)], total_gw=91.13,
        capacities=[("新能源", 59.64, "风电 15.66 · 光伏 43.98"), ("火电", 31.03, "火电装机"), ("储能", 10.13, "新型储能")],
    ),
    "NMG": _detail(
        region="内蒙古·西部电网", advice="优先布局·抢抓优质区域",
        maturity_summary="国内独有独立电网，市场体系设有实时电能量市场并配套放电量补贴，有效增厚储能充放电价差收益。",
        maturity_scores=[("电能量市场", 60), ("放电量补贴", 40)],
        contributions=[("电能量市场", 29.02), ("放电量补贴", 70.98)], total_gw=168.87,
        capacities=[("新能源", 94.35, "风电 50.47 · 光伏 43.88"), ("火电", 57, "火电装机"), ("储能", 15.43, "新型储能")],
    ),
    "GS": _detail(
        region="甘肃", advice="优先布局·稳步开发",
        maturity_summary="风光大基地配套储能需求旺盛，长期收益确定性强；调频收益核心取决于并网区位。",
        maturity_scores=[("电能量市场", 40), ("容量市场", 10), ("调频市场", 50)],
        contributions=[("电能量市场", 28.7), ("容量市场", 22.63), ("调频市场", 48.68)], total_gw=126.29,
        capacities=[("新能源", 81.60, "风电 41.67 · 光伏 39.93"), ("火电", 34.64, "火电装机"), ("储能", 10.26, "新型储能")],
    ),
    "SN": _detail(
        region="陕西", advice="适度布局·择优筛选优质点位",
        maturity_summary="陕西储能现阶段现货、调频仅可二选一申报，短期收益承压；容量补偿政策已落地。",
        maturity_scores=[("电能量市场", 70), ("容量市场", 10), ("调频市场", 20)],
        contributions=[("电能量市场", 73.48), ("容量市场", 15), ("调频市场", 11.52)], total_gw=128.85,
        capacities=[("新能源", 59.26, "风电 17.33 · 光伏 41.93"), ("火电", 63.56, "火电装机"), ("储能", 0.098, "新增装机 0.098GW")],
    ),
}

DETAILS = {item.province_code: ProvinceIndexDetail(summary=item, payload=DETAIL_PAYLOADS[item.province_code]) for item in PROVINCES}
