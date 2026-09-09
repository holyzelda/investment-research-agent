"""e2e（Batch 0.2）：应用可启动、健康检查与响应壳。

用 httpx ASGITransport 在主事件循环内直连 ASGI 应用（异步测试），
避免 Starlette TestClient 后台线程首次加载 greenlet C 扩展时被本机
应用管控策略偶发拦截的问题。
"""
import pytest
from contextlib import asynccontextmanager
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
    return AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"userId": "app-boot-pytest", "username": "__pytest__"},
    )


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
async def test_lifespan_starts_and_stops_policy_ask_warmup(monkeypatch):
    calls = []

    async def fake_init_nacos_config():
        calls.append("nacos-start")

    async def fake_recovery(session):
        calls.append("recovery")
        return 0

    @asynccontextmanager
    async def fake_session():
        yield object()

    def fake_get_sessionmaker():
        return fake_session

    async def fake_stop_warmup():
        calls.append("policy-stop")

    async def fake_dispose_engine():
        calls.append("db-stop")

    async def fake_cleanup_nacos():
        calls.append("nacos-stop")

    monkeypatch.setattr(main, "init_nacos_config", fake_init_nacos_config)
    monkeypatch.setattr(main, "init_engine", lambda: calls.append("db-start"))
    monkeypatch.setattr(main, "get_sessionmaker", fake_get_sessionmaker)
    monkeypatch.setattr(main, "mark_interrupted_generations_failed", fake_recovery)
    monkeypatch.setattr(main, "start_spot_daily_scheduler", lambda: calls.append("scheduler-start"))
    monkeypatch.setattr(main, "stop_spot_daily_scheduler", lambda: calls.append("scheduler-stop"))
    monkeypatch.setattr(main, "start_spot_context_cleanup_scheduler", lambda: calls.append("context-cleanup-start"))
    monkeypatch.setattr(main, "stop_spot_context_cleanup_scheduler", lambda: calls.append("context-cleanup-stop"))
    monkeypatch.setattr(main, "start_policy_ask_warmup", lambda: calls.append("policy-start"))
    monkeypatch.setattr(main, "stop_policy_ask_warmup", fake_stop_warmup)
    monkeypatch.setattr(main, "dispose_engine", fake_dispose_engine)
    monkeypatch.setattr(main, "cleanup_nacos", fake_cleanup_nacos)

    async with main.lifespan(app):
        assert calls[-1] == "policy-start"

    assert calls[-5:] == [
        "scheduler-stop", "context-cleanup-stop", "policy-stop", "db-stop", "nacos-stop",
    ]


@pytest.mark.asyncio
async def test_health_still_ok_with_daily_update_disabled():
    """默认关闭日更时，调度器接入不能影响应用健康检查。"""
    async with await _client() as client:
        assert (await client.get("/health")).status_code == 200
