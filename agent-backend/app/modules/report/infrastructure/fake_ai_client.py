"""报告 AI 的确定性测试实现。"""
from collections import defaultdict

from app.modules.report.domain.ports import ReportAiPort


class FakeReportAiClient(ReportAiPort):
    def __init__(self, failures: dict[str, int] | None = None):
        self._remaining_failures = dict(failures or {})
        self.calls = defaultdict(int)

    async def generate_section(
        self, rule: dict, context: dict, *, user_id: str = "", username: str = ""
    ) -> str:
        key = rule["key"]
        self.calls[key] += 1
        if self._remaining_failures.get(key, 0) > 0:
            self._remaining_failures[key] -= 1
            raise RuntimeError(f"模拟 {key} 生成失败")
        province = context.get("project", {}).get("province") or "该项目"
        return f"{province}{rule['title']}已基于本次冻结测算数据生成。"
