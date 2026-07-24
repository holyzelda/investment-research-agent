from tools import policy_ask

from app.modules.policy_market.domain.models import ConsultationAnswer


class PolicyAskExecutorAdapter:
    """将政策知识库脚本的返回值转换为应用领域结果。"""

    def ask(self, question: str) -> ConsultationAnswer:
        result = policy_ask.ask(question)
        timeliness = result.get("timeliness") or {}
        return ConsultationAnswer(
            answer=str(result.get("answer") or ""),
            province_code=timeliness.get("province"),
            source_data={
                "sources": list(result.get("sources") or []),
                "timeliness": timeliness,
                "reminders": list(result.get("reminders") or []),
            },
        )
