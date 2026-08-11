"""tools.policy_refs 纯函数单测。

该模块零配置依赖，可直接 import（对比 tools.policy_ask 需要完整飞书/LLM 配置）。
输入一律用内联 markdown 片段，不读 tools/_cache/*.md —— 那是运行时缓存，
CI 上不存在且 24 小时就被覆写。
"""
from tools.policy_refs import (
    ReferenceCollector,
    parse_file_index,
    renumber_citations,
    strip_context_markup,
)


DOMAIN = "feishu.example.test"


def _url(token):
    return f"https://{DOMAIN}/file/{token}"


# --- parse_file_index: 依据文件清单表 ---


def test_index_table_three_columns():
    text = f"""
| 文件 | URL | 类型 |
|---|---|---|
| 规则体系(269页, 2024-12) | {_url('exampleToken000000000000002')} | 权威母文件 |
"""
    index = parse_file_index(text, DOMAIN)

    assert index["exampleToken000000000000002"] == {
        "token": "exampleToken000000000000002",
        "title": "规则体系(269页, 2024-12)",
        "url": _url("exampleToken000000000000002"),
    }


def test_index_table_four_columns_strips_bold_and_star():
    text = f"""
| 文件 | URL | 类型 | 状态 |
|---|---|---|---|
| **★容量电费实施细则(试行)** | {_url('exampleToken000000000000081')} | 容量补偿 | 已精读 |
"""
    index = parse_file_index(text, DOMAIN)

    assert index["exampleToken000000000000081"]["title"] == "容量电费实施细则(试行)"


def test_index_table_row_with_two_urls_maps_both_tokens_to_same_title():
    a, b = "exampleToken000000000000082", "exampleToken000000000000083"
    text = f"| 不平衡资金管理办法 | {_url(a)} + {_url(b)} | 结算 |"

    index = parse_file_index(text, DOMAIN)

    assert index[a]["title"] == "不平衡资金管理办法"
    assert index[b]["title"] == "不平衡资金管理办法"


def test_index_table_skips_header_and_separator_rows():
    text = f"""
| 文件 | URL | 类型 |
|---|---|---|
| 真实文件 | {_url('RealTokenAAAAAAAAAAAAAAAAAA')} | 类型 |
"""
    index = parse_file_index(text, DOMAIN)

    assert list(index) == ["RealTokenAAAAAAAAAAAAAAAAAA"]


# --- parse_file_index: 依据行兜底 ---


def test_evidence_line_single_token_takes_trailing_paren_title():
    text = "- 依据: token=exampleToken000000000000003 (中长期交易方案2025年版, .doc转PDF精读, 395行)"

    index = parse_file_index(text, DOMAIN)

    assert index["exampleToken000000000000003"]["title"] == "中长期交易方案2025年版"
    assert index["exampleToken000000000000003"]["url"] == _url("exampleToken000000000000003")


def test_evidence_line_semicolon_separated_tokens_get_own_titles():
    text = (
        "- 依据: token=exampleToken000000000000004 (2026中长期交易通知752号, 2025-12-12); "
        "token=exampleToken000000000000005 第13-31页 (要点解析, 2025-02)"
    )

    index = parse_file_index(text, DOMAIN)

    assert index["exampleToken000000000000004"]["title"] == "2026中长期交易通知752号"
    assert index["exampleToken000000000000005"]["title"] == "要点解析"


def test_evidence_sublist_and_bold_and_tk_variant():
    text = """- 依据:
  - **token=exampleToken000000000000006 (★宁夏调频辅助服务市场实施细则, 14页)**
  - token=exampleToken000000000000007 (2026-01宁夏辅助服务运行情况, 569KB)
- source: token=exampleToken000000000000008 (并网调试管理办法, 2025)
- 现货出清参见 (tk=exampleToken000000000000084 附件5第19条)
"""
    index = parse_file_index(text, DOMAIN)

    assert index["exampleToken000000000000006"]["title"] == "宁夏调频辅助服务市场实施细则"
    assert index["exampleToken000000000000007"]["title"] == "2026-01宁夏辅助服务运行情况"
    assert index["exampleToken000000000000008"]["title"] == "并网调试管理办法"
    # tk= 变体能收录；标题取不到时降级但 url 必须在
    assert index["exampleToken000000000000084"]["url"] == _url("exampleToken000000000000084")


def test_truncated_token_is_ignored():
    """省页表格里有 `Ev6ObC55oo…` 这种省略号截断，长度不足不可用。"""
    text = "| 容量电费实施细则 | Ev6ObC55oo… 第三条 | 容量 |"

    assert parse_file_index(text, DOMAIN) == {}


def test_numeric_only_paren_is_not_used_as_title():
    """`token=XXX(03)/YYY(02)` 里的 (03) 是编号不是标题。"""
    token = "exampleToken000000000000009"
    text = f"> 数据源: 侯桥 token={token}(03)/GWrlbYwr8oUUS7x7HXbcPryUnKe(02)"

    index = parse_file_index(text, DOMAIN)

    assert index[token]["title"] != "03"
    assert index[token]["url"] == _url(token)


def test_index_merges_both_directions():
    """清单表与依据行各有对方没有的 token，必须双向合并。"""
    only_table = "TableOnlyTokenAAAAAAAAAAAAA"
    only_evidence = "EvidenceOnlyTokenBBBBBBBBBB"
    text = f"""
- 依据: token={only_evidence} (结算纠错说明, 2025)

| 文件 | URL | 类型 |
|---|---|---|
| 需求响应政策解读 | {_url(only_table)} | 需求响应 |
"""
    index = parse_file_index(text, DOMAIN)

    assert index[only_table]["title"] == "需求响应政策解读"
    assert index[only_evidence]["title"] == "结算纠错说明"


def test_index_table_title_wins_over_evidence_line_title():
    token = "SharedTokenCCCCCCCCCCCCCCCC"
    text = f"""
- 依据: token={token} (依据行里的简称, 2025)

| 文件 | URL | 类型 |
|---|---|---|
| 清单表里的正式全名 | {_url(token)} | 权威 |
"""
    index = parse_file_index(text, DOMAIN)

    assert index[token]["title"] == "清单表里的正式全名"


# --- ReferenceCollector ---


def test_collector_assigns_sequential_numbers_and_reuses_same_url():
    index = {
        "TokenAAAAAAAAAAAAAAAAAAAAAA": {
            "token": "TokenAAAAAAAAAAAAAAAAAAAAAA",
            "title": "甲文件",
            "url": _url("TokenAAAAAAAAAAAAAAAAAAAAAA"),
        }
    }
    collector = ReferenceCollector(file_index=index)

    first = collector.add_token("TokenAAAAAAAAAAAAAAAAAAAAAA", DOMAIN)
    second = collector.add_token("TokenBBBBBBBBBBBBBBBBBBBBBB", DOMAIN)
    again = collector.add_token("TokenAAAAAAAAAAAAAAAAAAAAAA", DOMAIN)

    assert (first, second, again) == (1, 2, 1)
    refs = collector.to_list()
    assert [r["index"] for r in refs] == [1, 2]
    assert refs[0]["title"] == "甲文件"
    # 索引里没有的 token 标题降级，但 url 仍可用
    assert refs[1]["title"].startswith("TokenBBB")
    assert refs[1]["url"] == _url("TokenBBBBBBBBBBBBBBBBBBBBBB")


def test_collector_respects_max_refs():
    collector = ReferenceCollector(max_refs=2)

    assert collector.add_url("https://a.test", "甲") == 1
    assert collector.add_url("https://b.test", "乙") == 2
    assert collector.add_url("https://c.test", "丙") is None
    assert len(collector.to_list()) == 2


def test_collector_markers_and_legend():
    collector = ReferenceCollector()
    collector.add_url("https://a.test", "甲文件", ref_type="wiki")
    collector.add_url("https://b.test", "乙网页", ref_type="web")

    assert collector.markers([1, 2]) == "[1][2]"
    assert collector.markers([]) == ""
    assert collector.markers([None, 1]) == "[1]"

    legend = collector.legend()
    assert "[1] 甲文件" in legend
    assert "[2] 乙网页" in legend


def test_collector_records_ref_type():
    collector = ReferenceCollector()
    collector.add_url("https://a.test", "甲", ref_type="wiki")
    collector.add_url("https://b.test", "乙", ref_type="web")

    assert [r["type"] for r in collector.to_list()] == ["wiki", "web"]


# --- renumber_citations ---


def _refs(count):
    return [
        {"index": i, "title": f"文件{i}", "url": f"https://s{i}.test", "token": "", "type": "wiki"}
        for i in range(1, count + 1)
    ]


def test_renumber_reorders_by_first_appearance_and_drops_uncited():
    answer, refs = renumber_citations("甲结论[2]。乙结论[1]。", _refs(3))

    assert answer == "甲结论[1]。乙结论[2]。"
    assert [r["index"] for r in refs] == [1, 2]
    assert [r["title"] for r in refs] == ["文件2", "文件1"]


def test_renumber_reuses_same_number_for_repeated_citation():
    answer, refs = renumber_citations("甲[2]乙[2]", _refs(3))

    assert answer == "甲[1]乙[1]"
    assert len(refs) == 1


def test_renumber_drops_out_of_range_but_keeps_valid_ones():
    answer, refs = renumber_citations("甲[3]乙[9]丙[1]", _refs(3))

    assert answer == "甲[1]乙丙[2]"
    assert [r["title"] for r in refs] == ["文件3", "文件1"]


def test_renumber_all_hallucinated_falls_back_to_full_reference_list():
    """模型只输出越界编号时，抹掉角标但来源全量保留，绝不让来源凭空消失。"""
    original = _refs(3)
    answer, refs = renumber_citations("甲[9]乙[0]", original)

    assert answer == "甲乙"
    assert refs == original


def test_renumber_without_any_citation_keeps_answer_and_all_references():
    original = _refs(2)
    answer, refs = renumber_citations("完全没有角标的回答。", original)

    assert answer == "完全没有角标的回答。"
    assert refs == original


def test_renumber_normalizes_grouped_and_fullwidth_brackets():
    answer, refs = renumber_citations("甲[1,3]乙【2】", _refs(3))

    # 原 1/3/2 依首次出现重排为 1/2/3
    assert answer == "甲[1][2]乙[3]"
    assert [r["title"] for r in refs] == ["文件1", "文件3", "文件2"]


def test_renumber_cleans_space_left_by_removed_marker():
    answer, _ = renumber_citations("甲结论 [9] 。乙[1]", _refs(1))

    assert "[9]" not in answer
    assert " 。" not in answer


def test_renumber_handles_empty_inputs():
    assert renumber_citations("", _refs(2))[0] == ""
    answer, refs = renumber_citations("甲[1]", [])
    assert answer == "甲[1]"
    assert refs == []


def test_renumber_does_not_mutate_input_references():
    original = _refs(3)
    snapshot = [dict(item) for item in original]

    renumber_citations("甲[3]", original)

    assert original == snapshot


# --- strip_context_markup（LLM 失败降级时把 context 当答案返回） ---


def test_strip_context_markup_removes_citation_hints_and_legend():
    context = (
        "[蒙西·容量补偿] (可引用: [1][2])\n"
        "- 2026 标准 0.28 元/kWh\n\n"
        "--- 可引用来源编号 ---\n"
        "[1] 容量电费实施细则\n"
    )
    cleaned = strip_context_markup(context)

    assert "可引用" not in cleaned
    assert "容量电费实施细则" not in cleaned
    assert "0.28 元/kWh" in cleaned
