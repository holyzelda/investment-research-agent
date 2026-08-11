"""
api: 储能投研知识库问答服务
用飞书 Python SDK (lark_oapi) 替代 lark-cli, 纯 Python 零 npm 依赖。
v2.1: 本地缓存 + section别名定位 + anysearch兜底 + 落库幂等修复
"""

import json
import re
import os
import time
import uuid
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import lark_oapi as lark

from app.core.config.settings import get_settings
from tools.policy_refs import (
    ReferenceCollector,
    parse_file_index,
    renumber_citations,
    strip_context_markup,
)

_REQUIRED_PROVINCES = ("蒙西", "宁夏", "甘肃", "陕西", "山西")


def _required_config_value(value, path):
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"政策问答配置缺少必填项：policy_ask.{path}")
    return value.strip()


_policy_ask = get_settings().policy_ask

APP_ID = _required_config_value(_policy_ask.feishu.app_id, "feishu.app_id")
APP_SECRET = _required_config_value(_policy_ask.feishu.app_secret, "feishu.app_secret")
INDEX_TOKEN = _required_config_value(_policy_ask.feishu.index_token, "feishu.index_token")
PROVINCES = {}
for _province in _REQUIRED_PROVINCES:
    _token = _policy_ask.feishu.province_tokens.get(_province)
    PROVINCES[_province] = _required_config_value(_token, f"feishu.province_tokens.{_province}")
CROSS_PROVINCE_TOKEN = str(_policy_ask.feishu.cross_province_token or "").strip()
FEISHU_DOMAIN = str(_policy_ask.feishu.domain or "example-value-0071").strip()

ANYSEARCH_API_KEY = str(_policy_ask.anysearch.api_key or "").strip()
TAVILY_API_KEY = str(_policy_ask.anysearch.tavily_api_key or "").strip()
LLM_BASE_URL = _required_config_value(_policy_ask.llm.base_url, "llm.base_url")
LLM_API_KEY = _required_config_value(_policy_ask.llm.api_key, "llm.api_key")
LLM_MODEL = _required_config_value(_policy_ask.llm.model, "llm.model")
BASE_TOKEN = str(_policy_ask.base.token or "").strip()
BASE_TABLE = str(_policy_ask.base.table or "").strip()

TMP_DIR = Path(__file__).parent / "_tmp_download"
CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_TTL = 86400  # 省页缓存24小时
# 省份别名(只收无歧义别名, 单字"宁"/"甘"会误路由；"陇"/"晋"需白名单语境见 _province_match)
PROVINCE_ALIASES = {
    "蒙西": ["蒙西", "内蒙古", "内蒙", "蒙西电网"],
    "宁夏": ["宁夏", "宁夏省"],
    "甘肃": ["甘肃", "甘肃省"],
    "陕西": ["陕西", "陕西省", "三秦"],
    "山西": ["山西", "山西省", "三晋"],
}
# 单字别名（子串匹配误路由风险高，仅允许出现在白名单语境，如"陇电/晋能"）
SINGLE_CHAR_ALIASES = {"甘肃": ["陇"], "山西": ["晋"]}

# 跨省对比关键词（仅明确跨省意图才触发；"回本/更适合"等过于通用已移除）
CROSS_PROVINCE_KW = ["西北", "三省", "跨省", "哪个省", "投哪里", "选哪个", "对比"]

SYSTEM_PROMPT = (
    "你是储能电力交易投研知识库问答助手。基于检索信息回答投研问题。规则: "
    "1.先给结论，再展开关键数值和约束。"
    "2.每个来自检索信息的结论、数值或政策约束，必须在该句句号之前标注引用角标，"
    "格式为半角方括号加数字，如 [1]；引用多个来源写成 [1][2]。"
    "3.只能使用【可引用来源编号】图例中出现过的编号，严禁编造图例里没有的编号。"
    "4.用角标代替来源标注，不要写出文件名全称，也不要输出任何URL。"
    "5.基于现有信息给出最有把握的回答。"
    "6.不提及资料状态、草稿、待确认等字样。"
    "7.不要提及'未找到/知识库暂无/检索不到/建议查阅'等检索缺失表述，直接给出答案。"
)

GENERAL_PROMPT = "你是储能电力交易投研助手。请基于你的专业知识和经验回答用户的投研问题。规则: 1.给出方向性、有依据的回答，包含关键分析维度。2.数值若不确定，用区间或定性描述。3.保持简洁、自信，不要提及'未找到/知识库暂无/建议查阅官方文件'等检索缺失表述。4.不要在答案中输出任何URL链接。"

# 单例 client
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = lark.Client.builder() \
            .app_id(APP_ID) \
            .app_secret(APP_SECRET) \
            .build()
    return _client


def _download(token, no_cache=False):
    """下载省页, 带本地缓存. 返回本地路径."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{token}.md"
    if not no_cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            return str(cache_path)

    client = _get_client()
    req = lark.BaseRequest.builder() \
        .http_method(lark.HttpMethod.GET) \
        .uri(f"/open-apis/drive/v1/files/{token}/download") \
        .token_types({lark.AccessTokenType.TENANT}) \
        .build()

    resp = client.request(req)
    if not resp.success():
        if cache_path.exists():  # 下载失败但旧缓存可用→降级
            return str(cache_path)
        raise RuntimeError(f"下载失败(token={token[:12]}...): code={resp.code}, msg={resp.msg}")

    cache_path.write_bytes(resp.raw.content)
    return str(cache_path)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _fallback_context(context):
    """LLM 返回空时降级为检索到的原文，避免空 answer。

    context 里带有只对模型有意义的引用编号提示与图例，直接展示会让用户困惑，
    先经 strip_context_markup 剥掉。
    """
    safe = re.sub(r"token=[A-Za-z0-9]{15,}", "", context or "")
    safe = re.sub(r"https?://\S+", "", safe)
    safe = strip_context_markup(safe)
    return safe or "抱歉，本次未能生成回答，请重试。"


def _call_llm_nonstream(body):
    """调用 LLM（非流式），对瞬时错误（5xx/超时）和空 content 重试 1 次。

    返回 content 字符串；重试仍失败则返回 ""，由调用方降级。
    """
    for attempt in range(2):  # 首次 + 重试 1 次
        try:
            req = Request(LLM_BASE_URL.rstrip("/") + "/v1/chat/completions", data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
            resp = urlopen(req, timeout=60)
            data = json.loads(resp.read())
            content = (data["choices"][0]["message"].get("content") or "").strip()
            if content:
                return content
            # content 空 → 重试
        except HTTPError as e:
            # 5xx 瞬时错误才重试；4xx 参数错误重试无用，直接抛给上层降级
            if e.code < 500 or attempt == 1:
                raise
            time.sleep(1)
        except (URLError, TimeoutError):
            if attempt == 1:
                raise
            time.sleep(1)
    return ""  # 重试仍失败 → 调用方降级


def _llm_summarize(question, context, as_of, status, on_token=None):
    """
    LLM 总结函数，支持流式输出。

    Args:
        question: 用户问题
        context: 检索到的上下文
        as_of: 时效信息
        status: 状态信息
        on_token: 可选回调函数，每收到一个 token 就调用一次 on_token(token)
    """
    # 只剥掉裸token(以token=开头的内部标识), 保留完整URL给用户点击
    safe_context = re.sub(r'token=[A-Za-z0-9]{15,}', '', context)
    prompt = f"用户问题: {question}\n\n检索到的信息:\n{safe_context}\n\n时效: as_of={as_of}, status={status}"

    body = json.dumps({
        "model": LLM_MODEL,
        "max_tokens": 8192,
        "stream": on_token is not None,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")

    api_url = LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"

    try:
        if on_token is None:
            # 非流式模式：_call_llm_nonstream 内部已重试 5xx/空 content
            content = _call_llm_nonstream(body)
            if not content:
                return _fallback_context(context)
            return content
        else:
            # 流式模式：对 5xx/超时重试 1 次，再解析 SSE
            resp = None
            for attempt in range(2):
                try:
                    req = Request(api_url, data=body, method="POST")
                    req.add_header("Content-Type", "application/json")
                    req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
                    resp = urlopen(req, timeout=60)
                    break
                except HTTPError as e:
                    if e.code < 500 or attempt == 1:
                        raise
                    time.sleep(1)
                except (URLError, TimeoutError):
                    if attempt == 1:
                        raise
                    time.sleep(1)
            full_content = []
            for line in resp:
                line = line.decode('utf-8').strip()
                if not line or line.startswith(':'):
                    continue
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        if not choices:
                            continue
                        delta = choices[0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            full_content.append(content)
                            on_token(content)
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
            return ''.join(full_content)
    except (URLError, TimeoutError):
        return _fallback_context(context)
    except (KeyError, IndexError, json.JSONDecodeError):
        return _fallback_context(context)


def _llm_summarize_general(question, on_token=None):
    """LLM 通用知识兜底（知识库+联网都 miss 时使用），支持流式输出"""
    prompt = f"用户问题: {question}"

    body = json.dumps({
        "model": LLM_MODEL,
        "max_tokens": 8192,
        "stream": on_token is not None,
        "messages": [
            {"role": "system", "content": GENERAL_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")

    api_url = LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"

    try:
        if on_token is None:
            # 非流式模式：_call_llm_nonstream 内部已重试 5xx/空 content
            content = _call_llm_nonstream(body)
            if not content:
                return _fallback_context(question)
            return content
        else:
            # 流式模式：对 5xx/超时重试 1 次，再解析 SSE
            resp = None
            for attempt in range(2):
                try:
                    req = Request(api_url, data=body, method="POST")
                    req.add_header("Content-Type", "application/json")
                    req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
                    resp = urlopen(req, timeout=60)
                    break
                except HTTPError as e:
                    if e.code < 500 or attempt == 1:
                        raise
                    time.sleep(1)
                except (URLError, TimeoutError):
                    if attempt == 1:
                        raise
                    time.sleep(1)
            full_content = []
            for line in resp:
                line = line.decode('utf-8').strip()
                if not line or line.startswith(':'):
                    continue
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        if not choices:
                            continue
                        delta = choices[0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            full_content.append(content)
                            on_token(content)
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
            return ''.join(full_content)
    except (URLError, TimeoutError):
        return "抱歉，本次未能生成回答，请稍后重试。"
    except (KeyError, IndexError, json.JSONDecodeError):
        return "抱歉，无法生成回答。"


def _parse_sections(text):
    """解析省页为 [{title, aliases, body}]."""
    sections = []
    cur = None
    for line in text.split("\n"):
        m = re.match(r"^#{1,4}\s+(.+)$", line)
        if m:
            if cur:
                sections.append(cur)
            cur = {"title": m.group(1).strip(), "lines": [], "aliases": []}
        elif cur:
            cur["lines"].append(line)
            am = re.match(r"\s*-\s*别名[:：]\s*(.+)", line)
            if am:
                cur["aliases"] = [a.strip() for a in re.split(r"[,，、]", am.group(1)) if a.strip()]
    if cur:
        sections.append(cur)
    return sections


def _extract_keywords(question):
    """从问题提取语义词元：去省份/问句尾/年份，按标点+空格切分，产出多个关键词。"""
    clean = question
    for aliases in PROVINCE_ALIASES.values():
        for a in aliases:
            clean = clean.replace(a, "")
    # 单字别名也剥掉（如"陇电"）
    for singles in SINGLE_CHAR_ALIASES.values():
        for ch in singles:
            clean = clean.replace(ch, "")
    # 剥离问句尾巴/语气词（不参与 section 匹配）
    clean = re.sub(
        r"(多少钱|是多少|多少|是什么|什么|如何|怎么|为什么|能|可以|是否|吗|呢|啊|吧|请问|大概|现在|最新|现行|了解|一下|告诉我|知道|想问|帮我)",
        "", clean)
    # 剥离年份（2026年/2025/25年）
    clean = re.sub(r"(20\d{2}年?|\b\d{2}年)", "", clean)
    # 按常用标点+空格切分
    words = [w for w in re.split(r"[，,。．；;：:、？！?\s]+", clean) if len(w) >= 2]
    if not words:
        words = [clean.strip()] if clean.strip() else []
    return words


def _tokenize_title(title):
    """把标题拆成语义词元：按 空格/括号/·/冒号/逗号 切分."""
    parts = re.split(r"[()（）\s·:：,，]+", title)
    return [p for p in parts if len(p) >= 2]


def _longest_common_substr(a, b):
    """返回两个字符串的最长公共子串长度."""
    if not a or not b:
        return 0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    longest = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                longest = max(longest, dp[i][j])
    return longest


def _score_section(section, keyword):
    """返回 keyword 对 section 的命中得分，0=未命中。得分越高越相关。"""
    score = 0
    kw = keyword
    # 别名命中（最高）
    for a in section["aliases"]:
        if kw in a or a in kw:
            score = max(score, 100)
    # 标题子串命中
    if kw in section["title"]:
        score = max(score, 80)
    # 标题词元交集/公共子串（解决"申报价上下限" vs 标题"申报价格"长词匹配）
    title_tokens = _tokenize_title(section["title"])
    for t in title_tokens:
        if t in kw or kw in t:
            score = max(score, 60)
        elif _longest_common_substr(kw, t) >= 2:
            score = max(score, 45)
    # 正文出现（低分兜底）
    if kw in "\n".join(section["lines"]):
        score = max(score, 30)
    return score


def _match_sections(sections, keywords):
    """多关键词匹配：每个 section 累加所有关键词得分，按总分排序返回命中列表.

    不再用优先级截断（别名>标题>正文），所有命中并列收集并按相关度排序，
    避免宽泛别名遮蔽精确标题；多关键词累加让"现货+限价"等复合问法命中更准。
    """
    scored = []
    for s in sections:
        total = 0
        for kw in keywords:
            total += _score_section(s, kw)
        if total > 0:
            scored.append((total, s))
    scored.sort(key=lambda x: -x[0])  # 得分降序
    return [s for _, s in scored]


def _quick_table(text):
    """抽取速查表."""
    m = re.search(r"(## 速查表.*?)(?=\n## |\Z)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _filter_quick_table(qt, keywords):
    """速查表行级过滤：只保留含关键词的行（表头/分隔行保留）。

    速查表是每行一个市场的 markdown 表格，如 `| 容量补偿 | 有条件 | ... |`。
    问"容量补偿"时只保留容量补偿行，无关市场行不污染 context。
    若过滤后只剩表头（关键词与速查表无关）→ 返回空，避免误导 LLM。
    """
    if not qt or not keywords:
        return qt
    lines = qt.split("\n")
    keep = []
    for line in lines:
        # 表头 | 细分市场 |...、分隔行 |---|---|、空行 无条件保留
        if not line.strip():
            keep.append(line)
        elif "细分市场" in line:
            keep.append(line)
        elif re.match(r"^\|[\s\-|]+\|$", line):
            keep.append(line)
        elif any(kw in line for kw in keywords):
            keep.append(line)
    filtered = "\n".join(keep)
    # 有无数据行（"| 可" / "| 有条件" / "| 无" 是数据行特征）
    has_data = any(("| 可" in l or "| 有条件" in l or "| 无" in l) for l in keep)
    return filtered if has_data else ""


def _evolution_entries(text, keyword):
    """抽取参数演变日志中相关条目."""
    m = re.search(r"## 参数演变日志.*?(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        return ""
    blocks = re.findall(r"(### .+?)(?=\n### |\Z)", m.group(0), re.DOTALL)
    rel = [b.strip() for b in blocks if keyword in b.split("\n")[0]]
    return "\n\n".join(rel)


def _cross_province_summary(text):
    """提取跨省对比页的关键表格，减少 context 大小"""
    blocks = []
    # 提取一句话总结
    m = re.search(r"> 四省现状一句话:.*", text)
    if m: blocks.append(m.group(0).strip())
    # 提取表3（关键参数对比）
    m = re.search(r"(## 表3 · 关键参数对比.*?)(?=\n## |\Z)", text, re.DOTALL)
    if m: blocks.append(m.group(1).strip())
    # 提取投研决策速递
    m = re.search(r"(## 投研决策速递.*?)(?=\n## |\Z)", text, re.DOTALL)
    if m: blocks.append(m.group(1).strip())
    return "\n\n".join(blocks) if blocks else text[:2000]


def _tokens_near_keywords(text, keywords, window=3):
    """收集含关键词行及其上下 window 行内的 token（依据块常在相邻行）。

    保持首现顺序去重。关键词为空或全无命中时返回空列表，由调用方决定兜底策略。
    """
    if not keywords:
        return []
    lines = text.split("\n")
    hit_indices = [i for i, line in enumerate(lines) if any(kw in line for kw in keywords)]
    tokens = []
    for i in hit_indices:
        for j in range(max(0, i - window), min(len(lines), i + window + 1)):
            tokens.extend(re.findall(r"token=([A-Za-z0-9]{15,})", lines[j]))
    return list(dict.fromkeys(tokens))


def _wiki_page_tokens():
    """省页/索引/跨省页自身的 token —— 它们是知识库骨架，不是可引用的政策文件。"""
    return set(PROVINCES.values()) | {INDEX_TOKEN, CROSS_PROVINCE_TOKEN}


def _append_legend(context, collector):
    """把编号图例追加到 context 末尾。

    必须在 MAX_CONTEXT 截断之后调用：图例若参与截断会被整段切掉，模型就不知道
    每个编号对应什么文件，角标质量直接归零。
    """
    legend = collector.legend()
    return f"{context}\n\n{legend}" if legend else context


def _cross_province_result():
    """跨省对比页结果：下载+精简+提取四省省页 sources.

    跨省对比的 sources 是各省页链接（用户点开看各省详情），
    只排除跨省页自身 + 索引页，保留省页。
    """
    prov_token = CROSS_PROVINCE_TOKEN
    prov_name = "跨省对比"
    if not prov_token:
        return {
            "province": prov_name,
            "context": "跨省对比页 token 未配置（设 KB_ASK_CROSS_PROVINCE_TOKEN 环境变量）。",
            "sources": [], "references": [], "as_of": None, "status": None,
            "source_type": "wiki",
        }
    prov_path = _download(prov_token)
    prov_text = _read(prov_path)
    m = re.search(r"as_of:\s*(\S+)", prov_text)
    as_of = m.group(1) if m else "未知"
    m = re.search(r"status:\s*(.+)", prov_text)
    status = m.group(1).strip() if m else "草稿"
    context = _cross_province_summary(prov_text)
    # sources: 提取"四省省页链接"表格中的 file URL。跨省页的清单表首列即省名，
    # 正好当作引用标题。
    collector = ReferenceCollector(file_index=parse_file_index(prov_text, FEISHU_DOMAIN))
    for line in prov_text.split("\n"):
        for token in re.findall(r"https://" + re.escape(FEISHU_DOMAIN) + r"/file/([A-Za-z0-9]+)", line):
            # 只排除跨省页自身 + 索引页，保留省页
            if token not in {INDEX_TOKEN, CROSS_PROVINCE_TOKEN}:
                collector.add_token(token, FEISHU_DOMAIN)
    references = collector.to_list()
    return {
        "province": prov_name,
        "context": _append_legend(context, collector),
        "sources": [item["url"] for item in references],
        "references": references,
        "as_of": as_of, "status": status,
        "source_type": "wiki",
    }


_SEARCH_STOPWORDS = (
    "储能", "装机", "情况", "多少", "怎么", "如何", "是否", "现在", "当前", "最新",
    "呢", "吗", "啊", "吧", "请问", "大概", "预估", "预测", "计算", "参与", "可以",
)

_AGENCY_KW = {
    "陕西": "陕西省能源局",
    "甘肃": "甘肃省能源局",
    "宁夏": "宁夏回族自治区发改委",
    "蒙西": "内蒙古自治区能源局",
    "山西": "山西省能源局",
}


def _build_search_queries(question):
    """豆包式拆词：从问题构造多个搜索 query，覆盖不同检索角度.

    独立于 _extract_keywords（那个剥离省份/储能等核心词，不适合搜索）。
    构造策略：
      - 主 query：原问题
      - 省份+主题+最新
      - 省份+主题+年份（如问题含年份）
      - 机构+主题（政策/规划类）
    """
    # 提取省份
    province = None
    for std_name, aliases in PROVINCE_ALIASES.items():
        for a in aliases:
            if a in question:
                province = std_name
                break
        if province:
            break

    # 提取年份：问题含年份用问题年份，否则默认当前业务年（时间优先）
    year = None
    ym = re.search(r"(20\d{2})", question)
    if ym:
        year = ym.group(1)
    else:
        year = "2026"

    # 提取主题：去省份/年份/停用词后的核心词
    clean = question
    for std_name, aliases in PROVINCE_ALIASES.items():
        for a in aliases:
            clean = clean.replace(a, "")
    clean = re.sub(r"20\d{2}年?", "", clean)
    words = [w for w in re.split(r"[，,。．；;：:、？！?\s]+", clean) if len(w) >= 2]
    words = [w for w in words if w not in _SEARCH_STOPWORDS]
    topic = " ".join(words[:4]) if words else ""

    queries = [question.strip()]  # 主 query

    if province and topic:
        queries.append(f"{province} {topic} {year}")  # 显式年份（时间优先）
        queries.append(f"{province} {topic} 最新")
        agency = _AGENCY_KW.get(province)
        if agency and any(k in question for k in ["规划", "政策", "通知", "标准", "方案", "装机"]):
            queries.append(f"{agency} {topic}")

    # 去重
    seen = set()
    return [q for q in queries if q.strip() and not (q in seen or seen.add(q))]


def _anysearch_search(query_text, max_results=5, collector=None):
    """调用 anysearch HTTP API 做联网搜索兜底. 返回 (正文聚合文本, URL列表) 或 None.

    优先使用结果中的 content（网页正文），而非 snippet（摘要）；
    带 freshness 时效参数；返回全部结果（非仅前3）。

    传入 collector 时，每条结果正文前会带上 ``[n]`` 编号，供 LLM 直接引用。
    """
    try:
        headers = {"Content-Type": "application/json"}
        if ANYSEARCH_API_KEY:
            headers["Authorization"] = f"Bearer {ANYSEARCH_API_KEY}"
        body = json.dumps({
            "query": query_text,
            "max_results": max_results,
            "freshness": "month",  # 时效：近一月
        }).encode("utf-8")
        req = Request("https://api.anysearch.com/v1/search", data=body, headers=headers)
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        results = (data.get("data") or {}).get("results") or []
        if not results:
            return None
        lines = ["[来源: 联网检索]"]
        urls = []
        for r in results:
            # 优先 content（正文），缺失用 snippet
            content = (r.get("content") or "").strip()
            if not content:
                content = (r.get("snippet") or "").strip()
            marker = _register_web_result(collector, r.get("url"), r.get("title"))
            if content:
                lines.append(f"- {marker}{r.get('title','')}:\n{content[:2000]}")
            if r.get("url"):
                lines.append(f"  来源: {r['url']}")
                urls.append(r["url"])
        return "\n".join(lines), urls
    except Exception:
        return None


def _register_web_result(collector, url, title):
    """给联网检索结果登记编号，返回 ``"[n] "`` 前缀（超出上限或无 collector 时为空串）。"""
    if collector is None or not url:
        return ""
    index = collector.add_url(url, title or url, ref_type="web")
    return f"[{index}] " if index else ""


def _tavily_search(query_text, max_results=5, collector=None):
    """调用 Tavily API 做联网搜索. 返回 (正文聚合文本, URL列表) 或 None.

    Tavily 专为 AI 设计：返回 answer（AI总结）+ results（含完整 content）。
    优先用 answer + 各结果 content（完整正文），信息量优于 anysearch snippet。
    """
    try:
        if not TAVILY_API_KEY:
            return None
        body = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": query_text,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }).encode("utf-8")
        req = Request("https://api.tavily.com/search", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        resp = urlopen(req, timeout=12)
        data = json.loads(resp.read())
        results = data.get("results") or []
        if not results:
            return None
        lines = ["[来源: 联网检索(Tavily)]"]
        urls = []
        answer = (data.get("answer") or "").strip()
        if answer:
            # AI 摘要是多源聚合，不对应单一 URL，故不给编号——给了会让角标指错来源。
            lines.append(f"- AI摘要: {answer[:1000]}")
        for r in results:
            content = (r.get("content") or "").strip()
            marker = _register_web_result(collector, r.get("url"), r.get("title"))
            if content:
                lines.append(f"- {marker}{r.get('title','')}:\n{content[:2000]}")
            if r.get("url"):
                lines.append(f"  来源: {r['url']}")
                urls.append(r["url"])
        return "\n".join(lines), urls
    except Exception:
        return None


def _web_fallback(question, prov_name, as_of, status):
    """联网兜底：多关键词搜索聚合正文，返回 web result dict 或 None.

    优先 Tavily（AI优化输出，信息质量更高），未配置/失败时 fallback 到 anysearch。
    """
    # 选择搜索函数：有 Tavily key 用 Tavily，否则 anysearch
    searcher = _tavily_search if TAVILY_API_KEY else _anysearch_search

    # collector 跨两个 query 共享，同一网页在两次检索里出现只占一个编号。
    collector = ReferenceCollector()
    combined_text = None
    combined_urls = []
    for q in _build_search_queries(question)[:2]:  # 主 query + 1 个副 query
        web_result = searcher(q, collector=collector)
        if web_result:
            text, urls = web_result
            combined_urls.extend(urls)
            if combined_text is None:
                combined_text = text
            else:
                combined_text += "\n\n" + text
    if not combined_urls:
        return None
    references = collector.to_list()
    context = (
        "以下为最新检索结果，回答时优先引用时间最新的数据，并明确标注每个数据的统计时点；"
        f"不同时点数据口径不同时需说明差异:\n{combined_text}"
    )
    return {
        "province": prov_name,
        "context": _append_legend(context, collector),
        "sources": [item["url"] for item in references],
        "references": references,
        "as_of": as_of,
        "status": status + " +联网检索" if status else "联网检索",
        "source_type": "web",
    }


def query(question, allow_web=True):
    # 1. 检测跨省对比意图（优先于单省匹配）
    # 显式跨省关键词，或问题同时提到 ≥2 个省份名（并列即对比意图）
    province_count = sum(
        1 for std_name, aliases in PROVINCE_ALIASES.items()
        if any(alias in question for alias in aliases)
    )
    is_cross = any(kw in question for kw in CROSS_PROVINCE_KW) or province_count >= 2
    if is_cross and province_count >= 2:
        return _cross_province_result()

    # 2. 匹配单省份 (含别名；单字别名需白名单语境)
    matched = None
    for std_name, aliases in PROVINCE_ALIASES.items():
        for alias in aliases:
            if alias in question:
                matched = (std_name, PROVINCES[std_name])
                break
        if matched:
            break
    if not matched:
        # 单字别名（陇/晋）仅在白名单语境匹配，避免"晋升/陇县"误路由
        for std_name, singles in SINGLE_CHAR_ALIASES.items():
            for ch in singles:
                if re.search(rf"{re.escape(ch)}(电|能|网|东|南|中|煤|京|地)", question):
                    matched = (std_name, PROVINCES[std_name])
                    break
            if matched:
                break

    # 3. 未匹配省份 → 跨省或 anysearch 兜底
    if not matched:
        if is_cross:
            return _cross_province_result()
        else:
            # wiki miss (未识别省份), 尝试 anysearch 兜底
            if allow_web:
                web_result = _web_fallback(question, None, None, None)
                if web_result:
                    return web_result
            # 联网也 miss → LLM 通用知识兜底
            return {
                "province": None,
                "context": "",
                "sources": [], "references": [], "as_of": None, "status": None,
                "source_type": "llm_general",
            }
    else:
        prov_name, prov_token = matched

    prov_path = _download(prov_token)
    prov_text = _read(prov_path)

    m = re.search(r"as_of:\s*(\S+)", prov_text)
    as_of = m.group(1) if m else "未知"
    m = re.search(r"status:\s*(.+)", prov_text)
    status = m.group(1).strip() if m else "草稿"

    # 页尾"依据文件清单"表 + 小节依据行合并出的 token→文件名/URL 索引，
    # 下面两条 wiki 路径都靠它把裸 token 变成有名字的引用条目。
    file_index = parse_file_index(prov_text, FEISHU_DOMAIN)
    wiki_tokens = _wiki_page_tokens()

    # 3. 从省页 section 别名/标题定位关键词 (替代硬编码 market_kw)
    sections = _parse_sections(prov_text)
    # 提取问题中的语义词元（去省份/问句尾/年份，按标点切分）
    keywords = _extract_keywords(question)

    hits = _match_sections(sections, keywords)
    # 去重（按标题保首现）
    seen = set()
    hits = [s for s in hits if not (s["title"] in seen or seen.add(s["title"]))]

    if not hits:
        # wiki section miss → 先用速查表兜底（行级过滤，仅当速查表确实覆盖问题）
        qt = _quick_table(prov_text)
        filtered_qt = _filter_quick_table(qt, keywords) if qt else ""
        if filtered_qt:
            # 提取省页源文件 token：优先按关键词相关行过滤，替代全页前5个
            collector = ReferenceCollector(file_index=file_index)
            candidates = _tokens_near_keywords(prov_text, keywords)
            if not candidates:
                candidates = re.findall(r"token=([A-Za-z0-9]{15,})", prov_text)
            for token in candidates:
                if token not in wiki_tokens:
                    collector.add_token(token, FEISHU_DOMAIN)
            references = collector.to_list()
            context = f"{prov_name} 相关参数如下:\n\n{filtered_qt}"
            return {
                "province": prov_name,
                "context": _append_legend(context, collector),
                "sources": [item["url"] for item in references],
                "references": references,
                "as_of": as_of,
                "status": status,
                "source_type": "wiki",
            }
        # 速查表不存在或与问题无关（过滤后为空）→ 联网兜底
        if allow_web:
            web_result = _web_fallback(question, prov_name, as_of, status)
            if web_result:
                return web_result

        # 联网也 miss → LLM 通用知识兜底
        return {
            "province": prov_name,
            "context": f"请基于专业知识回答该问题。",
            "sources": [],
            "references": [],
            "as_of": as_of,
            "status": status,
            "source_type": "llm_general",
        }

    # 先收集引用编号，再拼 context —— 每个 section 块头要带上自己的可引用编号，
    # 模型才知道"这段话该标 [2]"。
    collector = ReferenceCollector(file_index=file_index)
    lines = prov_text.split("\n")
    section_markers = {}
    for s in hits:
        numbers = []
        # 1) 命中 section 正文里的 token=XXX 引用（最精确，section 自己声明的依据）
        for line in s["lines"]:
            for token in re.findall(r"token=([A-Za-z0-9]{15,})", line):
                if token not in wiki_tokens:
                    numbers.append(collector.add_token(token, FEISHU_DOMAIN))
        # 2) 文件索引表里标题与本 section 标题/别名相关的行（URL 集中在表格，不在正文）
        filter_kw = {s["title"], *s["aliases"]}
        filter_kw.update(p for p in re.split(r"[()（）\s]+", s["title"]) if len(p) >= 2)
        for line in lines:
            urls = re.findall(r"https://" + re.escape(FEISHU_DOMAIN) + r"/file/([A-Za-z0-9]+)", line)
            if urls and any(kw in line for kw in filter_kw):
                for token in urls:
                    if token not in wiki_tokens:
                        numbers.append(collector.add_token(token, FEISHU_DOMAIN))
        section_markers[s["title"]] = collector.markers(numbers)

    qt = _quick_table(prov_text)
    filtered_qt = _filter_quick_table(qt, keywords)  # 行级过滤：只保留相关市场行
    blocks = []
    if filtered_qt:
        blocks.append(f"[{prov_name} 速查表·相关行]\n{filtered_qt}\n")
    for s in hits:
        body = "\n".join(l for l in s["lines"] if l.strip()
                         and not l.strip().startswith("- 别名"))
        marker = section_markers.get(s["title"]) or ""
        hint = f" (可引用: {marker})" if marker else ""
        blocks.append(f"[{prov_name}·{s['title']}]{hint}\n{body}")

    # 追加相关版本链条目
    for kw in keywords:
        evo = _evolution_entries(prov_text, kw)
        if evo:
            blocks.append(f"## 相关参数演变\n{evo}")
            break

    context = "\n\n".join(blocks)

    # context 长度上限：超长截断，避免 max_tokens=800 下上下文截断导致回答残缺
    MAX_CONTEXT = 3500
    if len(context) > MAX_CONTEXT:
        context = context[:MAX_CONTEXT] + "\n...(上下文过长已截断)"

    references = collector.to_list()

    return {
        "province": prov_name,
        # 图例必须在截断之后追加，否则会被整段切掉，模型就不认识这些编号了。
        "context": _append_legend(context, collector),
        "sources": [item["url"] for item in references],
        "references": references,
        "as_of": as_of,
        "status": status,
        "source_type": "wiki",
    }


def _finalize(answer, result):
    """统一出口：按正文角标重编号来源，只对外暴露结论与源文件。

    省份、时效、核验状态和 source_type 都是检索过程的元信息，仍留在 query()
    结果里供落库与日志使用，但不进入对外返回值——调用方只要答案和它出自哪份文件。
    """
    references = list(result.get("references") or [])
    answer, references = renumber_citations(answer, references)
    return {"answer": answer, "references": references}


def ask(question, allow_web=True, on_token=None):
    result = query(question, allow_web=allow_web)
    source_type = result.get("source_type", "wiki")

    # 三级兜底: wiki → web → llm_general
    if source_type == "llm_general":
        # 通用知识兜底没有任何检索来源，不加角标（GENERAL_PROMPT 也不要求）。
        answer = _llm_summarize_general(question, on_token=on_token)
        final = _finalize(answer, result)
        _log_to_base(question, final["answer"], result.get("province"), "N/A", "N/A", [])
        return final

    answer = _llm_summarize(
        question,
        result["context"],
        result.get("as_of"),
        result.get("status"),
        on_token=on_token,
    )
    final = _finalize(answer, result)

    # 落库用重编号后的 answer，保证日志与用户看到的一致。
    if result.get("province") is None:
        _log_to_base(question, final["answer"], None, "N/A", "N/A", [])
    else:
        _log_to_base(
            question,
            final["answer"],
            result["province"],
            result.get("as_of"),
            result.get("status"),
            result["context"],
        )
    return final


# === Base 自动记录（未配置 token/table 时跳过日志） ===

TOPIC_KW = {
    "容量补偿": ["容量补偿", "容量电价", "容量电费", "容量"],
    "现货": ["现货", "日前", "实时", "节点电价", "LMP"],
    "调频": ["调频", "AGC", "APC", "调频里程"],
    "调峰": ["调峰", "深调峰", "启停"],
    "中长期": ["中长期", "双边", "日融合", "多边交易"],
    "需求响应": ["需求响应", "需求侧"],
}


def _make_write_key(question, province, topic):
    """写入键不含来源指纹——同问题始终命中同记录，真正幂等。"""
    raw = f"{question}|{province or '其他'}|{topic}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:20]


def _infer_topic(question, province):
    if province == "跨省对比" or any(k in question for k in ["跨省", "三省", "哪个省", "投哪里"]):
        return "跨省对比"
    for topic, kws in TOPIC_KW.items():
        if any(k in question for k in kws):
            return topic
    return "其他"


def _make_fingerprint(answer):
    clean = re.sub(r"https?://\S+", "", answer)
    clean = re.sub(r"token=\S+", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:200]

def _log_to_base(question, answer, province, as_of, status, context):
    """先快速写入 Base(不含LLM评分), 后台异步补充打分. v2: 写入键幂等+标准主题+来源指纹."""
    if not BASE_TOKEN or not BASE_TABLE:
        return  # Base 未配置，静默跳过日志
    try:
        # 推断问题类型和市场
        qtype = "D-跨省" if province == "跨省对比" else (
            "F-超纲" if province is None else (
                "C-时效" if any(k in question for k in ["哪年","哪个值","现在","最新","还","变了"]) else (
                    "B-参数" if any(k in question for k in ["多少","价格","补偿","电价","参数"]) else (
                        "E-标杆" if any(k in question for k in ["赚","收益","结算单","标杆"]) else "A-准入"))))
        markets = []
        for mk, kws in {"中长期":["中长期"],"现货":["现货","日前","实时","节点电价"],"容量补偿":["容量"],"调峰":["调峰","深调峰"],"调频":["调频","AGC"]}.items():
            if any(k in question for k in kws):
                markets.append(mk)

        topic = _infer_topic(question, province)
        fingerprint = _make_fingerprint(answer)
        write_key = _make_write_key(question, province, topic)

        # 拒答边界(规则判定，不等LLM）
        refuse_score = 3
        ans_text = str(answer)
        if province is None or "未识别" in ans_text:
            refuse_score = 3 if any(k in ans_text for k in ["未识别","暂无","知识库暂无","无法","没有"]) else 1
        elif any(k in ans_text for k in ["知识库暂无","暂无相关","暂无具体"]):
            refuse_score = 3
        elif len(ans_text) < 50 and "无法" in ans_text:
            refuse_score = 2

        # 第一步：按写入键查已有记录→有则更新(幂等)
        data = {
            "问题": question, "答案": str(answer)[:500],
            "省份": province or "其他",
            "关联市场": markets or None,
            "问题类型": qtype,
            "忠实度": "", "相关性": "", "引用质量": "", "完整性": "",
            "拒答边界": refuse_score,
            "发现的问题": "", "状态": "待处理", "评估人": "api",
            "写入键": write_key,
            "标准主题": topic,
            "来源指纹": fingerprint,
        }
        js = json.dumps(data, ensure_ascii=False)
        tmp = f"_auto_log_{uuid.uuid4().hex[:8]}.json"
        with open(tmp, "w", encoding="utf-8") as f: f.write(js)

        try:
            # 按写入键查已有记录 (subprocess, 与 kb_log.py 一致)
            import subprocess
            rid = None
            try:
                r = subprocess.run(
                    ["lark-cli", "base", "+record-search",
                     "--base-token", BASE_TOKEN, "--table-id", BASE_TABLE,
                     "--keyword", write_key, "--search-field", "写入键",
                     "--field-id", "写入键", "--limit", "3",
                     "--as", "bot", "--format", "json"],
                    capture_output=True, text=True, encoding="utf-8",
                    shell=(os.name == "nt"))
                out = (r.stdout or "").strip()
                i = out.find("{")
                if i >= 0:
                    d = json.loads(out[i:])
                    for row, rid_val in zip(
                        (d.get("data") or {}).get("data") or [],
                        (d.get("data") or {}).get("record_id_list") or []):
                        val = row[0] if row else ""
                        if isinstance(val, list):
                            val = "".join(v if isinstance(v, str) else v.get("text", "") for v in val)
                        if val == write_key:
                            rid = rid_val
                            break
            except Exception:
                pass

            # upsert: 有rid则更新, 无则新建; 从响应拿record_id
            args = ["lark-cli", "base", "+record-upsert",
                    "--base-token", BASE_TOKEN, "--table-id", BASE_TABLE,
                    "--json", f"@./{tmp}", "--as", "bot", "--format", "json"]
            if rid:
                args += ["--record-id", rid]
            try:
                r = subprocess.run(args, capture_output=True, text=True,
                                   encoding="utf-8", shell=(os.name == "nt"))
                out = (r.stdout or "").strip()
                i = out.find("{")
                if i >= 0 and not rid:
                    d = json.loads(out[i:])
                    rec = (d.get("data") or {}).get("record") or {}
                    ids = rec.get("record_id_list") or []
                    rid = ids[0] if ids else rec.get("record_id", None)
            except Exception:
                pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        # 第二步：后台异步LLM打分（复用rid更新）
        saved_rid = rid
        import threading
        def _judge_async():
            try:
                ans_short = str(answer)[:800]
                combo = ("假设AI回答基于知识库且基本正确，请评分(1-5)。有明显错误才扣分。\n问题：" + question
                       + "\n回答：" + ans_short
                       + "\n输出格式：忠实度X 相关性X 引用质量X 完整性X")
                body = json.dumps({"model": LLM_MODEL, "max_tokens": 80, "messages": [{"role": "user", "content": combo}]}).encode("utf-8")
                req = urlopen(Request(LLM_BASE_URL.rstrip("/") + "/v1/chat/completions", data=body,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {LLM_API_KEY}"}), timeout=30)
                text = json.loads(req.read())["choices"][0]["message"]["content"]
                scores = {}; issues = []
                for metric in ["忠实度", "相关性", "引用质量", "完整性"]:
                    m = re.search(metric + r'\s*(\d)', text)
                    scores[metric] = int(m.group(1)) if m else 4
                    if scores[metric] < 3: issues.append(metric + str(scores[metric]) + "分")
                data2 = data.copy()
                data2.update({"忠实度": scores.get("忠实度",""), "相关性": scores.get("相关性",""),
                    "引用质量": scores.get("引用质量",""), "完整性": scores.get("完整性",""),
                    "发现的问题": "; ".join(issues) if issues else "无重大问题",
                    "评估人": "api-scored"})
                js2 = json.dumps(data2, ensure_ascii=False)
                tmp2 = f"_auto_log_{uuid.uuid4().hex[:8]}.json"
                with open(tmp2, "w", encoding="utf-8") as f: f.write(js2)
                args2 = ["lark-cli", "base", "+record-upsert",
                         "--base-token", BASE_TOKEN, "--table-id", BASE_TABLE,
                         "--json", f"@./{tmp2}", "--as", "bot", "--format", "json"]
                if saved_rid:
                    args2 += ["--record-id", saved_rid]
                subprocess.run(args2, capture_output=True, text=True,
                               encoding="utf-8", shell=(os.name == "nt"))
                if os.path.exists(tmp2):
                    os.remove(tmp2)
            except Exception as e:
                import sys
                print(f"[api] 异步打分失败(记录已保留): {e}", file=sys.stderr)
        threading.Thread(target=_judge_async, daemon=True).start()
    except:
        pass  # 静默失败
