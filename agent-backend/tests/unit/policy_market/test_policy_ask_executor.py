import asyncio
import threading
import types

import pytest

from app.modules.policy_market.infrastructure import policy_ask_executor
from app.modules.policy_market.infrastructure.policy_ask_executor import (
    PolicyAskExecutorAdapter,
    PolicySourceFileAdapter,
    stop_source_prefetch,
)


async def _drain_prefetch():
    """等在途预取跑完。生产上是 fire-and-forget，测试里必须显式收口。"""
    while policy_ask_executor._prefetch_tasks:
        await asyncio.gather(*list(policy_ask_executor._prefetch_tasks), return_exceptions=True)


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
    await _drain_prefetch()  # 这条来源带 wiki token，会触发预取，收口避免泄漏到后续用例

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


# --- 答案生成后的源文件预取 ---


def _module_with_refs(references, fetch=None):
    fetched = []

    def default_fetch(token):
        fetched.append(token)
        return (b"data", "f", "application/pdf")

    module = types.SimpleNamespace(
        ask=lambda question: {"answer": "结论[1]。", "references": references},
        fetch_source_file=fetch or default_fetch,
    )
    return module, fetched


def _patch_loader(monkeypatch, module):
    async def fake_get_module():
        return module

    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.get_policy_ask_module",
        fake_get_module,
    )


@pytest.mark.asyncio
async def test_ask_prefetches_wiki_sources_in_background(monkeypatch):
    """用户读答案的几十秒里把源文件焐进磁盘缓存，点开来源时才不用干等飞书。"""
    module, fetched = _module_with_refs([
        {"index": 1, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"},
        {"index": 2, "type": "wiki", "token": "TokenBBBBBBBBBBBBBBBBBBBBBB"},
    ])
    _patch_loader(monkeypatch, module)

    result = await PolicyAskExecutorAdapter().ask("蒙西容量补偿")
    await _drain_prefetch()

    assert result.answer == "结论[1]。"
    assert fetched == ["TokenAAAAAAAAAAAAAAAAAAAAAA", "TokenBBBBBBBBBBBBBBBBBBBBBB"]


@pytest.mark.asyncio
async def test_ask_skips_web_sources_and_blank_tokens(monkeypatch):
    """web 类型是公网链接，前端直跳不走代理；预取它纯属浪费飞书调用。"""
    module, fetched = _module_with_refs([
        {"index": 1, "type": "web", "token": "", "url": "https://example.test/news"},
        {"index": 2, "type": "web", "token": "ShouldNotBeFetchedAAAAAAAAA"},
        {"index": 3, "type": "wiki", "token": ""},
        {"index": 4, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"},
    ])
    _patch_loader(monkeypatch, module)

    await PolicyAskExecutorAdapter().ask("最新新闻")
    await _drain_prefetch()

    assert fetched == ["TokenAAAAAAAAAAAAAAAAAAAAAA"]


@pytest.mark.asyncio
async def test_ask_deduplicates_prefetch_tokens(monkeypatch):
    """同一份文件被多处引用时只下一次。"""
    module, fetched = _module_with_refs([
        {"index": 1, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"},
        {"index": 2, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"},
    ])
    _patch_loader(monkeypatch, module)

    await PolicyAskExecutorAdapter().ask("蒙西容量补偿")
    await _drain_prefetch()

    assert fetched == ["TokenAAAAAAAAAAAAAAAAAAAAAA"]


@pytest.mark.asyncio
async def test_prefetch_failure_never_breaks_the_answer(monkeypatch):
    """预取失败只是没加速，已经生成好的答案必须原样返回。"""
    def boom(token):
        raise RuntimeError("飞书下载失败")

    module, _ = _module_with_refs(
        [{"index": 1, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"}], fetch=boom
    )
    _patch_loader(monkeypatch, module)

    result = await PolicyAskExecutorAdapter().ask("蒙西容量补偿")
    await _drain_prefetch()

    assert result.answer == "结论[1]。"
    assert result.source_data["references"][0]["token"] == "TokenAAAAAAAAAAAAAAAAAAAAAA"


@pytest.mark.asyncio
async def test_ask_returns_before_prefetch_completes(monkeypatch):
    """预取必须是 fire-and-forget：串行下载几个 PDF 要十几秒，不能让用户等。"""
    release = threading.Event()

    def slow_fetch(token):
        release.wait(5)  # 在工作线程里阻塞，不影响事件循环
        return (b"data", "f", "application/pdf")

    module, _ = _module_with_refs(
        [{"index": 1, "type": "wiki", "token": "TokenAAAAAAAAAAAAAAAAAAAAAA"}], fetch=slow_fetch
    )
    _patch_loader(monkeypatch, module)

    result = await PolicyAskExecutorAdapter().ask("蒙西容量补偿")

    assert result.answer == "结论[1]。", "预取还没跑完，答案就该返回了"
    assert policy_ask_executor._prefetch_tasks, "预取任务应在途"
    release.set()
    await _drain_prefetch()


@pytest.mark.asyncio
async def test_stop_source_prefetch_cancels_inflight_tasks(monkeypatch):
    """应用关闭时取消在途预取，别让事件循环退出时留下未完成任务。"""
    async def never_ends():
        await asyncio.Event().wait()

    task = asyncio.create_task(never_ends())
    policy_ask_executor._prefetch_tasks.add(task)
    task.add_done_callback(policy_ask_executor._prefetch_tasks.discard)

    await stop_source_prefetch()

    assert task.cancelled()
    assert not policy_ask_executor._prefetch_tasks
