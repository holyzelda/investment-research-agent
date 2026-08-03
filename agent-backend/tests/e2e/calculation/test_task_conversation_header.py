"""测算任务会话 Header 接口契约测试。"""
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import register_exception_handlers
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.interface import router as task_router
from app.modules.platform_access.interface.middleware import PlatformIdentityMiddleware


class _TaskService:
    def __init__(self):
        self.conversation_id = object()

    async def create_and_run(self, _session, **kwargs):
        self.conversation_id = kwargs["conversation_id"]
        return {
            "conversationId": self.conversation_id,
            "taskId": 1,
            "version": "V1",
            "status": "completed",
        }


async def _session_override():
    yield object()


@pytest.fixture
async def client(monkeypatch):
    service = _TaskService()
    monkeypatch.setattr(task_router, "build_task_service", lambda: service)
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(PlatformIdentityMiddleware)
    app.include_router(task_router.router)
    app.dependency_overrides[get_db_session] = _session_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"userId": "u-1", "username": "tester"},
    ) as http_client:
        yield http_client, service


@pytest.mark.asyncio
async def test_standard_conversation_header_is_forwarded(client):
    http_client, service = client
    conversation_id = str(uuid4())

    response = await http_client.post(
        "/ir/calc/tasks",
        headers={"X-IR-Conversation-Id": conversation_id},
        json={"province": "甘肃", "capacity_mwh": 800, "power_mw": 200},
    )

    assert response.status_code == 200
    assert service.conversation_id == conversation_id
    assert response.json()["data"]["conversationId"] == conversation_id


@pytest.mark.asyncio
async def test_legacy_underscore_header_is_not_read(client):
    http_client, service = client

    response = await http_client.post(
        "/ir/calc/tasks",
        headers={"conversation_id": str(uuid4())},
        json={"province": "甘肃", "capacity_mwh": 800, "power_mw": 200},
    )

    assert response.status_code == 200
    assert service.conversation_id is None


@pytest.mark.asyncio
async def test_invalid_standard_conversation_header_returns_400(client):
    http_client, service = client

    response = await http_client.post(
        "/ir/calc/tasks",
        headers={"X-IR-Conversation-Id": "not-a-uuid"},
        json={"province": "甘肃", "capacity_mwh": 800, "power_mw": 200},
    )

    assert response.status_code == 400
    assert response.json() == {"code": 400, "msg": "conversation_id 格式无效", "data": None}
    assert not isinstance(service.conversation_id, str)
