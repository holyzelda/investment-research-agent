from app.modules.policy_market.domain.models import ConsultationRecord
from app.modules.policy_market.domain.ports import ConsultationRepository, PolicyAskExecutor


class ConsultationExecutionError(Exception):
    """政策知识库问答执行失败。"""


class ConsultationService:
    def __init__(
        self,
        *,
        repository: ConsultationRepository,
        executor: PolicyAskExecutor,
    ):
        self._repository = repository
        self._executor = executor

    async def create(self, *, user_id: str, question: str) -> ConsultationRecord:
        record = await self._repository.create_processing(user_id=user_id, question=question)
        try:
            answer = await self._executor.ask(question)
        except Exception as exc:
            await self._repository.mark_failed(record_id=record.id)
            raise ConsultationExecutionError("政策与市场咨询暂时不可用，请稍后重试") from exc
        return await self._repository.mark_completed(record_id=record.id, answer=answer)

    async def list_for_user(self, *, user_id: str) -> list[ConsultationRecord]:
        return await self._repository.list_by_user(user_id=user_id)

    async def get_for_user(
        self, *, record_id: int, user_id: str
    ) -> ConsultationRecord | None:
        return await self._repository.get_by_id_and_user(
            record_id=record_id,
            user_id=user_id,
        )
