import asyncio
import types

import pytest

from app.modules.policy_market.infrastructure import policy_ask_loader


@pytest.fixture(autouse=True)
async def reset_warmup_task():
    await policy_ask_loader.stop_policy_ask_warmup()
    yield
    await policy_ask_loader.stop_policy_ask_warmup()


@pytest.mark.asyncio
async def test_warmup_is_shared_and_getter_waits_for_loaded_module(monkeypatch):
    loaded = types.ModuleType("tools.policy_ask")
    calls = []

    def fake_import(name):
        calls.append(name)
        return loaded

    monkeypatch.setattr(policy_ask_loader.importlib, "import_module", fake_import)

    first = policy_ask_loader.start_policy_ask_warmup()
    second = policy_ask_loader.start_policy_ask_warmup()

    assert first is second
    assert await policy_ask_loader.get_policy_ask_module() is loaded
    assert calls == ["tools.policy_ask"]


@pytest.mark.asyncio
async def test_getter_starts_warmup_when_lifespan_has_not_started_it(monkeypatch):
    loaded = types.ModuleType("tools.policy_ask")
    monkeypatch.setattr(policy_ask_loader.importlib, "import_module", lambda name: loaded)

    assert await policy_ask_loader.get_policy_ask_module() is loaded


@pytest.mark.asyncio
async def test_getter_propagates_background_import_failure(monkeypatch):
    def fail_import(name):
        raise ImportError("sdk unavailable")

    monkeypatch.setattr(policy_ask_loader.importlib, "import_module", fail_import)

    policy_ask_loader.start_policy_ask_warmup()

    with pytest.raises(ImportError, match="sdk unavailable"):
        await policy_ask_loader.get_policy_ask_module()


@pytest.mark.asyncio
async def test_stop_cancels_pending_warmup(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def delayed_import():
        started.set()
        await release.wait()
        return types.ModuleType("tools.policy_ask")

    monkeypatch.setattr(policy_ask_loader, "_import_policy_ask", delayed_import)

    task = policy_ask_loader.start_policy_ask_warmup()
    await started.wait()
    await policy_ask_loader.stop_policy_ask_warmup()

    assert task.cancelled()
