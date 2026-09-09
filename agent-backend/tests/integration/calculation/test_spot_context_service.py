from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import ValidationException
from app.infrastructure.database.base import Base
from app.modules.calculation.application.spot_context_service import SpotContextService
from app.modules.calculation.infrastructure.persistence.orm import (
    ConversationORM,
    ConversationSpotContextORM,
)


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


def _parsed(name="spot.xlsx", file_hash="hash-1"):
    return SimpleNamespace(
        file_name=name,
        file_sha256=file_hash,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        valid_day_count=365,
        skipped_day_count=0,
        warnings=[],
        k_results={"8": {"chargeSum": "800", "dischargeSum": "4000", "slotCount": 8}},
    )


@pytest.mark.asyncio
async def test_staged_context_binds_once_to_new_conversation(session):
    service = SpotContextService()
    token, staged = await service.save_prepared(
        session, user_id="u1", conversation_id=None, parsed=_parsed()
    )
    conversation = ConversationORM(user_id="u1", username="User")
    session.add(conversation)
    await session.commit()

    bound = await service.bind_token(
        session, token=token, user_id="u1", conversation_id=conversation.id
    )

    assert staged.id == bound.id
    assert bound.conversation_id == conversation.id
    with pytest.raises(ValidationException, match="不属于当前会话"):
        other = ConversationORM(user_id="u1", username="User")
        session.add(other)
        await session.commit()
        await service.bind_token(
            session, token=token, user_id="u1", conversation_id=other.id
        )


@pytest.mark.asyncio
async def test_upload_to_existing_conversation_replaces_single_row(session):
    service = SpotContextService()
    conversation = ConversationORM(user_id="u1", username="User")
    session.add(conversation)
    await session.commit()
    await service.save_prepared(
        session, user_id="u1", conversation_id=conversation.id, parsed=_parsed()
    )
    await service.save_prepared(
        session,
        user_id="u1",
        conversation_id=conversation.id,
        parsed=_parsed(name="new.xlsx", file_hash="hash-2"),
    )

    rows = (await session.execute(select(ConversationSpotContextORM))).scalars().all()
    assert len(rows) == 1
    assert rows[0].file_name == "new.xlsx"
    assert rows[0].file_sha256 == "hash-2"


@pytest.mark.asyncio
async def test_expired_bound_context_is_retained_without_results_and_blocks_use(session):
    service = SpotContextService()
    conversation = ConversationORM(user_id="u1", username="User")
    session.add(conversation)
    await session.commit()
    _, context = await service.save_prepared(
        session, user_id="u1", conversation_id=conversation.id, parsed=_parsed()
    )
    context.expires_at = datetime.now() - timedelta(seconds=1)
    await session.commit()

    with pytest.raises(ValidationException, match="已失效"):
        await service.get_for_conversation(
            session, conversation_id=conversation.id, user_id="u1"
        )

    await session.refresh(context)
    assert context.status == "expired"
    assert context.k_results == {}
