import types

import pytest

from app.modules.policy_market.infrastructure.policy_ask_executor import PolicyAskExecutorAdapter


@pytest.mark.asyncio
async def test_executor_waits_for_loader_and_maps_tools_answer(monkeypatch):
    module = types.SimpleNamespace(
        ask=lambda question: {
            "answer": "宁夏结论",
            "sources": ["https://example.test/source"],
            "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
            "reminders": ["关注更新"],
        }
    )

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    result = await PolicyAskExecutorAdapter().ask("宁夏政策")

    assert result.answer == "宁夏结论"
    assert result.province_code == "宁夏"
    assert result.source_data == {
        "sources": ["https://example.test/source"],
        "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
        "reminders": ["关注更新"],
    }
