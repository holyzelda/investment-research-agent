"""e2e（Batch 1）：平台身份中间件在固定接口 Token 通过后读取身份 header。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config.settings import reload_settings
from app.main import app


@pytest.fixture(autouse=True)
def fixed_token(monkeypatch):
    monkeypatch.setenv("IR_API_TOKEN", "test-fixed-token")
    reload_settings()
    yield
    monkeypatch.delenv("IR_API_TOKEN", raising=False)
    reload_settings()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _headers(**headers: str) -> dict[str, str]:
    return {"Authorization": "Bearer test-fixed-token", **headers}


@pytest.mark.asyncio
async def test_reads_identity_from_headers():
    async with await _client() as client:
        # 注意：HTTP header 仅允许 ASCII。若平台需在 header 传中文用户名，
        # 须由平台侧 URL-encode / Base64 编码（属平台对接约定，PRD 挂账 #8）。
        resp = await client.get("/ir/me", headers=_headers(**{"X-User-Id": "u123", "X-User-Name": "zhangsan"}))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["userId"] == "u123"
        assert data["username"] == "zhangsan"


@pytest.mark.asyncio
async def test_anonymous_fallback_when_header_missing():
    async with await _client() as client:
        resp = await client.get("/ir/me", headers=_headers())
        # 允许匿名（开发态）：不返回 401，降级为匿名占位
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["userId"] == "0"
        assert data["username"] == "访客"


@pytest.mark.asyncio
async def test_valid_fixed_token_allows_platform_identity_processing():
    async with await _client() as client:
        resp = await client.get("/ir/me", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["code"] == 200
