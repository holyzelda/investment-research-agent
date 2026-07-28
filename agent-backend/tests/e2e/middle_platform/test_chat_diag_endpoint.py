"""中台对话 SSE 接口响应契约测试。"""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.session import get_db_session
from app.modules.middle_platform.application.chat_proxy_service import ChatProxyService
from app.modules.middle_platform.interface.router import router
from app.modules.platform_access.interface.middleware import PlatformIdentityMiddleware


async def _session_override():
    yield object()


async def _chunks():
    yield b'event: thinking\ndata: {"data":{"text":"first"}}\n\n'


@pytest.mark.asyncio
async def test_chat_diag_disables_sse_response_buffering(monkeypatch):
    conversation_id = uuid4()

    async def fake_start_chat(self, **kwargs):
        return SimpleNamespace(conversation_id=conversation_id, chunks=_chunks())

    monkeypatch.setattr(ChatProxyService, "start_chat", fake_start_chat)
    app = FastAPI()
    app.add_middleware(PlatformIdentityMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_db_session] = _session_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/ir/chat/diag",
            headers={"userId": "u-1", "username": "tester"},
            json={"message": "分析项目"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-ir-conversation-id"] == str(conversation_id)
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
