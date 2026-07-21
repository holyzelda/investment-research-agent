"""e2e（Batch 0.2）：应用可启动、健康检查与响应壳。

用 httpx ASGITransport 在主事件循环内直连 ASGI 应用（异步测试），
避免 Starlette TestClient 后台线程首次加载 greenlet C 扩展时被本机
应用管控策略偶发拦截的问题。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app import main

app = main.app


def test_main_owns_application_factory_and_lifecycle():
    assert callable(main.create_app)
    assert callable(main.lifespan)
    assert callable(main.register_routers)
    assert {"/health", "/ir/me", "/ir/calc/param-dict"}.issubset(
        {route.path for route in app.routes}
    )


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_returns_envelope():
    async with await _client() as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["status"] == "up"


@pytest.mark.asyncio
async def test_docs_available():
    async with await _client() as client:
        assert (await client.get("/docs")).status_code == 200
        assert (await client.get("/openapi.json")).status_code == 200


@pytest.mark.asyncio
async def test_health_still_ok_with_daily_update_disabled():
    """默认关闭日更时，调度器接入不能影响应用健康检查。"""
    async with await _client() as client:
        assert (await client.get("/health")).status_code == 200
