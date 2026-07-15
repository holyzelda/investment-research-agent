"""e2e（Batch 1）：平台身份中间件——读 header 注入 request.state，不做 token 校验。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_reads_identity_from_headers():
    async with await _client() as client:
        # 注意：HTTP header 仅允许 ASCII。若平台需在 header 传中文用户名，
        # 须由平台侧 URL-encode / Base64 编码（属平台对接约定，PRD 挂账 #8）。
        resp = await client.get("/ir/me", headers={"X-User-Id": "u123", "X-User-Name": "zhangsan"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["userId"] == "u123"
        assert data["username"] == "zhangsan"


@pytest.mark.asyncio
async def test_anonymous_fallback_when_header_missing():
    async with await _client() as client:
        resp = await client.get("/ir/me")
        # 允许匿名（开发态）：不返回 401，降级为匿名占位
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["userId"] == "0"
        assert data["username"] == "访客"


@pytest.mark.asyncio
async def test_no_token_validation_no_401():
    # 携带任意/无 token 均不触发 401（本系统不做登录校验）
    async with await _client() as client:
        resp = await client.get("/ir/me", headers={"Authorization": "Bearer whatever"})
        assert resp.status_code == 200
        assert resp.json()["code"] == 200
