from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.modules.policy_market.domain.models import ConsultationAnswer
from app.modules.policy_market.infrastructure.persistence.consultation_repository import (
    SqlAlchemyConsultationRepository,
)


@pytest.mark.asyncio
async def test_repository_lists_only_current_user_in_reverse_creation_order():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with maker() as session:
        repository = SqlAlchemyConsultationRepository(session)
        first = await repository.create_processing(user_id="user-1", question="第一个问题")
        second = await repository.create_processing(user_id="user-1", question="第二个问题")
        await repository.create_processing(user_id="user-2", question="其他用户的问题")
        await session.commit()

        records = await repository.list_by_user(user_id="user-1")

    assert [item.id for item in records] == [second.id, first.id]
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_updates_completed_answer_and_hides_another_users_detail():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with maker() as session:
        repository = SqlAlchemyConsultationRepository(session)
        created = await repository.create_processing(user_id="user-1", question="宁夏政策")
        completed = await repository.mark_completed(
            record_id=created.id,
            answer=ConsultationAnswer(
                answer="结构化回答",
                province_code="宁夏",
                source_data={"sources": [], "timeliness": {}, "reminders": []},
            ),
        )
        await session.commit()

        hidden = await repository.get_by_id_and_user(record_id=created.id, user_id="user-2")

    assert completed.status == "completed"
    assert completed.answered_at is not None
    assert completed.source_data == {"sources": [], "timeliness": {}, "reminders": []}
    assert hidden is None
    await engine.dispose()
