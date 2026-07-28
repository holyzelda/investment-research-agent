import types

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.policy_market.infrastructure.persistence.orm import ConsultationRecordORM


@pytest.fixture
async def consultation_client(monkeypatch):
    async def fake_get_policy_ask_module():
        return types.SimpleNamespace(
            ask=lambda question: {
                "answer": "结构化回答",
                "sources": ["https://example.test/source"],
                "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
                "reminders": ["关注更新"],
            }
        )

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_policy_ask_module,
    )
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        session.add_all([
            ConsultationRecordORM(id=1, user_id="policy-user", question="较早问题", status="completed"),
            ConsultationRecordORM(id=2, user_id="policy-user", question="较新问题", status="completed"),
            ConsultationRecordORM(id=3, user_id="another-user", question="他人问题", status="completed"),
        ])
        await session.commit()

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"userId": "policy-user", "username": "__pytest__"},
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_consultations_only_return_current_users_records(consultation_client):
    response = await consultation_client.get("/ir/policy-market/consultations")

    assert response.status_code == 200
    records = response.json()["data"]
    assert [item["id"] for item in records] == [2, 1]
    assert all("answer" not in item for item in records)


@pytest.mark.asyncio
async def test_consultation_detail_returns_404_for_another_users_record(consultation_client):
    response = await consultation_client.get("/ir/policy-market/consultations/3")

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_consultation_endpoints_require_platform_identity(consultation_client):
    response = await consultation_client.get(
        "/ir/policy-market/consultations",
        headers={"userId": "", "username": ""},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_consultation_returns_frozen_completed_detail(consultation_client):
    response = await consultation_client.post(
        "/ir/policy-market/consultations",
        json={"question": "宁夏政策"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == {
        "id": 4,
        "title": "宁夏政策",
        "question": "宁夏政策",
        "status": "completed",
        "createdAt": body["data"]["createdAt"],
        "answeredAt": body["data"]["answeredAt"],
        "answer": "结构化回答",
        "provinceCode": "宁夏",
        "topic": None,
        "sourceData": {
            "sources": ["https://example.test/source"],
            "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
            "reminders": ["关注更新"],
        },
    }


@pytest.mark.asyncio
async def test_create_consultation_rejects_blank_question(consultation_client):
    response = await consultation_client.post(
        "/ir/policy-market/consultations",
        json={"question": "  "},
    )

    assert response.status_code == 400
