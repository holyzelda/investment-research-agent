"""测算任务会话 Header 接口契约测试。"""
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import register_exception_handlers
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.trial_quota.interface.deps import get_trial_role_service
from tests.conftest import FakeTrialRole
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


class _FakeSession:
    """支持 create_task 内归属校验 + 同会话规模补全的最小 mock。

    create_task 在 X-IR-Conversation-Id 存在时会先做归属校验
    （require_active_conversation），再查最近成功版本冻结入参
    （_latest_frozen_input）；此处 mock 会话对归属查询返回本用户会话，
    对冻结入参查询返回空结果，补全逻辑不生效。
    """

    def __init__(self, conversation=None):
        self._conversation = conversation
        self._calls = 0
        self._scalar = None

    async def execute(self, *args, **kwargs):
        # 第一次 execute 是归属校验（返回本用户会话），后续是冻结入参查询（返回空）。
        self._calls += 1
        if self._calls == 1 and self._conversation is not None:
            return _FakeResult(self._conversation)
        return _FakeResult(self._scalar)

    async def scalar(self, *args, **kwargs):
        return self._scalar


class _FakeResult:
    def __init__(self, scalar):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return _FakeScalars([self._scalar] if self._scalar is not None else [])

    def first(self):
        return self._scalar


class _FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


def _session_override(conversation=None):
    """返回可注入的依赖函数：归属校验返回该会话，冻结入参查询返回空。"""
    async def _override():
        yield _FakeSession(conversation=conversation)
    return _override


@pytest.fixture
async def client(monkeypatch):
    service = _TaskService()
    monkeypatch.setattr(task_router, "build_task_service", lambda: service)
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(PlatformIdentityMiddleware)
    app.include_router(task_router.router)
    # 归属校验用的本用户会话占位（仅需 id 属性，service 收到的是完整 conversation_id）。
    conversation_id = str(uuid4())
    app.dependency_overrides[get_db_session] = _session_override(conversation_id)
    app.dependency_overrides[get_trial_role_service] = lambda: FakeTrialRole(result=False)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"userId": "u-1", "username": "tester"},
    ) as http_client:
        yield http_client, service, conversation_id


@pytest.mark.asyncio
async def test_standard_conversation_header_is_forwarded(client):
    http_client, service, conversation_id = client

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
    http_client, service, _ = client

    response = await http_client.post(
        "/ir/calc/tasks",
        headers={"conversation_id": str(uuid4())},
        json={"province": "甘肃", "capacity_mwh": 800, "power_mw": 200},
    )

    assert response.status_code == 200
    assert service.conversation_id is None


@pytest.mark.asyncio
async def test_invalid_standard_conversation_header_returns_400(client):
    http_client, service, _ = client

    response = await http_client.post(
        "/ir/calc/tasks",
        headers={"X-IR-Conversation-Id": "not-a-uuid"},
        json={"province": "甘肃", "capacity_mwh": 800, "power_mw": 200},
    )

    assert response.status_code == 400
    assert response.json() == {"code": 400, "msg": "conversation_id 格式无效", "data": None}
    assert not isinstance(service.conversation_id, str)
