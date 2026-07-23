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
    assert AI_SECTION_RULES[0]["maxWords"] == 100
    assert "IRR" in AI_SECTION_RULES[0]["forbiddenMetrics"]
    assert AI_SECTION_RULES[-1]["maxWords"] == 300
    assert AI_FALLBACK_TEXT == "本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。"
