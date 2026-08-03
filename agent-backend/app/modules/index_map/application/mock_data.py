"""全国指数地图本地模拟数据。

数据由 my_projects/reference_files/全国投资指数.xlsx 整理，当前用于数据库表尚未投产时的页面联调。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.modules.index_map.domain.models import IndexPeriod, ProvinceIndexDetail, ProvinceIndexSummary

UPDATED_AT = datetime(2026, 7, 28, 10, 0, 0)
PERIOD = IndexPeriod(period="2026-07", label="2026年7月（模拟数据）", updated_at=UPDATED_AT)


def _summary(code: str, name: str, map_name: str, score: int, grade: str, rank: int, stability: int | None) -> ProvinceIndexSummary:
    return ProvinceIndexSummary(
        province_code=code,
        province_name=name,
        map_name=map_name,
        index_score=Decimal(str(score)),
        grade=grade,
        opened=True,
        rank=rank,
        # 新 Excel 未给新增省份收益稳定榜数值，缺失时保持 None，不伪造。
        annualized_return=Decimal(str(stability)) if stability is not None else None,
        updated_at=UPDATED_AT,
    )


PROVINCES = (
    # map_name 必须与前端 china.json 的省级 name 完全一致（全称），否则地图无法着色。
    _summary("SX", "山西", "山西省", 93, "S", 1, 87),
    _summary("NX", "宁夏", "宁夏回族自治区", 92, "S", 2, 98),
    _summary("NMG", "蒙西", "内蒙古自治区", 88, "A", 3, 82),
    _summary("GS", "甘肃", "甘肃省", 86, "A", 4, 85),
    _summary("SN", "陕西", "陕西省", 80, "A", 5, 75),
    # 新增区域来自 全国投资指数-1.xlsx；rank 由服务端按分数统一重排，这里给占位值。
    # 收益稳定榜分数：Excel 未提供的省份 stability 传 None；山东按最新口径给 80。
    _summary("SD", "山东", "山东省", 88, "A", 6, 80),
    _summary("GD", "广东", "广东省", 84, "A", 7, None),
    _summary("HI", "海南", "海南省", 73, "B", 8, None),
    _summary("HA", "河南", "河南省", 71, "B", 9, None),
    _summary("HE", "河北", "河北省", 66, "C", 10, None),
)


DETAIL_KEYS = {
    "电能量市场": "energy",
    "调频市场": "frequency",
    "干预补偿": "intervention",
    "容量补偿": "capacity",
    "容量租赁": "capacityLease",
    "放电量补贴": "discharge",
}

CAPACITY_KEYS = {
    "新能源": "renewable",
    "火电": "thermal",
    "储能": "storage",
}


def _format_delta(value: float | str | None) -> str | None:
    # 河北新 Excel 无“同比变化率”列，缺失时返回 None，前端据此不渲染同比标签，不伪造 0%。
    if value is None:
        return None
    if isinstance(value, str):
        return value
    percentage = abs(value) * 100
    digits = 0 if percentage >= 1 else 2
    formatted = f"{percentage:.{digits}f}".rstrip("0").rstrip(".")
    return f"{'↑' if value >= 0 else '↓'}{formatted}%"


def _detail(
    *, region: str, advice: str, maturity_summary: str, maturity_scores: list[tuple[str, int]],
    contributions: list[tuple[str, float]], total_gw: float,
    capacities: list[tuple[str, float, float, float | None, float | None, str, float | str | None]],
) -> dict:
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
                    "key": CAPACITY_KEYS[label], "label": label, "share": share,
                    "windShare": wind_share, "solarShare": solar_share,
                    "capacityGw": capacity_gw, "description": description, "deltaText": _format_delta(delta),
                }
                for label, share, capacity_gw, wind_share, solar_share, description, delta in capacities
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
        capacities=[("新能源", 48.01, 78.81, 35.95, 62.81, "", 0.3408), ("火电", 51.21, 84.05, None, None, "火电装机", 0.0017), ("储能", 2.04, 3.35, None, None, "新型储能", 0.1922)],
    ),
    "NX": _detail(
        region="宁夏", advice="强烈推荐·加速落地",
        maturity_summary="宁夏储能可双向参与中长期市场，通过跨周期价差套利；省内网架通畅，输电阻塞风险低。",
        maturity_scores=[("电能量市场", 54), ("调频市场", 30), ("干预补偿", 4), ("容量补偿", 10), ("容量租赁", 2)],
        contributions=[("电能量市场", 53.22), ("调频市场", 13.77), ("干预补偿", 8.69), ("容量补偿", 11.96), ("容量租赁", 12.36)], total_gw=91.13,
        capacities=[("新能源", 65.44, 59.64, 26.26, 73.74, "", 0.209), ("火电", 34.05, 31.03, None, None, "火电装机", 0.0444), ("储能", 11.12, 10.13, None, None, "新型储能", 0.7364)],
    ),
    "NMG": _detail(
        region="内蒙古·西部电网", advice="优先布局·抢抓优质区域",
        maturity_summary="国内独有独立电网，市场体系设有实时电能量市场并配套放电量补贴，有效增厚储能充放电价差收益。",
        maturity_scores=[("电能量市场", 60), ("放电量补贴", 40)],
        contributions=[("电能量市场", 29.02), ("放电量补贴", 70.98)], total_gw=168.87,
        capacities=[("新能源", 55.87, 94.35, 53.49, 46.51, "", 0.3791), ("火电", 33.75, 57, None, None, "火电装机", 0.0794), ("储能", 9.14, 15.43, None, None, "新型储能", 1.5283)],
    ),
    "GS": _detail(
        region="甘肃", advice="优先布局·稳步开发",
        maturity_summary="风光大基地配套储能需求旺盛，长期收益确定性强；调频收益核心取决于并网区位。",
        maturity_scores=[("电能量市场", 40), ("容量市场", 10), ("调频市场", 50)],
        contributions=[("电能量市场", 28.7), ("容量市场", 22.63), ("调频市场", 48.68)], total_gw=126.29,
        capacities=[("新能源", 64.61, 81.5985, 51.06, 42.45, "", 0.3112), ("火电", 27.43, 34.641, None, None, "火电装机", 0.2696), ("储能", 8.12, 10.26, None, None, "新型储能", 0.71)],
    ),
    "SN": _detail(
        region="陕西", advice="适度布局·择优筛选优质点位",
        maturity_summary="陕西储能现阶段现货、调频仅可二选一申报，短期收益承压；容量补偿政策已落地。",
        maturity_scores=[("电能量市场", 70), ("容量市场", 10), ("调频市场", 20)],
        contributions=[("电能量市场", 73.48), ("容量市场", 15), ("调频市场", 11.52)], total_gw=128.8514,
        capacities=[("新能源", 45.99, 59.26, 29.24, 70.76, "", 0.2866), ("火电", 49.33, 63.56, None, None, "火电装机", -0.0034), ("储能", 0.08, 0.098, None, None, "新增装机 0.098GW", "新增")],
    ),
    "SD": _detail(
        region="山东", advice="稳步推进·推荐布局",
        maturity_summary="山东独立储能政策框架完备，可同步参与电能量、调频辅助服务市场，并叠加容量补偿收益，多元盈利路径清晰可落地。",
        maturity_scores=[("电能量市场", 70), ("调频市场", 15), ("容量补偿", 15)],
        contributions=[("电能量市场", 65.05), ("调频市场", 16.51), ("容量补偿", 18.44)], total_gw=273.16,
        capacities=[("新能源", 47.25, 129.07, 26.33, 73.67, "", 0.048412), ("火电", 43.86, 119.82, None, None, "火电装机", -0.025854), ("储能", 4.76, 13, None, None, "新型储能", 0.160714)],
    ),
    "GD": _detail(
        region="广东", advice="择优布局落地",
        maturity_summary="广东独立储能电能量、调频市场收益贡献均衡，但调频赛道资源高度集中，头部电站瓜分大部分调节收益。",
        maturity_scores=[("电能量市场", 48), ("调频市场", 50), ("容量租赁", 2)],
        contributions=[("电能量市场", 46.72), ("调频市场", 50.92), ("容量租赁", 2.37)], total_gw=260.78,
        capacities=[("新能源", 30.57, 79.73, 76.76, 23.24, "", 0.616225), ("火电", 52.1, 135.87, None, None, "火电装机", 3.573146), ("储能", 5.15, 13.43, None, None, "新型储能", 0.479075)],
    ),
    "HI": _detail(
        region="海南", advice="收益分化明显",
        maturity_summary="海南暂未落地储能容量补偿机制，全部盈利依托节点价差套利，优质并网节点资源稀缺，市场拿点竞争白热化。",
        maturity_scores=[("电能量市场", 90), ("调频市场", 10), ("容量补偿", 15)],
        # 新 Excel 仅给出电能量市场、调频市场两项因子贡献度，缺失的容量补偿贡献不伪造。
        contributions=[("电能量市场", 85.49), ("调频市场", 14.51)], total_gw=25.37,
        capacities=[("新能源", 50.1, 12.71, 22.34, 77.66, "", 0.116872), ("火电", 35.0, 8.88, None, None, "火电装机", 0.076364), ("储能", 6.31, 1.6, None, None, "新型储能", 0.428571)],
    ),
    "HA": _detail(
        region="河南", advice="持续跟踪观望",
        maturity_summary="河南独立储能尚处发展初期，当前盈利路径单一；调频辅助服务、容量补偿机制预计年内落地，多元收益体系仍待验证。",
        maturity_scores=[("电能量市场", 85), ("容量租赁", 2), ("容量补偿", 13)],
        contributions=[("电能量市场", 59.1), ("容量租赁", 4.59), ("容量补偿", 36.31)], total_gw=174.6,
        capacities=[("新能源", 51.66, 90.19, 29.88, 70.12, "", 0.181116), ("火电", 42.53, 74.25, None, None, "火电装机", -0.006423), ("储能", 2.04, 3.57, None, None, "新型储能", 0.302920)],
    ),
    "HE": _detail(
        region="河北(冀北)", advice="项目审慎·跟踪观察",
        maturity_summary="冀北储能6月后中长期签约通道关闭；年度容量补偿标准100元·kW/年，当前依托表后结算模式维持基础收益，后续现货市场落地将冲击现有盈利逻辑。",
        maturity_scores=[("电能量市场", 30), ("容量补偿", 70)],
        contributions=[("电能量市场", 63.56), ("容量补偿", 36.44)], total_gw=107.75,
        # 河北新 Excel 无“同比变化率”列，delta 传 None，前端不渲染同比标签。
        capacities=[("新能源", 75.8, 81.67, 44.83, 48.88, "", None), ("火电", 17.48, 18.84, None, None, "火电装机", None), ("储能", 3.94, 4.25, None, None, "新型储能", None)],
    ),
}

DETAILS = {item.province_code: ProvinceIndexDetail(summary=item, payload=DETAIL_PAYLOADS[item.province_code]) for item in PROVINCES}
