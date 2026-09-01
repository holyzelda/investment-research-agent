"""e2e：台账首屏聚合只解析一次可见范围，并保持统一响应壳。"""
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.calculation.interface import ledger_router
from app.modules.platform_access.domain.models import OrganizationUser, UserScope
from app.modules.platform_access.interface.deps import get_user_scope

HEADERS = {"userId": "119", "username": "bjjzA"}


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.pop(get_user_scope, None)
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_bootstrap_aggregates_scope_provinces_and_records_once(monkeypatch):
    scope_calls = 0
    scope = UserScope(
        current_user_id="119",
        is_admin=True,
        users=(
            OrganizationUser(user_id="119", nick_name="北京金租管理员"),
            OrganizationUser(user_id="120", nick_name="北京金租普通账号"),
        ),
    )

    async def resolve_scope():
        nonlocal scope_calls
        scope_calls += 1
        return scope

    session = object()
    app.dependency_overrides[get_user_scope] = resolve_scope
    app.dependency_overrides[get_db_session] = lambda: session
    list_provinces = AsyncMock(return_value=["宁夏", "甘肃"])
    list_records = AsyncMock(return_value={
        "items": [{"taskId": 42, "title": "甘肃 储能测算"}],
        "total": 1,
        "page": 1,
        "pageSize": 10,
    })
    monkeypatch.setattr(ledger_router._service, "list_provinces", list_provinces)
    monkeypatch.setattr(ledger_router._service, "list_records", list_records)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/ir/calc/ledger/bootstrap",
            params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert scope_calls == 1
    assert response.json()["data"] == {
        "users": {
            "isAdmin": True,
            "users": [
                {"userId": "119", "nickName": "北京金租管理员"},
                {"userId": "120", "nickName": "北京金租普通账号"},
            ],
        },
        "provinces": {"items": ["宁夏", "甘肃"]},
        "records": {
            "items": [{"taskId": 42, "title": "甘肃 储能测算"}],
            "total": 1,
            "page": 1,
            "pageSize": 10,
        },
    }
    list_provinces.assert_awaited_once_with(session, scope=scope)
    list_records.assert_awaited_once()
    assert list_records.await_args.kwargs["scope"] is scope
    assert str(list_records.await_args.kwargs["start_date"]) == "2026-08-01"
    assert str(list_records.await_args.kwargs["end_date"]) == "2026-08-31"


@pytest.mark.asyncio
async def test_bootstrap_rejects_an_inverted_date_range_before_queries(monkeypatch):
    scope = UserScope(
        current_user_id="119",
        is_admin=False,
        users=(OrganizationUser(user_id="119", nick_name="北京金租普通账号"),),
    )
    app.dependency_overrides[get_user_scope] = lambda: scope
    app.dependency_overrides[get_db_session] = lambda: object()
    list_provinces = AsyncMock()
    list_records = AsyncMock()
    monkeypatch.setattr(ledger_router._service, "list_provinces", list_provinces)
    monkeypatch.setattr(ledger_router._service, "list_records", list_records)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/ir/calc/ledger/bootstrap",
            params={"start_date": "2026-08-31", "end_date": "2026-08-01"},
            headers=HEADERS,
        )

    assert response.status_code == 400
    assert response.json()["msg"] == "测算时间范围无效：开始日期晚于结束日期"
    list_provinces.assert_not_awaited()
    list_records.assert_not_awaited()
