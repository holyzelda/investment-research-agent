"""calculation 领域 · 端口（抽象网关）。

依赖倒置：application/domain 只依赖这些抽象；infrastructure 提供实现。
单测通过注入 mock 实现，隔离飞书/电价库/文件 I/O。
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.modules.calculation.domain.models import ProvinceRevenueProfile


class RevenueStructureReader(ABC):
    """各省收益结构表读取端口（stub 读本地副本，Batch3 切飞书）。"""

    @abstractmethod
    def get_profile(self, province: str) -> Optional[ProvinceRevenueProfile]:
        """按省份返回收益结构画像；省份不存在返回 None。"""
        raise NotImplementedError


class MidLongPriceProvider(ABC):
    """中长期充/放电均价常量端口（仅宁夏有值）。"""

    @abstractmethod
    def get_prices(self, province: str) -> tuple[Optional[float], Optional[float]]:
        """返回 (充电均价, 放电均价)；无则 (None, None)。"""
        raise NotImplementedError


class SpotPriceAlgo(ABC):
    """现货充/放电均价二次计算端口（电价库多循环 DP，PRD 挂账#6；stub 返回固定值）。"""

    @abstractmethod
    def compute(
        self, province: str, node_name: Optional[str],
        capacity_mwh: float, power_mw: float, daily_cycles: float,
    ) -> tuple[Optional[float], Optional[float]]:
        """返回 (现货充电均价, 现货放电均价)。node_name 有值走节点级库，否则省级库。"""
        raise NotImplementedError


class FeishuGateway(ABC):
    """飞书接口区读写端口（方案A：只读写 API_INPUT/OUTPUT/META）。

    异步 I/O：真实实现（HttpFeishuGateway）用 httpx.AsyncClient；轮询等算不阻塞事件循环。
    副本策略：copy_template 每次新测算复制新副本；重试复用同一 doc_token（不再复制）。
    """

    @abstractmethod
    async def copy_template(self, template_token: str, name: Optional[str] = None) -> str:
        """从指定模板复制副本，返回新副本的 doc_token（独立文档隔离）。

        name 为副本显示名（城市-节点-功率/容量-时间，由应用层拼），None 时用实现默认名。
        """
        raise NotImplementedError

    @abstractmethod
    async def write_input(self, doc_token: str, payload: dict) -> None:
        """写入 API_INPUT（参数ID→值）。"""
        raise NotImplementedError

    @abstractmethod
    async def write_meta(self, doc_token: str, meta: dict) -> None:
        """写入 API_META（request_id / 参数hash / 模板版本）。"""
        raise NotImplementedError

    @abstractmethod
    async def read_meta(self, doc_token: str) -> dict:
        """读取 API_META，至少含 {status, request_id}（等算完成判定）。"""
        raise NotImplementedError

    @abstractmethod
    async def read_output(self, doc_token: str) -> dict:
        """读取 API_OUTPUT（参数ID→值）。"""
        raise NotImplementedError

    async def read_report_sources(
        self,
        *,
        doc_token: str,
        province: str | None,
        energy_sheet: str,
        energy_range: str,
        market_sheet: str,
        market_range: str,
        chart_sheet: str,
        chart_end_column: str,
    ) -> dict:
        """读取报告专用省份资料与画图数据，供测算完成时冻结。"""
        raise NotImplementedError
