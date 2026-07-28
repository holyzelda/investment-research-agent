import json

import httpx
import pytest

from app.core.config.settings import MiddlePlatformConfig
from app.core.exceptions import ValidationException
from app.modules.middle_platform.infrastructure.http_client import MiddlePlatformHttpClient


@pytest.mark.asyncio
async def test_model_pool_client_sends_bearer_payload_and_returns_direct_text(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={
            "code": 200,
            "msg": "操作成功",
            "data": {"content": "  冻结正文  "},
        })

    transport = httpx.MockTransport(handler)

    class Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    client = MiddlePlatformHttpClient(MiddlePlatformConfig(
        report_model_url="http://internal-2-58.example.invalid:8180/gateway/agent-middle/api/v1/model-pool/chat",
    ))
    text = await client.chat_report_model(
        access_token="token-1",
        payload={"source_app_id": "ir-agent", "message": "冻结资料"},
    )

    assert text == "冻结正文"
    assert seen["url"] == "http://internal-2-58.example.invalid:8180/gateway/agent-middle/api/v1/model-pool/chat"
    assert seen["headers"]["authorization"] == "Bearer token-1"
    assert seen["payload"] == {"source_app_id": "ir-agent", "message": "冻结资料"}


@pytest.mark.asyncio
async def test_model_pool_client_rejects_empty_or_invalid_application_response(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, json={"code": 200, "data": {"content": " "}}
    ))

    class Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    client = MiddlePlatformHttpClient(MiddlePlatformConfig())

    with pytest.raises(ValidationException, match="无有效正文"):
        await client.chat_report_model(access_token="token-1", payload={})
