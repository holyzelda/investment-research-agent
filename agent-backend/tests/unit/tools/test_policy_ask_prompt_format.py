"""提示词的排版约定。

答案由前端 ConsultationResult.vue 的 parseMarkdownBlocks() 按 Markdown 渲染。
提示词里不要求结构，模型就会交出一整坨长文本，前端只能当一个段落显示——
这些用例把"提示词必须要求 Markdown 结构"钉住，避免后续调提示词时被顺手删掉。
"""

from tools.policy_ask import GENERAL_PROMPT, SYSTEM_PROMPT

import pytest


@pytest.mark.parametrize("prompt", [SYSTEM_PROMPT, GENERAL_PROMPT])
def test_prompts_require_markdown_structure(prompt):
    assert "Markdown" in prompt
    # 小标题与列表是前端能渲染的结构，缺一个答案就退化成纯段落
    assert "##" in prompt
    assert "- 列表" in prompt
    assert "**加粗**" in prompt
    assert "表格" in prompt


@pytest.mark.parametrize("prompt", [SYSTEM_PROMPT, GENERAL_PROMPT])
def test_prompts_forbid_wall_of_text(prompt):
    assert "不要输出一大段没有换行的长文" in prompt


def test_knowledge_prompt_keeps_citation_and_source_rules():
    """排版规则是追加的，不能挤掉原有的角标与来源约束。"""
    assert "[1]" in SYSTEM_PROMPT
    assert "【可引用来源编号】" in SYSTEM_PROMPT
    assert "不要输出任何URL" in SYSTEM_PROMPT


def test_knowledge_prompt_isolates_caliber_notes():
    """口径差异单起一节，别混在正文里——用户反馈的原始答案就是混着写的。"""
    assert "## 口径说明" in SYSTEM_PROMPT


def test_general_prompt_has_no_citation_rules():
    """通用兜底没有任何检索来源，要求标角标只会让模型编造编号。"""
    assert "【可引用来源编号】" not in GENERAL_PROMPT
