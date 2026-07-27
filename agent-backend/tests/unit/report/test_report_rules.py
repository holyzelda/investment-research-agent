"""正式报告 AI 规则是版本化、稳定的模板契约。"""
from app.modules.report.application.report_rules import AI_FALLBACK_TEXT, AI_SECTION_RULES


def test_template_defines_the_five_frozen_ai_sections_without_irr_in_debt_analysis():
    assert [rule["key"] for rule in AI_SECTION_RULES] == [
        "debt_service_coverage",
        "operating_cashflow",
        "accounting_profit",
        "sensitivity",
        "investment_conclusion",
    ]
    debt, cashflow, profit = AI_SECTION_RULES[:3]
    assert debt["maxWords"] == 100
    assert "IRR" in debt["forbiddenMetrics"]
    assert "年度经营性现金流 ÷ 当年还本付息" in debt["prompt"]
    assert "还本、付息、经营性现金流、偿债后自由现金流" in cashflow["prompt"]
    assert "净利润与折旧摊销" in profit["prompt"]
    assert "非现金费用" in profit["prompt"]
    assert AI_SECTION_RULES[-1]["maxWords"] == 300
    assert AI_SECTION_RULES[-1]["title"] == "风险提示与后续动作"
    assert "风险提示与后续动作建议" in AI_SECTION_RULES[-1]["prompt"]
    assert "锁定EPC价格" in AI_SECTION_RULES[-1]["prompt"]
    assert AI_FALLBACK_TEXT == "本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。"
