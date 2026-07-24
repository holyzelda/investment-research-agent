from typing import Protocol

from app.modules.policy_market.domain.models import ConsultationAnswer, ConsultationRecord


class ConsultationRepository(Protocol):
    async def create_processing(self, *, user_id: str, question: str) -> ConsultationRecord: ...

    async def mark_completed(
        self, *, record_id: int, answer: ConsultationAnswer
    ) -> ConsultationRecord: ...

    async def mark_failed(self, *, record_id: int) -> ConsultationRecord: ...

    async def list_by_user(self, *, user_id: str) -> list[ConsultationRecord]: ...

    async def get_by_id_and_user(
        self, *, record_id: int, user_id: str
    ) -> ConsultationRecord | None: ...


class PolicyAskExecutor(Protocol):
    def ask(self, question: str) -> ConsultationAnswer: ...
