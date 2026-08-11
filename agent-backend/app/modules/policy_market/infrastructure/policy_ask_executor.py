import asyncio

from app.modules.policy_market.infrastructure.policy_ask_loader import get_policy_ask_module

from app.modules.policy_market.domain.models import ConsultationAnswer


class PolicyAskExecutorAdapter:
    """将政策知识库脚本的返回值转换为应用领域结果。"""

    async def ask(self, question: str) -> ConsultationAnswer:
        policy_ask = await get_policy_ask_module()
        result = await asyncio.to_thread(policy_ask.ask, question)
        return ConsultationAnswer(
            answer=str(result.get("answer") or ""),
            # 咨询结果只对外暴露结论与源文件：省份、时效、核验状态属于检索元信息，
            # 仍在 tools 层落飞书评估表，不再随快照返回给前端。
            province_code=None,
            source_data={"references": list(result.get("references") or [])},
        )
