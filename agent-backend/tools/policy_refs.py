"""政策问答引用工具：省页解析、引用编号收集、答案角标重编号。

这个模块刻意保持纯函数、零外部依赖（只用 re），不 import
``app.core.config.settings`` 或 ``lark_oapi``。原因是 ``tools.policy_ask``
在模块顶层就执行 ``get_settings()`` 并强校验五省 token，任何 import 都需要
完整的飞书/LLM 配置；把这些逻辑拆出来，单测才能直接 import 验证。
"""
from __future__ import annotations

import re

# LLM 图例与降级清洗共用的分隔符，policy_ask 拼 context 时也用这个常量。
LEGEND_HEADER = "--- 可引用来源编号 ---"

# 飞书 file token 至少 15 位。这个下限顺带排除了省页里被省略号截断的
# 残缺 token（形如 ``Ev6ObC55oo…``），那种 token 拼出来的 URL 是死链。
_TOKEN_CHARS = r"[A-Za-z0-9]{15,}"
_EVIDENCE_TOKEN_RE = re.compile(rf"\b(?:token|tk)=({_TOKEN_CHARS})")
_CITE_RE = re.compile(r"\[(\d{1,2})\]")
_FULLWIDTH_CITE_RE = re.compile(r"【\s*([\d\s,，、;；]+?)\s*】")
_GROUPED_CITE_RE = re.compile(r"\[\s*(\d{1,2}(?:\s*[,，、;；]\s*\d{1,2})+)\s*\]")
_HINT_RE = re.compile(r"[(（]\s*可引用[:：][^)）]*[)）]")

# 标题里的装饰字符：加粗、重点星标、以及页尾常见的状态后缀。
_TITLE_NOISE_RE = re.compile(r"[*`★☆]|\s*[（(]?已精读[）)]?\s*$")
# 纯数字/页码类候选不是标题（如 ``token=XXX(03)`` 里的 03 是文件序号）。
_NOT_A_TITLE_RE = re.compile(r"^[\d\s.\-第页页码/]*$")


def _clean_title(raw):
    """去掉标题里的加粗、星标与尾部状态词；拿不到有效标题返回空串。"""
    title = _TITLE_NOISE_RE.sub("", str(raw or "")).strip()
    title = title.strip("|-—– \t")
    if not title or _NOT_A_TITLE_RE.match(title):
        return ""
    return title


def _fallback_title(token):
    return f"{token[:8]}…"


def build_file_url(token, domain):
    return f"https://{domain}/file/{token}"


def parse_file_index(text, domain):
    """从省页 markdown 解析 ``token -> {token, title, url}`` 索引。

    两遍扫描双向合并：页尾"依据文件清单"表是权威来源（标题最完整），但确实
    存在只出现在小节 ``- 依据:`` 行里的 token；反过来也有只在清单表里的。
    任何一遍单独用都会漏。

    解析失败只会让 title 降级为 ``token[:8]…``，绝不丢 url、绝不抛异常——
    省页是人工维护的，格式漂移是常态。
    """
    index = {}
    lines = str(text or "").splitlines()
    url_re = re.compile(rf"https://{re.escape(str(domain or ''))}/file/({_TOKEN_CHARS})")

    # Pass 1：依据文件清单表。一行里可能有多个 URL（同一份文件的正文+附件），
    # 它们共享该行首列的标题。
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        tokens = url_re.findall(stripped)
        if not tokens:
            # 表头与 |---|---| 分隔行没有 URL，天然被跳过。
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        title = _clean_title(cells[0]) if cells else ""
        for token in tokens:
            index[token] = {
                "token": token,
                "title": title or _fallback_title(token),
                "url": build_file_url(token, domain),
            }

    # Pass 2：小节依据行兜底。标题从 token 之后、下一个 token 之前的
    # 第一个 ``(文件名, 年份)`` 括号里取逗号前的片段。逐行处理，避免跨行误配。
    for line in lines:
        matches = list(_EVIDENCE_TOKEN_RE.finditer(line))
        for position, match in enumerate(matches):
            token = match.group(1)
            if token in index:
                continue
            tail_end = matches[position + 1].start() if position + 1 < len(matches) else len(line)
            tail = line[match.end():tail_end]
            paren = re.search(r"[(（]([^)）]*)[)）]", tail)
            title = _clean_title(re.split(r"[,，]", paren.group(1))[0]) if paren else ""
            index[token] = {
                "token": token,
                "title": title or _fallback_title(token),
                "url": build_file_url(token, domain),
            }

    return index


class ReferenceCollector:
    """按首次出现顺序给来源分配编号，供 context 图例与最终 references 使用。

    同一个 url 重复登记复用同一编号；超过 ``max_refs`` 返回 None，调用方
    据此不给该来源加角标（而不是把编号写飞）。
    """

    def __init__(self, file_index=None, max_refs=8):
        self._file_index = dict(file_index or {})
        self._max_refs = max_refs
        self._by_url = {}
        self._items = []

    def add_url(self, url, title=None, ref_type="wiki", token=""):
        url = str(url or "").strip()
        if not url:
            return None
        if url in self._by_url:
            return self._by_url[url]
        if len(self._items) >= self._max_refs:
            return None
        index = len(self._items) + 1
        self._by_url[url] = index
        self._items.append({
            "index": index,
            "title": _clean_title(title) or url,
            "url": url,
            "token": token,
            "type": ref_type,
        })
        return index

    def add_token(self, token, domain, ref_type="wiki"):
        token = str(token or "").strip()
        if not token:
            return None
        meta = self._file_index.get(token) or {}
        url = meta.get("url") or build_file_url(token, domain)
        title = meta.get("title") or _fallback_title(token)
        return self.add_url(url, title, ref_type=ref_type, token=token)

    def markers(self, numbers):
        """把编号列表渲染成 ``[2][3]``；None 与重复项自动剔除。"""
        unique = sorted({number for number in (numbers or []) if number})
        return "".join(f"[{number}]" for number in unique)

    def legend(self):
        """拼给 LLM 的编号图例。必须在 context 截断之后追加，否则会被整段截掉。"""
        if not self._items:
            return ""
        lines = [f"[{item['index']}] {item['title']}" for item in self._items]
        return LEGEND_HEADER + "\n" + "\n".join(lines)

    def to_list(self):
        return [dict(item) for item in self._items]

    def __len__(self):
        return len(self._items)


def _normalize_citations(answer):
    """把 ``【1】`` / ``[1,3]`` 归一成 ``[1][3]``。中文模型很爱输出全角括号。"""
    answer = _FULLWIDTH_CITE_RE.sub(lambda m: f"[{m.group(1)}]", answer)

    def _split(match):
        numbers = re.split(r"[,，、;；\s]+", match.group(1).strip())
        return "".join(f"[{number}]" for number in numbers if number)

    return _GROUPED_CITE_RE.sub(_split, answer)


def _tidy(answer):
    """收拾删除角标后留下的空白：孤立空格、标点前空格、多余空行。"""
    answer = re.sub(r"[ \t]{2,}", " ", answer)
    answer = re.sub(r"[ \t]+([，。；、！？：)）】」])", r"\1", answer)
    answer = re.sub(r"\n{3,}", "\n\n", answer)
    return answer.strip()


def renumber_citations(answer, references):
    """按正文角标首次出现顺序重排编号，并只保留被引用到的来源。

    返回 ``(answer, references)``。设计上有两层安全网：
    - 越界编号（模型编造的）直接从正文删掉，不留 ``[]`` 残迹；
    - 若一个有效角标都没有（模型完全不配合），保持正文语义并**全量返回**
      references，绝不让来源列表凭空消失。
    """
    answer = str(answer or "")
    references = list(references or [])
    if not answer or not references:
        return answer, references

    answer = _normalize_citations(answer)

    # 第一遍只建映射，不改文本——边扫边改会让后续匹配读到刚写入的新编号。
    mapping = {}
    for match in _CITE_RE.finditer(answer):
        old = int(match.group(1))
        if 1 <= old <= len(references) and old not in mapping:
            mapping[old] = len(mapping) + 1

    if not mapping:
        return _tidy(_CITE_RE.sub("", answer)), references

    answer = _CITE_RE.sub(lambda m: f"[{mapping[int(m.group(1))]}]" if int(m.group(1)) in mapping else "", answer)

    renumbered = []
    for old, new in sorted(mapping.items(), key=lambda pair: pair[1]):
        item = dict(references[old - 1])  # 拷贝，避免污染 collector 内部状态
        item["index"] = new
        renumbered.append(item)

    return _tidy(answer), renumbered


def strip_context_markup(text):
    """LLM 失败降级时会把 context 原文当答案返回，先剥掉只对模型有意义的标记。"""
    text = str(text or "")
    head = text.split(LEGEND_HEADER)[0]
    head = _HINT_RE.sub("", head)
    head = _CITE_RE.sub("", head)
    return _tidy(head)
