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
            province_code=result.get("province"),
            source_data={
                "sources": list(result.get("sources") or []),
            },
        )
