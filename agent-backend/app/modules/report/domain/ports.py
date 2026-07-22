"""正式报告 AI 端口。"""
from abc import ABC, abstractmethod


class ReportAiPort(ABC):
    @abstractmethod
    async def generate_section(self, rule: dict, context: dict) -> str:
        """按冻结上下文生成一节面向读者的分析文本。"""
        raise NotImplementedError
