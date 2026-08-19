"""应用配置（基础设施层）。

分层：固定启动配置（.env）与默认值；业务配置为默认值 → configs/application.yml
→ 业务环境变量 → Nacos 远端业务配置（最高优先级）。log/cors 只从 .env 读取。
Nacos 装载在启动时执行（见 app/infrastructure/nacos/client.py），装载结果并入本模块缓存。

说明：本系统采用团队统一栈（FastAPI + 异步 SQLAlchemy + Nacos），
仅框架选型与 trader 一致，配置实现为本项目自研。
"""
import copy
import os
from functools import lru_cache
from typing import Any, Optional

import yaml
from loguru import logger
from pydantic import BaseModel, Field

# __file__ = app/infrastructure/config/settings.py
# 4 层 dirname：config → infrastructure → app → agent-backend
CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs"
)
APPLICATION_YML = os.path.join(CONFIG_DIR, "application.yml")

# Nacos 仅覆盖业务配置；启动和 Nacos 连接本身必须在进程启动前确定。
_nacos_overrides: dict[str, Any] = {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def set_nacos_overrides(config: dict[str, Any]) -> None:
    """保存远端业务配置；固定的 app、log、cors 和 nacos 配置不由 Nacos 覆盖。"""
    global _nacos_overrides
    _nacos_overrides = {
        key: copy.deepcopy(value)
        for key, value in (config or {}).items()
        if key not in {"app", "log", "cors", "nacos"}
    }


def clear_nacos_overrides() -> None:
    global _nacos_overrides
    _nacos_overrides = {}


def _load_yaml() -> dict:
    if not os.path.exists(APPLICATION_YML):
        logger.warning(f"配置文件不存在：{APPLICATION_YML}，使用默认值")
        return {}
    try:
        with open(APPLICATION_YML, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:  # noqa: BLE001
        logger.error(f"加载 application.yml 失败：{e}")
        return {}


def _nested(cfg: dict, keys: list[str], default: Any = None) -> Any:
    cur = cfg
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _as_bool(value: Any) -> bool:
    return str(value).lower() == "true"


def _as_list(value: str | None, default: list[str]) -> list[str]:
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _business_value(env_name: str, config: dict[str, Any], keys: list[str], default: Any) -> Any:
    """Nacos 远端业务配置最高，其次保留既有 IR_* 环境变量兼容性。"""
    remote_value = _nested(_nacos_overrides, keys)
    if remote_value is not None:
        return remote_value
    return os.getenv(env_name, _nested(config, keys, default))


class AppConfig(BaseModel):
    name: str = "ir-agent"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    description: str = "朱雀投研智能体 ZRA-3 后端（平台子应用）"


class LogConfig(BaseModel):
    """Loguru 控制台与文件输出配置。"""

    level: str = "DEBUG"
    format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}"
    dir: str = "./logs"
    rotation: str = "00:00"
    retention: str = "7 days"


class DatabaseConfig(BaseModel):
    # 主数据源 ir_agent。应用默认连测试库（见 configs/application.yml，mysql+aiomysql）。
    # 纯单元测试由 tests/conftest.py 用 IR_DB_URL 覆盖为内存 sqlite。
    url: str = "mysql+aiomysql://root:<PASSWORD>@internal-3-60.example.invalid:3306/ir_agent"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class NacosConfig(BaseModel):
    enabled: bool = False
    server_addr: str = "127.0.0.1:8848"
    namespace: str = "test"
    group: str = "DEFAULT_GROUP"
    profile: str = "test"
    service_name: str = "ir-agent"


class CorsConfig(BaseModel):
    allow_origins: list[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    expose_headers: list[str] = ["X-IR-Conversation-Id"]


class MiddlePlatformConfig(BaseModel):
    """智能体中台对话代理配置。"""

    app_id: str = "ir_agent"
    app_secret: str = ""
    # 各中台服务地址独立（不同端口），均配置完整 URL。
    chat_url: str = "http://internal-2-58.example.invalid:8089/api/v1/chat/diag"
    auth_token_url: str = "http://internal-2-58.example.invalid:8089/api/v1/auth/token"
    report_model_url: str = "http://internal-2-58.example.invalid:8180/gateway/agent-middle/api/v1/model-pool/chat"
    report_model_name: str = "qwen-plus"
    report_model_timeout_seconds: float = 30.0
    report_model_concurrency: int = Field(default=5, ge=1)

class CalcConfig(BaseModel):
    """测算执行参数（Nacos 可配）：轮询间隔/总超时/重试上限。"""
    poll_interval_seconds: float = 3.0
    poll_timeout_seconds: float = 10.0
    max_retries: int = 3
    share_fernet_key: str = ""


class FeishuConfig(BaseModel):
    """飞书电子表格集成（方案A：只读写 API_INPUT/OUTPUT/META 接口区）。

    enabled=false 时系统用 MockFeishuGateway（默认，不连真飞书）。
    凭据与接口区地址由业务/运维提供（Nacos/env），到位后仅改配置即可上线（挂账 #2/#5/#7）。
    """
    enabled: bool = False
    base_url: str = "https://open.feishu.cn"
    app_id: str = ""
    app_secret: str = ""
    template_token_15_years: str = ""  # 15年模板电子表格 token（被复制的源）
    template_token_20_years: str = ""  # 20年模板电子表格 token（被复制的源）
    target_folder_token: str = ""      # 副本目标文件夹 token
    copy_name_prefix: str = "zra-calc"
    # API_META 接口区单元格（业务冻结后经 Nacos/env 覆盖；格式 title!cell）
    meta_status_cell: str = "API_META!B1"
    meta_request_id_cell: str = "API_META!B2"
    meta_param_hash_cell: str = "API_META!B3"
    meta_done_value: str = "done"      # status 单元格表示"算完"的取值（业务约定）
    # 表2《各省收益结构》——独立电子表格（稳定 token，非底稿副本），方案A"表2取数由后端做"的源。
    # 换电压/省份开关等由后端读表2算好后写 API_INPUT；空 token 时回退本地 json（JsonRevenueStructureReader）。
    revenue_structure_token: str = ""              # 表2 电子表格 token（稳定，不随测算副本变）
    revenue_structure_sheet: str = "各省收益结构"     # 表2 sheet 名（title；v2 需再解析 sheetId）
    revenue_structure_range: str = "A4:S40"        # 数据区：表头在第2行，省份数据行4起，列 A:S
    report_energy_structure_sheet: str = "各省能源结构"
    report_energy_structure_range: str = "A1:F100"
    report_market_status_sheet: str = "各省电力市场情况"
    report_market_status_range: str = "A1:G100"
    report_chart_sheet: str = "画图数据"


class ProvincePriceCoefficient(BaseModel):
    """省级现货充、放电均价修正系数。"""
    charge: float = Field(gt=0)
    discharge: float = Field(gt=0)


class SpotPriceConfig(BaseModel):
    """现货电价库（多循环 DP，离线预计算）。enabled=false 时用 NullSpotPriceAlgo（默认，不连库、返回 None）。

    enabled=true 时测算走 PrecomputeSpotPriceAlgo 查 ir_agent 预计算表；
    预计算脚本 tools/spot_precompute.py 用下列 DSN 读源库、算好写表。测试期 DSN 明文，正式改 Nacos。
    """
    enabled: bool = False
    # 省级电价库：long 格式，96 行/天(time=00:15..24:00)，price 为 varchar
    province_dsn: str = ""                          # mysql+pymysql://example_user:example_password@database.example.invalid:3306/lamda_data
    province_table: str = "market_curve_points_current"
    province_market: str = "省内市场"                # 仅取 market=省内市场
    # 节点级电价库：wide 格式，96 列(00:15..24:00) decimal，node=station_name
    node_dsn: str = ""                              # mysql+pymysql://example_user:example_password@database.example.invalid:3306/dlsc_mengxi
    node_table: str = "real_time_spot_price"
    node_price_type: int = 1                        # 仅取 price_type=1（节点电价）
    # 算法默认（spec §3）
    min_action_minutes: int = 30
    switch_gap_minutes: int = 15
    # 未配置省份默认不修正；每个已配置省份都必须给出 charge / discharge。
    province_price_coefficients: dict[str, ProvincePriceCoefficient] = Field(default_factory=dict)
    # 应用内日更：默认关闭，仅指定部署机开启，避免测试/多实例环境误触发。
    daily_update_enabled: bool = False
    daily_update_hour: int = Field(default=3, ge=0, le=23)
    daily_update_minute: int = Field(default=30, ge=0, le=59)
    daily_update_workers: int = Field(default=4, ge=1)


class PolicyAskFeishuConfig(BaseModel):
    """政策问答知识库的飞书凭据与文档标识。"""

    app_id: str = ""
    app_secret: str = ""
    index_token: str = ""
    province_tokens: dict[str, str] = Field(default_factory=dict)
    cross_province_token: str = ""
    domain: str = "example-value-0071"


class PolicyAskLlmConfig(BaseModel):
    """政策问答使用的 LLM 服务配置。"""

    base_url: str = ""
    api_key: str = ""
    model: str = ""


class PolicyAskAnysearchConfig(BaseModel):
    api_key: str = ""
    tavily_api_key: str = ""


class PolicyAskBaseConfig(BaseModel):
    token: str = ""
    table: str = ""


class PolicyAskConfig(BaseModel):
    """政策与市场问答配置。"""

    feishu: PolicyAskFeishuConfig = Field(default_factory=PolicyAskFeishuConfig)
    llm: PolicyAskLlmConfig = Field(default_factory=PolicyAskLlmConfig)
    anysearch: PolicyAskAnysearchConfig = Field(default_factory=PolicyAskAnysearchConfig)
    base: PolicyAskBaseConfig = Field(default_factory=PolicyAskBaseConfig)


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    log: LogConfig = LogConfig()
    database: DatabaseConfig = DatabaseConfig()
    nacos: NacosConfig = NacosConfig()
    cors: CorsConfig = CorsConfig()
    calc: CalcConfig = CalcConfig()
    middle_platform: MiddlePlatformConfig = MiddlePlatformConfig()
    feishu: FeishuConfig = FeishuConfig()
    spot_price: SpotPriceConfig = SpotPriceConfig()
    policy_ask: PolicyAskConfig = Field(default_factory=PolicyAskConfig)


def _build_settings() -> Settings:
    y = _deep_merge(_load_yaml(), _nacos_overrides)

    app = AppConfig(
        name=os.getenv("APP_NAME", _nested(y, ["app", "name"], "ir-agent")),
        version=os.getenv("APP_VERSION", _nested(y, ["app", "version"], "0.1.0")),
        debug=_as_bool(os.getenv("APP_DEBUG", _nested(y, ["app", "debug"], True))),
        host=os.getenv("APP_HOST", _nested(y, ["app", "host"], "0.0.0.0")),
        port=int(os.getenv("APP_PORT", _nested(y, ["app", "port"], 8080))),
        description=os.getenv("APP_DESCRIPTION", _nested(y, ["app", "description"], AppConfig().description)),
    )
    _ld = LogConfig()
    log = LogConfig(
        level=os.getenv("APP_LOG_LEVEL", _ld.level),
        format=os.getenv("APP_LOG_FORMAT", _ld.format),
        dir=os.getenv("APP_LOG_DIR", _ld.dir),
        rotation=os.getenv("APP_LOG_ROTATION", _ld.rotation),
        retention=os.getenv("APP_LOG_RETENTION", _ld.retention),
    )
    database = DatabaseConfig(
        url=_business_value("IR_DB_URL", y, ["database", "url"], DatabaseConfig().url),
        echo=_nested(y, ["database", "echo"], False),
        pool_size=int(_nested(y, ["database", "pool_size"], DatabaseConfig().pool_size)),
        max_overflow=int(_nested(y, ["database", "max_overflow"], DatabaseConfig().max_overflow)),
    )
    nacos = NacosConfig(
        enabled=_as_bool(os.getenv("NACOS_ENABLED", _nested(y, ["nacos", "enabled"], False))),
        server_addr=os.getenv("NACOS_SERVER_ADDR", _nested(y, ["nacos", "server_addr"], "127.0.0.1:8848")),
        namespace=os.getenv("NACOS_NAMESPACE", _nested(y, ["nacos", "namespace"], "test")),
        group=os.getenv("NACOS_GROUP", _nested(y, ["nacos", "group"], "DEFAULT_GROUP")),
        profile=os.getenv("NACOS_PROFILE", _nested(y, ["nacos", "profile"], "test")),
        service_name=os.getenv("NACOS_DISCOVERY_SERVICE_NAME", os.getenv(
            "NACOS_SERVICE_NAME", _nested(y, ["nacos", "service_name"], "ir-agent"))),
    )
    cors = CorsConfig(
        allow_origins=_as_list(os.getenv("APP_CORS_ALLOW_ORIGINS"), ["*"]),
        allow_credentials=_as_bool(os.getenv("APP_CORS_ALLOW_CREDENTIALS", "true")),
        allow_methods=_as_list(os.getenv("APP_CORS_ALLOW_METHODS"), ["*"]),
        allow_headers=_as_list(os.getenv("APP_CORS_ALLOW_HEADERS"), ["*"]),
        expose_headers=["X-IR-Conversation-Id"],
    )
    calc = CalcConfig(
        poll_interval_seconds=float(_business_value("IR_CALC_POLL_INTERVAL", y, ["calc", "poll_interval_seconds"], 3.0)),
        poll_timeout_seconds=float(_business_value("IR_CALC_POLL_TIMEOUT", y, ["calc", "poll_timeout_seconds"], 10.0)),
        max_retries=int(_business_value("IR_CALC_MAX_RETRIES", y, ["calc", "max_retries"], 3)),
        share_fernet_key=str(_business_value(
            "IR_CALC_SHARE_FERNET_KEY", y, ["calc", "share_fernet_key"], ""
        )),
    )
    _mpd = MiddlePlatformConfig()
    middle_platform = MiddlePlatformConfig(
        app_id=_business_value(
            "IR_MIDDLE_PLATFORM_APP_ID", y, ["middle_platform", "app_id"], _mpd.app_id),
        app_secret=_business_value(
            "IR_MIDDLE_PLATFORM_APP_SECRET", y, ["middle_platform", "app_secret"], _mpd.app_secret),
        chat_url=_business_value(
            "IR_MIDDLE_PLATFORM_CHAT_URL", y, ["middle_platform", "chat_url"], _mpd.chat_url),
        auth_token_url=_business_value(
            "IR_MIDDLE_PLATFORM_AUTH_TOKEN_URL", y, ["middle_platform", "auth_token_url"], _mpd.auth_token_url),
        report_model_url=_business_value(
            "IR_MIDDLE_PLATFORM_REPORT_MODEL_URL", y, ["middle_platform", "report_model_url"], _mpd.report_model_url),
        report_model_name=_business_value(
            "IR_MIDDLE_PLATFORM_REPORT_MODEL_NAME", y, ["middle_platform", "report_model_name"], _mpd.report_model_name),
        report_model_timeout_seconds=float(_business_value(
            "IR_MIDDLE_PLATFORM_REPORT_MODEL_TIMEOUT_SECONDS", y,
            ["middle_platform", "report_model_timeout_seconds"], _mpd.report_model_timeout_seconds)),
        report_model_concurrency=int(_business_value(
            "IR_MIDDLE_PLATFORM_REPORT_MODEL_CONCURRENCY", y,
            ["middle_platform", "report_model_concurrency"], _mpd.report_model_concurrency)),
    )
    _fd = FeishuConfig()
    feishu = FeishuConfig(
        enabled=_as_bool(_business_value("IR_FEISHU_ENABLED", y, ["feishu", "enabled"], False)),
        base_url=_business_value("IR_FEISHU_BASE_URL", y, ["feishu", "base_url"], _fd.base_url),
        app_id=_business_value("IR_FEISHU_APP_ID", y, ["feishu", "app_id"], ""),
        app_secret=_business_value("IR_FEISHU_APP_SECRET", y, ["feishu", "app_secret"], ""),
        template_token_15_years=_business_value(
            "IR_FEISHU_TEMPLATE_TOKEN_15_YEARS", y, ["feishu", "template_token_15_years"], ""),
        template_token_20_years=_business_value(
            "IR_FEISHU_TEMPLATE_TOKEN_20_YEARS", y, ["feishu", "template_token_20_years"], ""),
        target_folder_token=_business_value("IR_FEISHU_FOLDER_TOKEN", y, ["feishu", "target_folder_token"], ""),
        copy_name_prefix=_nested(y, ["feishu", "copy_name_prefix"], _fd.copy_name_prefix),
        meta_status_cell=_nested(y, ["feishu", "meta_status_cell"], _fd.meta_status_cell),
        meta_request_id_cell=_nested(y, ["feishu", "meta_request_id_cell"], _fd.meta_request_id_cell),
        meta_param_hash_cell=_nested(y, ["feishu", "meta_param_hash_cell"], _fd.meta_param_hash_cell),
        meta_done_value=_nested(y, ["feishu", "meta_done_value"], _fd.meta_done_value),
        revenue_structure_token=_business_value("IR_FEISHU_REVENUE_TOKEN", y, ["feishu", "revenue_structure_token"], ""),
        revenue_structure_sheet=_nested(y, ["feishu", "revenue_structure_sheet"], _fd.revenue_structure_sheet),
        revenue_structure_range=_nested(y, ["feishu", "revenue_structure_range"], _fd.revenue_structure_range),
    )
    _sd = SpotPriceConfig()
    spot_price = SpotPriceConfig(
        enabled=_as_bool(_business_value("IR_SPOT_ENABLED", y, ["spot_price", "enabled"], False)),
        province_dsn=_business_value("IR_SPOT_PROVINCE_DSN", y, ["spot_price", "province_dsn"], ""),
        province_table=_nested(y, ["spot_price", "province_table"], _sd.province_table),
        province_market=_nested(y, ["spot_price", "province_market"], _sd.province_market),
        node_dsn=_business_value("IR_SPOT_NODE_DSN", y, ["spot_price", "node_dsn"], ""),
        node_table=_nested(y, ["spot_price", "node_table"], _sd.node_table),
        node_price_type=int(_nested(y, ["spot_price", "node_price_type"], _sd.node_price_type)),
        min_action_minutes=int(_nested(y, ["spot_price", "min_action_minutes"], _sd.min_action_minutes)),
        switch_gap_minutes=int(_nested(y, ["spot_price", "switch_gap_minutes"], _sd.switch_gap_minutes)),
        province_price_coefficients=_nested(
            y, ["spot_price", "province_price_coefficients"], _sd.province_price_coefficients),
        daily_update_enabled=_as_bool(_business_value(
            "IR_SPOT_DAILY_UPDATE_ENABLED", y, ["spot_price", "daily_update_enabled"], _sd.daily_update_enabled)),
        daily_update_hour=int(_nested(y, ["spot_price", "daily_update_hour"], _sd.daily_update_hour)),
        daily_update_minute=int(_nested(y, ["spot_price", "daily_update_minute"], _sd.daily_update_minute)),
        daily_update_workers=int(_nested(y, ["spot_price", "daily_update_workers"], _sd.daily_update_workers)),
    )
    _pad = PolicyAskConfig()
    policy_ask = PolicyAskConfig(
        feishu=PolicyAskFeishuConfig(
            app_id=_nested(y, ["policy_ask", "feishu", "app_id"], _pad.feishu.app_id),
            app_secret=_nested(y, ["policy_ask", "feishu", "app_secret"], _pad.feishu.app_secret),
            index_token=_nested(y, ["policy_ask", "feishu", "index_token"], _pad.feishu.index_token),
            province_tokens=_nested(
                y, ["policy_ask", "feishu", "province_tokens"], _pad.feishu.province_tokens),
            cross_province_token=_nested(
                y, ["policy_ask", "feishu", "cross_province_token"], _pad.feishu.cross_province_token),
        ),
        llm=PolicyAskLlmConfig(
            base_url=_nested(y, ["policy_ask", "llm", "base_url"], _pad.llm.base_url),
            api_key=_nested(y, ["policy_ask", "llm", "api_key"], _pad.llm.api_key),
            model=_nested(y, ["policy_ask", "llm", "model"], _pad.llm.model),
        ),
        anysearch=PolicyAskAnysearchConfig(
            api_key=_nested(y, ["policy_ask", "anysearch", "api_key"], _pad.anysearch.api_key),
            tavily_api_key=_nested(y, ["policy_ask", "anysearch", "tavily_api_key"], _pad.anysearch.tavily_api_key),
        ),
        base=PolicyAskBaseConfig(
            token=_nested(y, ["policy_ask", "base", "token"], _pad.base.token),
            table=_nested(y, ["policy_ask", "base", "table"], _pad.base.table),
        ),
    )
    return Settings(
        app=app, log=log, database=database, nacos=nacos, cors=cors,
        calc=calc, middle_platform=middle_platform, feishu=feishu,
        spot_price=spot_price, policy_ask=policy_ask,
    )


@lru_cache
def get_settings() -> Settings:
    return _build_settings()


def get_app_config() -> AppConfig:
    return get_settings().app


def get_log_config() -> LogConfig:
    return get_settings().log


def get_cors_config() -> CorsConfig:
    return get_settings().cors


def get_nacos_config() -> NacosConfig:
    return get_settings().nacos


def reload_settings() -> Settings:
    """Nacos 装载后或测试中重建配置缓存。"""
    get_settings.cache_clear()
    return get_settings()


_logging_signature: tuple[str, str, str, str, str] | None = None


def configure_logging(settings: LogConfig | None = None) -> None:
    """配置 Loguru 控制台和按天滚动的文件输出。"""
    global _logging_signature

    settings = settings or get_log_config()
    signature = (
        settings.level,
        settings.format,
        settings.dir,
        settings.rotation,
        settings.retention,
    )
    if signature == _logging_signature:
        return

    import sys

    os.makedirs(settings.dir, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=settings.level, format=settings.format)
    logger.add(
        os.path.join(settings.dir, "{time:YYYY-MM-DD}.log"),
        level=settings.level,
        format=settings.format,
        rotation=settings.rotation,
        retention=settings.retention,
        encoding="utf-8",
    )
    _logging_signature = signature
