from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.policy_market.domain.models import ConsultationAnswer, ConsultationRecord
from app.modules.policy_market.infrastructure.persistence.orm import ConsultationRecordORM


class SqlAlchemyConsultationRepository:
    """咨询记录的 SQLAlchemy 持久化实现。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_processing(self, *, user_id: str, question: str) -> ConsultationRecord:
        row = ConsultationRecordORM(
            user_id=user_id,
            question=question,
            status="processing",
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def mark_completed(
        self, *, record_id: int, answer: ConsultationAnswer
    ) -> ConsultationRecord:
        row = await self._require_row(record_id)
        row.answer = answer.answer
        row.province_code = answer.province_code
        row.source_data = answer.source_data
        row.status = "completed"
        row.answered_at = datetime.now()
        await self._session.flush()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def mark_failed(self, *, record_id: int) -> ConsultationRecord:
        row = await self._require_row(record_id)
        row.status = "failed"
        await self._session.flush()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def list_by_user(self, *, user_id: str) -> list[ConsultationRecord]:
        statement = (
            select(ConsultationRecordORM)
            .where(ConsultationRecordORM.user_id == user_id)
            .order_by(
                ConsultationRecordORM.created_at.desc(),
                ConsultationRecordORM.id.desc(),
            )
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def get_by_id_and_user(
        self, *, record_id: int, user_id: str
    ) -> ConsultationRecord | None:
        statement = select(ConsultationRecordORM).where(
            ConsultationRecordORM.id == record_id,
            ConsultationRecordORM.user_id == user_id,
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def delete_by_id_and_user(self, *, record_id: int, user_id: str) -> bool:
        statement = delete(ConsultationRecordORM).where(
            ConsultationRecordORM.id == record_id,
            ConsultationRecordORM.user_id == user_id,
        )
        result = await self._session.execute(statement)
        return result.rowcount > 0

    async def _require_row(self, record_id: int) -> ConsultationRecordORM:
        row = await self._session.get(ConsultationRecordORM, record_id)
        if row is None:
            raise LookupError(f"咨询记录不存在：{record_id}")
        return row

    @staticmethod
    def _to_domain(row: ConsultationRecordORM) -> ConsultationRecord:
        return ConsultationRecord(
            id=row.id,
            user_id=row.user_id,
            question=row.question,
            answer=row.answer,
            province_code=row.province_code,
            topic=row.topic,
            status=row.status,
            source_data=row.source_data,
            created_at=row.created_at,
            answered_at=row.answered_at,
            updated_at=row.updated_at,
        )
