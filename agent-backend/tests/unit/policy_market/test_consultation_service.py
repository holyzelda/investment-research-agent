import pytest

from app.modules.policy_market.domain.models import ConsultationAnswer, ConsultationRecord
from app.modules.policy_market.domain.ports import ConsultationRepository, PolicyAskExecutor


def test_consultation_domain_contract_is_importable_without_infrastructure():
    answer = ConsultationAnswer(
        answer="回答",
        province_code="宁夏",
        source_data={"sources": [], "timeliness": {}, "reminders": []},
    )
    record = ConsultationRecord(
        id=1,
        user_id="user-1",
        question="宁夏现货市场如何？",
        answer=answer.answer,
        province_code=answer.province_code,
        topic=None,
        status="completed",
        source_data=answer.source_data,
        created_at=None,
        answered_at=None,
        updated_at=None,
    )

    assert record.status == "completed"
    assert ConsultationRepository is not None
    assert PolicyAskExecutor is not None


def test_consultation_orm_has_user_time_index():
    from app.modules.policy_market.infrastructure.persistence.orm import ConsultationRecordORM

    indexes = {index.name for index in ConsultationRecordORM.__table__.indexes}

    assert "idx_consultation_user_time" in indexes


class FakeRepository:
    def __init__(self):
        self.records = {}
        self.next_id = 1

    async def create_processing(self, *, user_id, question):
        record = ConsultationRecord(
            self.next_id, user_id, question, None, None, None, "processing", None,
            None, None, None,
        )
        self.records[record.id] = record
        self.next_id += 1
        return record

    async def mark_completed(self, *, record_id, answer):
        old = self.records[record_id]
        record = ConsultationRecord(
            old.id, old.user_id, old.question, answer.answer, answer.province_code,
            None, "completed", answer.source_data, None, None, None,
        )
        self.records[record_id] = record
        return record

    async def mark_failed(self, *, record_id):
        old = self.records[record_id]
        record = ConsultationRecord(
            old.id, old.user_id, old.question, None, None, None, "failed", None,
            None, None, None,
        )
        self.records[record_id] = record
        return record


class FakeExecutor:
    def ask(self, question):
        return ConsultationAnswer(
            "结构化回答",
            "宁夏",
            {"sources": ["https://example.test/a"], "timeliness": {}, "reminders": []},
        )


@pytest.mark.asyncio
async def test_create_persists_completed_answer_snapshot():
    from app.modules.policy_market.application.consultation_service import ConsultationService

    service = ConsultationService(repository=FakeRepository(), executor=FakeExecutor())

    record = await service.create(user_id="u-1", question="宁夏政策")

    assert record.status == "completed"
    assert record.answer == "结构化回答"
    assert record.source_data["sources"] == ["https://example.test/a"]


@pytest.mark.asyncio
async def test_create_marks_record_failed_when_executor_raises():
    from app.modules.policy_market.application.consultation_service import (
        ConsultationExecutionError,
        ConsultationService,
    )

    class BrokenExecutor:
        def ask(self, question):
            raise RuntimeError("上游不可用")

    repository = FakeRepository()
    service = ConsultationService(repository=repository, executor=BrokenExecutor())

    with pytest.raises(ConsultationExecutionError, match="政策与市场咨询暂时不可用"):
        await service.create(user_id="u-1", question="宁夏政策")

    assert repository.records[1].status == "failed"
    assert repository.records[1].answer is None
