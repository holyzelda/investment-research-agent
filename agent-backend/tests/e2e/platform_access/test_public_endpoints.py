"""e2e coverage for routes that do not require a platform identity."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/health"])
async def test_allows_public_endpoints_without_platform_identity(path):
    async with await _client() as client:
        response = await client.get(path)

    assert response.status_code == 200
