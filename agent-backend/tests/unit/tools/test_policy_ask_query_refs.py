"""tools.policy_ask 四条检索路径的 references 契约测试。

policy_ask 模块顶层就跑 get_settings() 强校验，所以这里复用 test_policy_ask_config
的 fixture 手法：先 monkeypatch settings 再 import。省页用内联迷你 markdown，
不碰 tools/_cache（运行时缓存，CI 上不存在）。
"""
import importlib
import sys
from types import SimpleNamespace

import pytest


MODULE_NAME = "tools.policy_ask"
DOMAIN = "feishu.example.test"

# 迷你省页：含 frontmatter、速查表、一个带依据行的小节、页尾依据文件清单表。
PROVINCE_PAGE = f"""---
as_of: 2026-07-31
status: 草稿-待人确认
---

## 速查表

| 细分市场 | 可参与 | 备注 |
|---|---|---|
| 容量补偿 | 有条件 | 需独立储能备案 |
| 调频 | 无 | 暂未开放 |

## 容量补偿
- 别名: 容量电价, 容量电费
- 参数: 2026 年标准 0.28 元/kWh
- 依据: token=exampleToken000000000000078 (容量电费实施细则, 2026-01); token=Cap1bTokenDDDDDDDDDDDDDDDDD (独立储能管理通知656号, 2025-09)

## 调频
- 别名: AGC
- 里程报价上限 12 元/MW
- 依据: token=Agc0bTokenBBBBBBBBBBBBBBBBB (调频辅助服务细则, 2025-11)

## 依据文件清单

| 文件 | URL | 类型 |
|---|---|---|
| 容量电费实施细则(试行) | https://{DOMAIN}/file/exampleToken000000000000078 | 容量补偿 |
| 调频辅助服务市场细则 | https://{DOMAIN}/file/Agc0bTokenBBBBBBBBBBBBBBBBB | 调频 |
"""

CROSS_PAGE = f"""---
as_of: 2026-07-20
status: 草稿
---

> 四省现状一句话: 蒙西容量补偿最优。

## 表3 · 关键参数对比

| 省份 | URL | 容量补偿 |
|---|---|---|
| 蒙西 | https://{DOMAIN}/file/MxPageTokenAAAAAAAAAAAAAAA | 0.28 |
| 宁夏 | https://{DOMAIN}/file/NxPageTokenBBBBBBBBBBBBBBB | 无 |
| 甘肃 | https://{DOMAIN}/file/GsPageTokenCCCCCCCCCCCCCCC | 0.15 |
"""


def _settings():
    feishu = SimpleNamespace(
        app_id="cli-test",
        app_secret="secret",
        index_token="IndexPageTokenZZZZZZZZZZZZZ",
        # 省页 token 用真实长度（27 位）：短 token 拼出的 URL 不匹配
        # parse_file_index 的 {15,} 下限，会让测试跑在不真实的分支上。
        province_tokens={
            "蒙西": "MxPageTokenAAAAAAAAAAAAAAA",
            "宁夏": "NxPageTokenBBBBBBBBBBBBBBB",
            "甘肃": "GsPageTokenCCCCCCCCCCCCCCC",
            "陕西": "SxPageTokenDDDDDDDDDDDDDDD",
            "山西": "SaxPageTokenEEEEEEEEEEEEEE",
        },
        cross_province_token="CrossPageTokenYYYYYYYYYYYY",
        domain=DOMAIN,
    )
    llm = SimpleNamespace(base_url="https://llm.example.test", api_key="llm-key", model="test-model")
    anysearch = SimpleNamespace(api_key="", tavily_api_key="")
    base = SimpleNamespace(token="", table="")
    return SimpleNamespace(
        policy_ask=SimpleNamespace(feishu=feishu, llm=llm, anysearch=anysearch, base=base)
    )


@pytest.fixture
def policy_ask(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.get_settings", lambda: _settings())
    sys.modules.pop(MODULE_NAME, None)
    module = importlib.import_module(MODULE_NAME)
    # 省页按 token 返回不同内容：跨省页与省页结构不同。
    monkeypatch.setattr(module, "_download", lambda token, no_cache=False: token)
    # 各省页的政策文件 token 互不相同，跨省下钻才验得出"每个省都取到了自己的源文件"；
    # 若所有省页内容一样，ReferenceCollector 会按 URL 去重成一份，测不出下钻。
    monkeypatch.setattr(
        module,
        "_read",
        lambda path: CROSS_PAGE if path == module.CROSS_PROVINCE_TOKEN
        else PROVINCE_PAGE.replace("0bToken", f"0b{path[:2]}Token"),
    )
    yield module
    sys.modules.pop(MODULE_NAME, None)


def _urls(result):
    return [item["url"] for item in result["references"]]


# --- 路径 A：wiki 命中 section ---


def test_wiki_section_hit_builds_references_with_titles(policy_ask):
    result = policy_ask.query("蒙西容量补偿是多少", allow_web=False)

    assert result["source_type"] == "wiki"
    assert result["province"] == "蒙西"
    titles = [item["title"] for item in result["references"]]
    assert "容量电费实施细则(试行)" in titles, "清单表标题应覆盖依据行标题"
    assert all(item["type"] == "wiki" for item in result["references"])
    # sources 与 references 顺序严格一致，是同一份数据的两种形状
    assert result["sources"] == _urls(result)


def test_wiki_section_context_carries_marker_and_legend(policy_ask):
    result = policy_ask.query("蒙西容量补偿是多少", allow_web=False)

    assert "(可引用: [1]" in result["context"]
    legend_start = result["context"].index("--- 可引用来源编号 ---")
    assert "[1] 容量电费实施细则(试行)" in result["context"][legend_start:]


def test_wiki_legend_survives_context_truncation(policy_ask, monkeypatch):
    """图例必须拼在截断之后——否则模型完全看不到编号含义。"""
    monkeypatch.setattr(policy_ask, "_read", lambda path: PROVINCE_PAGE.replace(
        "- 参数: 2026 年标准 0.28 元/kWh", "- 参数: " + "占位数据。" * 900
    ))

    result = policy_ask.query("蒙西容量补偿是多少", allow_web=False)

    assert "(上下文过长已截断)" in result["context"]
    assert "--- 可引用来源编号 ---" in result["context"]


def test_wiki_excludes_province_page_tokens_from_references(policy_ask):
    """省页/索引页自身是知识库骨架，不该出现在用户可见的来源列表里。"""
    result = policy_ask.query("蒙西容量补偿是多少", allow_web=False)

    tokens = {item["token"] for item in result["references"]}
    assert tokens.isdisjoint(set(policy_ask.PROVINCES.values()) | {
        policy_ask.INDEX_TOKEN, policy_ask.CROSS_PROVINCE_TOKEN
    })


# --- 路径 B：速查表兜底 ---


def test_quick_table_fallback_still_produces_references(policy_ask):
    """问题只命中速查表行、没命中 section 时也要给出来源。"""
    result = policy_ask.query("蒙西调频能参与吗", allow_web=False)

    assert result["source_type"] == "wiki"
    assert result["references"], "速查表兜底路径必须给出来源，否则用户无从验证"
    assert result["sources"] == _urls(result)


# --- 路径 C：跨省对比 ---


def test_cross_province_drills_down_to_source_files_not_wiki_pages(policy_ask):
    """跨省页上挂的是各省 wiki 页（模型用的骨架），用户要的是骨架背后的政策原文。"""
    result = policy_ask.query("蒙西和宁夏哪个省更适合投储能", allow_web=False)

    assert result["province"] == "跨省对比"
    tokens = {item["token"] for item in result["references"]}
    assert tokens.isdisjoint(set(policy_ask.PROVINCES.values()) | {
        policy_ask.INDEX_TOKEN, policy_ask.CROSS_PROVINCE_TOKEN
    }), "省页 token 不该出现在来源里"
    # 标题带省名前缀，用户才分得清同名文件属于哪个省
    titles = [item["title"] for item in result["references"]]
    assert "蒙西·容量电费实施细则(试行)" in titles
    assert "宁夏·调频辅助服务市场细则" in titles
    assert result["sources"] == _urls(result)
    assert "--- 可引用来源编号 ---" in result["context"]


def test_cross_province_survives_unreachable_province_page(policy_ask, monkeypatch):
    """某个省页下不下来时，跨省结论照给——来源少一个省，不是整体报错。"""
    original_read = policy_ask._read

    def flaky_read(path):
        if path == policy_ask.PROVINCES["宁夏"]:
            raise RuntimeError("下载失败")
        return original_read(path)

    monkeypatch.setattr(policy_ask, "_read", flaky_read)

    result = policy_ask.query("蒙西和宁夏哪个省更适合投储能", allow_web=False)

    titles = [item["title"] for item in result["references"]]
    assert any(title.startswith("蒙西·") for title in titles)
    assert not any(title.startswith("宁夏·") for title in titles)


# --- 路径 D：联网 ---


def test_web_fallback_numbers_results_and_shares_collector_across_queries(policy_ask, monkeypatch):
    pages = {
        "https://a.test": "甲页",
        "https://b.test": "乙页",
    }

    def fake_search(query_text, max_results=5, collector=None):
        lines = []
        for url, title in pages.items():
            marker = policy_ask._register_web_result(collector, url, title)
            lines.append(f"- {marker}{title}: 正文")
        return "\n".join(lines), list(pages)

    monkeypatch.setattr(policy_ask, "TAVILY_API_KEY", "tvly-key")
    monkeypatch.setattr(policy_ask, "_tavily_search", fake_search)

    result = policy_ask._web_fallback("蒙西 2030 年氢能规划装机", "蒙西", "2026-07-31", "草稿")

    assert result["source_type"] == "web"
    # 两个 query 检索到同样的网页，编号不能重复分配
    assert [item["index"] for item in result["references"]] == [1, 2]
    assert [item["type"] for item in result["references"]] == ["web", "web"]
    body, legend = result["context"].split("--- 可引用来源编号 ---")
    assert body.count("[1] 甲页") == 2, "两次检索命中同一网页，编号必须复用"
    assert legend.count("[1] 甲页") == 1
    assert result["sources"] == _urls(result)


def test_llm_general_path_has_no_references(policy_ask, monkeypatch):
    """通用知识兜底没有检索来源，references 必须为空而不是缺键。"""
    monkeypatch.setattr(policy_ask, "_web_fallback", lambda *a, **kw: None)

    result = policy_ask.query("请介绍一下期权定价模型", allow_web=True)

    assert result["source_type"] == "llm_general"
    assert result["references"] == []
    assert result["sources"] == []


# --- ask()：重编号与落库 ---


def test_ask_renumbers_answer_and_keeps_only_cited_sources(policy_ask, monkeypatch):
    monkeypatch.setattr(
        policy_ask, "_llm_summarize",
        lambda question, context, as_of, status, on_token=None: "结论见细则[2]。补充[2]。",
    )
    logged = {}
    monkeypatch.setattr(
        policy_ask, "_log_to_base",
        lambda q, a, p, ao, st, ctx: logged.update(answer=a),
    )

    result = policy_ask.ask("蒙西容量补偿是多少", allow_web=False)

    assert result["answer"] == "结论见细则[1]。补充[1]。"
    assert len(result["references"]) == 1
    assert result["references"][0]["index"] == 1
    # ask() 只对外暴露结论与源文件，检索元信息不再随返回值下发
    assert set(result) == {"answer", "references"}
    assert logged["answer"] == result["answer"], "落库必须用重编号后的答案"


def test_ask_keeps_all_sources_when_model_ignores_citations(policy_ask, monkeypatch):
    """模型不配合输出角标时，来源列表绝不能凭空消失。"""
    monkeypatch.setattr(
        policy_ask, "_llm_summarize",
        lambda question, context, as_of, status, on_token=None: "2026 年标准 0.28 元/kWh。",
    )
    monkeypatch.setattr(policy_ask, "_log_to_base", lambda *a, **kw: None)

    result = policy_ask.ask("蒙西容量补偿是多少", allow_web=False)

    assert result["answer"] == "2026 年标准 0.28 元/kWh。"
    assert result["references"], "无角标时应全量保留来源"


def test_ask_general_path_returns_answer_without_citations(policy_ask, monkeypatch):
    monkeypatch.setattr(policy_ask, "_web_fallback", lambda *a, **kw: None)
    monkeypatch.setattr(
        policy_ask, "_llm_summarize_general", lambda question, on_token=None: "方向性回答。"
    )
    monkeypatch.setattr(policy_ask, "_log_to_base", lambda *a, **kw: None)

    result = policy_ask.ask("请介绍一下期权定价模型", allow_web=True)

    assert result["answer"] == "方向性回答。"
    assert result["references"] == []
    assert set(result) == {"answer", "references"}


def test_ask_still_logs_retrieval_metadata_to_base(policy_ask, monkeypatch):
    """省份与时效不再对外返回，但必须继续落飞书评估表，否则问答质量看板会失真。"""
    monkeypatch.setattr(
        policy_ask, "_llm_summarize",
        lambda question, context, as_of, status, on_token=None: "结论见细则[1]。",
    )
    logged = {}
    monkeypatch.setattr(
        policy_ask, "_log_to_base",
        lambda q, a, p, ao, st, ctx: logged.update(province=p, as_of=ao, status=st),
    )

    policy_ask.ask("蒙西容量补偿是多少", allow_web=False)

    assert logged["province"] == "蒙西"
    assert logged["as_of"] == "2026-07-31"
    assert logged["status"] == "草稿-待人确认"


def test_fallback_context_strips_citation_markup(policy_ask):
    """LLM 挂掉时 context 会被当答案返回，编号提示与图例不能漏给用户。"""
    context = "[蒙西·容量补偿] (可引用: [1])\n- 标准 0.28 元/kWh\n\n--- 可引用来源编号 ---\n[1] 某细则"

    cleaned = policy_ask._fallback_context(context)

    assert "可引用" not in cleaned
    assert "某细则" not in cleaned
    assert "0.28 元/kWh" in cleaned
