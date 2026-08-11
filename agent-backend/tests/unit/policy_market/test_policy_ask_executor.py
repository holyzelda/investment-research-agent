import types

import pytest

from app.modules.policy_market.infrastructure.policy_ask_executor import (
    PolicyAskExecutorAdapter,
    PolicySourceFileAdapter,
)


@pytest.mark.asyncio
async def test_executor_waits_for_loader_and_maps_tools_answer(monkeypatch):
    # 契约以 tools.policy_ask._finalize() 的返回值为准：只有 answer 与 references，
    # 省份/时效/核验状态属于检索元信息，不再对外返回。
    module = types.SimpleNamespace(
        ask=lambda question: {
            "answer": "宁夏结论[1]。",
            "references": [
                {
                    "index": 1,
                    "title": "宁夏调频细则",
                    "url": "https://example.test/source",
                    "token": "NxTokenAAAAAAAAAAAAAAAAAAAA",
                    "type": "wiki",
                }
            ],
        }
    )

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    result = await PolicyAskExecutorAdapter().ask("宁夏政策")

    assert result.answer == "宁夏结论[1]。"
    assert result.province_code is None
    assert result.source_data == {
        "references": [
            {
                "index": 1,
                "title": "宁夏调频细则",
                "url": "https://example.test/source",
                "token": "NxTokenAAAAAAAAAAAAAAAAAAAA",
                "type": "wiki",
            }
        ],
    }


@pytest.mark.asyncio
async def test_executor_tolerates_missing_reference_fields(monkeypatch):
    """llm_general 兜底路径没有任何来源，references 必须落到空列表而不是抛 KeyError。"""
    module = types.SimpleNamespace(ask=lambda question: {"answer": "方向性回答。"})

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    result = await PolicyAskExecutorAdapter().ask("期权定价")

    assert result.province_code is None
    assert result.source_data == {"references": []}


@pytest.mark.asyncio
async def test_source_file_adapter_maps_tools_tuple(monkeypatch):
    module = types.SimpleNamespace(
        fetch_source_file=lambda token: (b"%PDF-1.7", "容量电费.pdf", "application/pdf")
    )

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    source = await PolicySourceFileAdapter().fetch("exampleToken000000000000078")

    assert source.content == b"%PDF-1.7"
    assert source.filename == "容量电费.pdf"
    assert source.content_type == "application/pdf"


@pytest.mark.asyncio
async def test_source_file_adapter_returns_none_for_token_outside_whitelist(monkeypatch):
    """白名单校验在 tools 层；适配器要如实把 None 透传上去，由路由转 404。"""
    module = types.SimpleNamespace(fetch_source_file=lambda token: None)

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    assert await PolicySourceFileAdapter().fetch("AnyOtherFeishuTokenXXXXXXXX") is None


@pytest.mark.asyncio
async def test_source_file_adapter_defaults_missing_content_type(monkeypatch):
    module = types.SimpleNamespace(fetch_source_file=lambda token: (b"data", "rule", ""))

    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )

    source = await PolicySourceFileAdapter().fetch("exampleToken000000000000078")

    assert source.content_type == "application/octet-stream"
