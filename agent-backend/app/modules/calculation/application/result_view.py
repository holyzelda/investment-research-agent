"""calculation 应用层 · 结果视图映射（CalculationResult → 渲染就绪 dict）。

report_snapshot 的载荷即此形状：PRD 规定"历史展示数据源为 report_snapshot，可直接渲染"，
所以快照存的就是前端消费的 camelCase 三模块结构。放应用层，供 interface 序列化与
snapshot_service 落库共用（避免 application 依赖 interface）。
"""
from app.modules.calculation.domain.result import CalculationResult


def to_report_payload(r: CalculationResult) -> dict:
    b, f, adv = r.basic_info, r.financial, r.advanced
    d, coverage = adv.donut, adv.debt_service_coverage
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
            "transmissionPrice": b.transmission_price,
            "lineLossFee": b.line_loss_fee,
            "systemOperationFee": b.system_operation_fee,
            "governmentFundSurcharge": b.government_fund_surcharge,
        },
        "financial": {
            "projectIrr": f.project_irr,
            "projectStaticPayback": f.project_static_payback,
            "capitalIrr": f.capital_irr,
            "capitalStaticPayback": f.capital_static_payback,
            "averageProfit": f.average_profit,
            "averageRevenue": f.average_revenue,
            "totalInvestmentRoi": f.total_investment_roi,
        },
        "boundary": {
            "equityRatio": r.boundary.equity_ratio,
            "annualOperationDays": r.boundary.annual_operation_days,
            "repaymentMethod": r.boundary.repayment_method,
            "discountRate": r.boundary.discount_rate,
            "energyRevenueVatRate": r.boundary.energy_revenue_vat_rate,
            "ancillaryServiceVatRate": r.boundary.ancillary_service_vat_rate,
            "capacityCompensationVatRate": r.boundary.capacity_compensation_vat_rate,
            "capacityLeaseVatRate": r.boundary.capacity_lease_vat_rate,
            "subsidyVatRate": r.boundary.subsidy_vat_rate,
            "interventionCompensationVatRate": r.boundary.intervention_compensation_vat_rate,
            "incomeTaxRate": r.boundary.income_tax_rate,
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
            "debtServiceCoverage": {
                "cashflowRatio": coverage.cashflow_ratio,
            },
        },
    }
