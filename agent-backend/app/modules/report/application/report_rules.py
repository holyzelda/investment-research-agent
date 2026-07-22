"""正式报告内容规则。模板批注是唯一业务约束来源。"""

REPORT_SCHEMA_VERSION = 1
REPORT_STRUCTURE_VERSION = "v1.1"
AI_FALLBACK_TEXT = "本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。"
MISSING_DATA_TEXT = "需补充核实：____"

AI_SECTION_RULES = (
    {
        "key": "debt_service_coverage",
        "title": "现金流口径下偿债倍数分析",
        "maxWords": 100,
        "perspective": "偿债能力与投资可行性",
        "forbiddenMetrics": ["IRR", "全投资收益率", "资本金收益率"],
    },
    {
        "key": "operating_cashflow",
        "title": "经营性现金流覆盖能力分析",
        "maxWords": 100,
        "perspective": "项目偿债能力分析师",
        "forbiddenMetrics": ["IRR", "收益率"],
    },
    {
        "key": "accounting_profit",
        "title": "会计净利润分析",
        "maxWords": 150,
        "perspective": "财务报表",
        "forbiddenMetrics": ["IRR", "收益率"],
    },
    {
        "key": "sensitivity",
        "title": "压力情景偿债覆盖倍数分析",
        "maxWords": 150,
        "perspective": "现金流抗压能力",
        "forbiddenMetrics": ["IRR", "全投资收益率", "资本金收益率"],
    },
    {
        "key": "investment_conclusion",
        "title": "结论、风险提示与后续动作",
        "maxWords": 300,
        "perspective": "投决报告",
        "forbiddenMetrics": [],
    },
)
