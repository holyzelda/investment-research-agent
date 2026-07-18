"""calculation 基础设施 · 飞书样例输出（薄片 Mock 数据源）。

一份符合输出契约 shape 的假结果，供无飞书环境下端到端跑通主链路、
前端满保真开发结果三模块。数值为演示占位，非真实测算。

Batch3 接真飞书后，本样例仅用于测试；生产走 HttpFeishuGateway 真读。
"""

SAMPLE_API_OUTPUT: dict = {
    # ② 财务指标
    "project_irr": 8.5,
    "project_static_payback": 9.2,
    "capital_irr": 12.3,
    "capital_static_payback": 7.1,
    "average_profit": 3200.0,
    # ③-a 首年收入（环形图）
    "first_year_total_revenue": 8600.0,
    "first_year_energy_revenue": 5200.0,
    "first_year_capacity_revenue": 1800.0,
    "first_year_frequency_revenue": 900.0,
    "first_year_lease_revenue": 400.0,
    "first_year_intervention_revenue": 200.0,
    "first_year_subsidy_revenue": 100.0,
    # ③-b 现金流口径下偿债倍数（贷款期序列）
    "cashflow_debt_service_coverage_ratio": [1.12, 1.24, 0.0, None, 1.36, 1.48],
}


def sample_output() -> dict:
    """返回样例输出的副本。"""
    import copy
    return copy.deepcopy(SAMPLE_API_OUTPUT)
