from app.modules.policy_market.infrastructure.policy_ask_executor import PolicyAskExecutorAdapter


def test_executor_maps_tools_answer_to_domain(monkeypatch):
    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.policy_ask.ask",
        lambda question: {
            "answer": "宁夏结论",
            "sources": ["https://example.test/source"],
            "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
            "reminders": ["关注更新"],
        },
    )

    result = PolicyAskExecutorAdapter().ask("宁夏政策")

    assert result.answer == "宁夏结论"
    assert result.province_code == "宁夏"
    assert result.source_data == {
        "sources": ["https://example.test/source"],
        "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
        "reminders": ["关注更新"],
    }
