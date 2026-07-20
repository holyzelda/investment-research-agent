"""calculation 应用层 · 组合根（默认 stub 实现装配）。

生产切换：Batch3 将 revenue_structure/spot/feishu 替换为飞书/真实算法实现，
本工厂是唯一装配点，application/domain 无需改动。
"""
from app.modules.calculation.application.calculation_service import CalculationService
from app.modules.calculation.application.feishu_calc_engine import (
    FeishuCalcEngine,
    SnapshotHook,
)
from app.modules.calculation.application.param_assembler import ParamAssembler
from app.modules.calculation.infrastructure.feishu_client import MockFeishuGateway
from app.modules.calculation.infrastructure.feishu_sample import sample_output
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository
from app.modules.calculation.infrastructure.providers import (
    ConstMidLongPriceProvider,
    NullSpotPriceAlgo,
)
from app.modules.calculation.infrastructure.revenue_structure_reader import (
    FeishuRevenueStructureReader,
    JsonRevenueStructureReader,
)


def build_revenue_structure_reader():
    """装配表2《各省收益结构》读取器（feishu.enabled 且已配置 token → 飞书真读，否则本地 json）。

    独立导出：`build_param_assembler` 与 `GET /ir/calc/param-dict?province=` 共用同一装配逻辑。
    """
    from app.core.config.settings import get_settings

    s = get_settings()
    if s.feishu.enabled and s.feishu.revenue_structure_token:
        return FeishuRevenueStructureReader(config=s.feishu)
    return JsonRevenueStructureReader()


def build_param_assembler(spot=None) -> ParamAssembler:
    """装配参数组装器。表2《各省收益结构》读取源按配置切换：

    feishu.enabled 且 revenue_structure_token 已填 → 飞书真读（FeishuRevenueStructureReader）；
    否则回退本地 json（JsonRevenueStructureReader）。
    现货：spot_price.enabled → 查预计算表（PrecomputeSpotPriceAlgo），否则 NullSpotPriceAlgo（返回 None）。
    中长期均价仍为常量表。spot 参数用于测试注入假实现（不走库）。
    """
    from app.core.config.settings import get_settings

    s = get_settings()
    revenue = build_revenue_structure_reader()
    if spot is None:
        if s.spot_price.enabled:
            from app.modules.calculation.infrastructure.spot_price_algo import PrecomputeSpotPriceAlgo
            spot = PrecomputeSpotPriceAlgo(
                coefficients=s.spot_price.province_price_coefficients,
                ir_dsn=s.database.url.replace("+aiomysql", "+pymysql"),
            )
        else:
            spot = NullSpotPriceAlgo()
    return ParamAssembler(
        param_dict=JsonParamDictRepository().load(),
        revenue_structure=revenue,
        mid_long=ConstMidLongPriceProvider(),
        spot=spot,
    )


def build_calculation_service() -> CalculationService:
    """薄片 Mock 主链路：飞书网关回放样例 output（不依赖真飞书）。

    Batch3 将 MockFeishuGateway 替换为 HttpFeishuGateway，此处是唯一装配点。
    """
    return CalculationService(
        assembler=build_param_assembler(),
        feishu=MockFeishuGateway(output=sample_output()),
    )


def build_calc_engine(
    gateway=None,
    snapshot_hook: SnapshotHook | None = None,
) -> FeishuCalcEngine:
    """测算执行引擎（状态机）。轮询间隔/超时读 settings.calc（Nacos 可配）。

    gateway 默认 MockFeishuGateway（回放样例 output、read_meta 立即 done）；
    Batch3 接真飞书时换 HttpFeishuGateway，此处是唯一装配点。
    """
    from app.core.config.settings import get_settings

    s = get_settings()
    return FeishuCalcEngine(
        gateway=gateway or MockFeishuGateway(output=sample_output()),
        poll_interval=s.calc.poll_interval_seconds,
        poll_timeout=s.calc.poll_timeout_seconds,
        snapshot_hook=snapshot_hook,
    )


def build_retry_policy():
    """智能重试策略；max_retries 读 settings.calc（Nacos 可配）。"""
    from app.core.config.settings import get_settings
    from app.modules.calculation.application.retry_policy import RetryPolicy

    return RetryPolicy(max_retries=get_settings().calc.max_retries)


def build_feishu_gateway():
    """按配置选网关：feishu.enabled=true 用真实 HttpFeishuGateway，否则 MockFeishuGateway（默认）。

    真实网关注入参数字典（api_cell 定位接口区单元格）与 FeishuConfig（凭据/模板/文件夹/META 单元格）。
    """
    from app.core.config.settings import get_settings

    s = get_settings()
    if s.feishu.enabled:
        from app.modules.calculation.infrastructure.feishu_http_client import HttpFeishuGateway
        return HttpFeishuGateway(config=s.feishu, param_dict=JsonParamDictRepository().load())
    return MockFeishuGateway(output=sample_output())


def build_task_service():
    """测算任务编排器（每请求新建：组装器/网关/引擎/重试/快照 全新装配）。

    网关按 feishu.enabled 选真实/Mock（build_feishu_gateway）；同一网关既供引擎读写、
    也供重试层复制副本（副本归属在重试层）。
    """
    from app.core.config.settings import get_settings
    from app.modules.calculation.application.snapshot_service import SnapshotService
    from app.modules.calculation.application.task_service import CalculationTaskService

    gateway = build_feishu_gateway()
    return CalculationTaskService(
        assembler=build_param_assembler(),
        gateway=gateway,
        engine=build_calc_engine(gateway=gateway),
        retry=build_retry_policy(),
        snapshot=SnapshotService(),
        feishu=get_settings().feishu,
    )
