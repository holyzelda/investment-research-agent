"""GET /ir/trial/quota 与业务端点的试用额度行为。"""
from __future__ import annotations

import types

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.trial_quota.application.trial_quota_service import (
    TRIAL_DAILY_LIMIT,
    TrialQuotaService,
)
from app.modules.trial_quota.application.trial_role_service import TrialRoleUnavailable
from app.modules.trial_quota.interface.deps import get_trial_role_service


class FakeTrialRole:
    def __init__(self, result=True):
        self._result = result

    async def is_trial(self, user_id):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


@pytest.fixture
async def quota_env(monkeypatch):
    async def fake_get_policy_ask_module():
        return types.SimpleNamespace(
            ask=lambda question: {"answer": "结构化回答[1]。", "references": []},
            fetch_source_file=lambda token: (b"%PDF-1.7", "宁夏调频细则.pdf", "application/pdf"),
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
    role = FakeTrialRole(True)

    async def _override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_trial_role_service] = lambda: role
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"userId": "trial-user", "username": "__pytest__"},
    ) as client:
        yield {"client": client, "role": role, "maker": maker}
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_trial_role_service, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_trial_user_gets_full_quota_structure(quota_env):
    response = await quota_env["client"].get("/ir/trial/quota")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["isTrial"] is True
    assert "usageDate" in data
    for feature in ("calculation", "report", "consultation"):
        assert data[feature] == {
            "used": 0,
            "limit": TRIAL_DAILY_LIMIT,
            "remaining": TRIAL_DAILY_LIMIT,
        }


@pytest.mark.asyncio
async def test_normal_account_gets_minimal_non_trial_payload(quota_env):
    quota_env["role"]._result = False

    response = await quota_env["client"].get("/ir/trial/quota")

    assert response.status_code == 200
    assert response.json()["data"] == {"isTrial": False}


@pytest.mark.asyncio
async def test_role_check_failure_returns_503(quota_env):
    quota_env["role"]._result = TrialRoleUnavailable()

    response = await quota_env["client"].get("/ir/trial/quota")

    assert response.status_code == 503
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_endpoint_requires_platform_identity(quota_env):
    response = await quota_env["client"].get(
        "/ir/trial/quota", headers={"userId": "", "username": ""}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_quota_reflects_reserved_usage(quota_env):
    async with quota_env["maker"]() as session:
        await TrialQuotaService().reserve(session, "trial-user", "calculation")
        await TrialQuotaService().reserve(session, "trial-user", "consultation")

    response = await quota_env["client"].get("/ir/trial/quota")

    data = response.json()["data"]
    assert data["calculation"]["used"] == 1
    assert data["report"]["used"] == 0
    assert data["consultation"]["used"] == 1


@pytest.mark.asyncio
async def test_consultation_exhaustion_returns_403_after_five_successes(quota_env):
    client = quota_env["client"]
    for _ in range(TRIAL_DAILY_LIMIT):
        response = await client.post(
            "/ir/policy-market/consultations", json={"question": "宁夏现货市场"}
        )
        assert response.status_code == 200

    exhausted = await client.post(
        "/ir/policy-market/consultations", json={"question": "再多问一次"}
    )

    assert exhausted.status_code == 403
    assert "政策咨询" in exhausted.json()["msg"]
    assert "明日恢复" in exhausted.json()["msg"]


@pytest.mark.asyncio
async def test_blank_question_is_rejected_without_consuming_quota(quota_env):
    client = quota_env["client"]
    for _ in range(3):
        response = await client.post(
            "/ir/policy-market/consultations", json={"question": "   "}
        )
        assert response.status_code == 400

    data = (await client.get("/ir/trial/quota")).json()["data"]
    assert data["consultation"]["used"] == 0


@pytest.mark.asyncio
async def test_failed_consultation_refunds_reserved_quota(quota_env, monkeypatch):
    calls = {"n": 0}

    async def flaky_module():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("知识库暂不可用")
        return types.SimpleNamespace(
            ask=lambda question: {"answer": "结构化回答[1]。", "references": []},
            fetch_source_file=lambda token: (b"%PDF-1.7", "a.pdf", "application/pdf"),
        )

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        flaky_module,
    )
    client = quota_env["client"]

    failed = await client.post(
        "/ir/policy-market/consultations", json={"question": "宁夏现货市场"}
    )
    assert failed.status_code == 400

    ok_response = await client.post(
        "/ir/policy-market/consultations", json={"question": "宁夏现货市场"}
    )
    assert ok_response.status_code == 200

    data = (await client.get("/ir/trial/quota")).json()["data"]
    assert data["consultation"]["used"] == 1
