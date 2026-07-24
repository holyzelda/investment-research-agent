"""calculation 领域 · 测算结果契约（结果三模块，PRD US-1.2 规则3）。

这是前端结果区消费的稳定契约，与飞书内部结构无关：
飞书侧 API_OUTPUT 的 shape 由本系统方案A 规定，业务桥接公式来对齐。
故本 DTO 换真飞书网关时不变形。

三模块：
- ① BasicInfo 基本信息：省份/节点/容量/功率 + 充电成本/放电返还/损耗费用（地区表按省算，经 API_OUTPUT 读回）
- ② FinancialMetrics 财务指标：全投资IRR/全投资静态回收期/资本金IRR/资本金静态回收期/年均利润
- ③ AdvancedResult 进阶图形：首年总收入 + 环形图(6类首年收益) + 现金流口径下偿债倍数折线图
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BasicInfo:
    """① 基本信息及地区运营成本。"""
    province: str
    capacity_mwh: float
    power_mw: float
    node_name: Optional[str] = None          # 用户没提则 None，前端不显示
    charge_cost: Optional[float] = None       # 地区表 W，元/kWh（经 API_OUTPUT 读回）
    discharge_return: Optional[float] = None  # 地区表 X（经 API_OUTPUT 读回）
    loss_cost: Optional[float] = None         # 地区表 Y（经 API_OUTPUT 读回）
    transmission_price: Optional[float] = None
    line_loss_fee: Optional[float] = None
    system_operation_fee: Optional[float] = None
    government_fund_surcharge: Optional[float] = None


@dataclass(frozen=True)
class FinancialMetrics:
    """② 财务指标。"""
    project_irr: Optional[float] = None              # 项目全投资IRR %
    project_static_payback: Optional[float] = None   # 全投资静态回收期 年
    capital_irr: Optional[float] = None              # 资本金IRR %
    capital_static_payback: Optional[float] = None   # 资本金静态回收期 年
    average_profit: Optional[float] = None           # 年均利润 万元
    total_investment_roi: Optional[float] = None     # 总投资收益率 %


@dataclass(frozen=True)
class BoundaryParams:
    """测算边界中需随结果冻结展示的参数。"""
    equity_ratio: Optional[float] = None
    annual_operation_days: Optional[float] = None


@dataclass(frozen=True)
class RevenueDonut:
    """③-a 首年收入环形图（6 类 + 总收入）。"""
    total_revenue: Optional[float] = None            # 首年总收入 万元
    energy_revenue: Optional[float] = None           # 电能量
    capacity_revenue: Optional[float] = None         # 容量市场
    frequency_revenue: Optional[float] = None        # 调频市场
    lease_revenue: Optional[float] = None            # 租赁市场
    intervention_revenue: Optional[float] = None     # 干预补偿
    subsidy_revenue: Optional[float] = None          # 补贴


@dataclass(frozen=True)
class DebtServiceCoverage:
    """现金流口径下偿债倍数；元素对应第 1..N 年，None 表示断点。"""
    cashflow_ratio: list[float | None] = field(default_factory=list)


@dataclass(frozen=True)
class AdvancedResult:
    """③ 进阶图形结果。"""
    donut: RevenueDonut = field(default_factory=RevenueDonut)
    debt_service_coverage: DebtServiceCoverage = field(default_factory=DebtServiceCoverage)


@dataclass(frozen=True)
class CalculationResult:
    """测算结果（结果三模块 + 版本元）。"""
    basic_info: BasicInfo
    financial: FinancialMetrics
    advanced: AdvancedResult
    boundary: BoundaryParams = field(default_factory=BoundaryParams)
    version: Optional[str] = None       # V1/V2/V3…（Batch3 版本记录落地；薄片先占位）
    request_id: Optional[str] = None    # 本次测算标识（薄片占位）
    warnings: list = field(default_factory=list)
