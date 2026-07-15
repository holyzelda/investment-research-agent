"""calculation 应用层 · 结果视图映射（CalculationResult → 渲染就绪 dict）。

report_snapshot 的载荷即此形状：PRD 规定"历史展示数据源为 report_snapshot，可直接渲染"，
所以快照存的就是前端消费的 camelCase 三模块结构。放应用层，供 interface 序列化与
snapshot_service 落库共用（避免 application 依赖 interface）。
"""
from app.modules.calculation.domain.result import CalculationResult


def to_report_payload(r: CalculationResult) -> dict:
    b, f, adv = r.basic_info, r.financial, r.advanced
    d, li = adv.donut, adv.lines
    return {
        "version": r.version,
        "requestId": r.request_id,
        "warnings": r.warnings,
        "basicInfo": {
            "province": b.province,
            "nodeName": b.node_name,
            "capacityMwh": b.capacity_mwh,
            "powerMw": b.power_mw,
            "chargeCost": b.charge_cost,
            "dischargeReturn": b.discharge_return,
            "lossCost": b.loss_cost,
        },
        "financial": {
            "projectIrr": f.project_irr,
            "projectStaticPayback": f.project_static_payback,
            "capitalIrr": f.capital_irr,
            "capitalStaticPayback": f.capital_static_payback,
            "averageProfit": f.average_profit,
        },
        "advanced": {
            "donut": {
                "totalRevenue": d.total_revenue,
                "energyRevenue": d.energy_revenue,
                "capacityRevenue": d.capacity_revenue,
                "frequencyRevenue": d.frequency_revenue,
                "leaseRevenue": d.lease_revenue,
                "interventionRevenue": d.intervention_revenue,
                "subsidyRevenue": d.subsidy_revenue,
            },
            "lines": {
                "mainBusinessCost": li.main_business_cost,
                "currentPrincipalInterest": li.current_principal_interest,
                "capitalNetCashflow": li.capital_net_cashflow,
                "totalInvestNetCashflowAfterTax": li.total_invest_net_cashflow_after_tax,
            },
        },
    }
