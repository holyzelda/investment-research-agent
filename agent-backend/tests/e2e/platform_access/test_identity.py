"""e2e：平台身份中间件从固定 Header 读取 ecenter 身份。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_reads_and_decodes_identity_from_headers():
    async with await _client() as client:
        resp = await client.get(
            "/ir/me",
            headers={"userId": "u123", "username": "%E5%BC%A0%E4%B8%89"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["userId"] == "u123"
    assert data["username"] == "张三"


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"userId": "u123"}, {"username": "zhangsan"}])
async def test_rejects_incomplete_identity_headers(headers):
    async with await _client() as client:
        resp = await client.get("/ir/me", headers=headers)

    assert resp.status_code == 401
    assert resp.json() == {"code": 401, "msg": "未获取到平台用户身份", "data": None}
