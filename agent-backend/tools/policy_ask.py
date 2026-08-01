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
from urllib.error import URLError

import lark_oapi as lark

# === 飞书配置(内部使用,已内置) ===
APP_ID = "example-value-0063"
APP_SECRET = "example-value-0011"
INDEX_TOKEN = "exampleToken000000000000012"

TMP_DIR = Path(__file__).parent / "_tmp_download"
CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_TTL = 86400  # 省页缓存24小时

PROVINCES = {
    "蒙西": "exampleToken000000000000014",
    "宁夏": "exampleToken000000000000016",
    "甘肃": "exampleToken000000000000018",
}
# 省份别名(只收无歧义别名, 单字"宁"/"甘"会误路由)
PROVINCE_ALIASES = {
    "蒙西": ["蒙西", "内蒙古", "内蒙", "蒙西电网"],
    "宁夏": ["宁夏", "宁夏省"],
    "甘肃": ["甘肃", "甘肃省", "陇"],
}

# 跨省对比关键词
CROSS_PROVINCE_KW = ["西北", "三省", "跨省", "对比", "哪个省", "投哪里", "选哪", "更适合", "回本"]
CROSS_PROVINCE_TOKEN = ""
ANYSEARCH_API_KEY = ""

# === LLM 配置 ===
LLM_BASE_URL = "http://qileerouter.jd-ecenter.com"
LLM_API_KEY = "example-value-0013"
LLM_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = "你是储能电力交易投研知识库问答助手。基于检索信息回答投研问题。规则: 1.先给结论，再展开关键数值和约束。2.结论带依据(用文件名或政策名称,不暴露URL)。3.信息不足如实说明,不编造数值。4.风险提醒放末尾。5.不输出URL。"

GENERAL_PROMPT = "你是储能电力交易投研助手。用户的问题在知识库和联网搜索中均未找到确切信息。请基于你的通用知识给出最佳回答。规则: 1.开头明确标注'以下基于AI通用知识，非最新政策数据，仅供参考'。2.给出方向性回答，不含具体数值（因为可能过时）。3.建议用户查阅官方文件确认。4.保持简洁。5.不要在答案中输出任何URL链接。"

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
        "max_tokens": 800,
        "stream": on_token is not None,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")

    api_url = LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"

    try:
        req = Request(api_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
        resp = urlopen(req, timeout=60)

        if on_token is None:
            # 非流式模式
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        else:
            # 流式模式：解析 SSE
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
    except (URLError, TimeoutError) as e:
        safe_context = re.sub(r'https?://\S+', '', context)
        safe_context = re.sub(r'\n{3,}', '\n\n', safe_context).strip()
        return f"[LLM调用失败: {e}]\n\n{safe_context}"
    except (KeyError, IndexError, json.JSONDecodeError):
        safe_context = re.sub(r'https?://\S+', '', context)
        return safe_context.strip()


def _llm_summarize_general(question, on_token=None):
    """LLM 通用知识兜底（知识库+联网都 miss 时使用），支持流式输出"""
    prompt = f"用户问题: {question}"

    body = json.dumps({
        "model": LLM_MODEL,
        "max_tokens": 800,
        "stream": on_token is not None,
        "messages": [
            {"role": "system", "content": GENERAL_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")

    api_url = LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"

    try:
        req = Request(api_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
        resp = urlopen(req, timeout=60)

        if on_token is None:
            # 非流式模式
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        else:
            # 流式模式：解析 SSE
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
    except (URLError, TimeoutError) as e:
        return f"[LLM调用失败: {e}]\n\n抱歉，无法获取回答。"
    except (KeyError, IndexError, json.JSONDecodeError):
        return "抱歉，无法生成回答。"


def _parse_sections(text):
    """解析省页为 [{title, aliases, body}]."""
    sections = []
    cur = None
    for line in text.split("\n"):
        m = re.match(r"^(#{2,3}) (.+)$", line)
        if m:
            if cur:
                sections.append(cur)
            cur = {"title": m.group(2).strip(), "lines": [], "aliases": []}
        elif cur:
            cur["lines"].append(line)
            am = re.match(r"\s*-\s*别名[:：]\s*(.+)", line)
            if am:
                cur["aliases"] = [a.strip() for a in re.split(r"[,，、]", am.group(1)) if a.strip()]
    if cur:
        sections.append(cur)
    return sections


def _match_sections(sections, keyword):
    """关键词定位: 别名精确表→标题子串→正文兜底. 返回命中列表."""
    hits = []
    for s in sections:
        if any(keyword in a or a in keyword for a in s["aliases"]):
            hits.append((0, s))
        elif keyword in s["title"]:
            hits.append((1, s))
    if not hits:
        for s in sections:
            if keyword in "\n".join(s["lines"]):
                hits.append((2, s))
    hits.sort(key=lambda x: x[0])
    if hits:
        best = hits[0][0]
        return [s for p, s in hits if p == best]
    return []


def _quick_table(text):
    """抽取速查表."""
    m = re.search(r"(## 速查表.*?)(?=\n## |\Z)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


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


def _anysearch_search(query_text):
    """调用 anysearch HTTP API 做联网搜索兜底. 返回 (文本, URL列表) 或 None."""
    try:
        anysearch_key = ANYSEARCH_API_KEY
        headers = {"Content-Type": "application/json"}
        if anysearch_key:
            headers["Authorization"] = f"Bearer {anysearch_key}"
        body = json.dumps({"query": query_text, "max_results": 5}).encode("utf-8")
        req = Request("https://api.anysearch.com/v1/search", data=body, headers=headers)
        resp = urlopen(req, timeout=8)
        data = json.loads(resp.read())
        results = (data.get("data") or {}).get("results") or []
        if not results:
            return None
        lines = ["[来源: 联网检索(anysearch)]"]
        urls = []
        for r in results[:3]:
            lines.append(f"- {r.get('title','')}: {r.get('snippet','')[:300]}")
            if r.get("url"):
                lines.append(f"  {r['url']}")
                urls.append(r["url"])
        return "\n".join(lines), urls
    except Exception:
        return None


def query(question, allow_web=True):
    # 1. 检测跨省对比意图（优先于单省匹配）
    is_cross = any(kw in question for kw in CROSS_PROVINCE_KW)
    province_count = sum(
        1 for std_name, aliases in PROVINCE_ALIASES.items()
        if any(alias in question for alias in aliases)
    )
    if is_cross and province_count >= 2:
        prov_token = CROSS_PROVINCE_TOKEN
        prov_name = "跨省对比"
        if not prov_token:
            return {
                "province": "跨省对比",
                "context": "跨省对比页 token 未配置（设 KB_ASK_CROSS_PROVINCE_TOKEN 环境变量）。",
                "sources": [], "as_of": None, "status": None,
                "source_type": "wiki",
            }
        prov_path = _download(prov_token)
        prov_text = _read(prov_path)
        m = re.search(r"as_of:\s*(\S+)", prov_text)
        as_of = m.group(1) if m else "未知"
        m = re.search(r"status:\s*(.+)", prov_text)
        status = m.group(1).strip() if m else "草稿"
        # 跨省对比页是聚合页，只传关键表格，不传全文
        context = _cross_province_summary(prov_text)
        return {
            "province": prov_name,
            "context": context,
            "sources": [],
            "as_of": as_of, "status": status,
            "source_type": "wiki",
        }

    # 2. 匹配单省份 (含别名)
    matched = None
    for std_name, aliases in PROVINCE_ALIASES.items():
        for alias in aliases:
            if alias in question:
                matched = (std_name, PROVINCES[std_name])
                break
        if matched:
            break

    # 3. 未匹配省份 → 跨省或 anysearch 兜底
    if not matched:
        if is_cross:
            prov_token = CROSS_PROVINCE_TOKEN
            prov_name = "跨省对比"
            if not prov_token:
                return {
                    "province": "跨省对比",
                    "context": "跨省对比页 token 未配置（设 KB_ASK_CROSS_PROVINCE_TOKEN 环境变量）。",
                    "sources": [], "as_of": None, "status": None,
                    "source_type": "wiki",
                }
            prov_path = _download(prov_token)
            prov_text = _read(prov_path)
            m = re.search(r"as_of:\s*(\S+)", prov_text)
            as_of = m.group(1) if m else "未知"
            m = re.search(r"status:\s*(.+)", prov_text)
            status = m.group(1).strip() if m else "草稿"
            context = _cross_province_summary(prov_text)
            return {
                "province": prov_name,
                "context": context,
                "sources": [],
                "as_of": as_of, "status": status,
                "source_type": "wiki",
            }
        else:
            # wiki miss (未识别省份), 尝试 anysearch 兜底
            web_sources = []
            if allow_web:
                web_result = _anysearch_search(question)
                if web_result:
                    web_text, web_urls = web_result
                    if web_urls:
                        return {
                            "province": None,
                            "context": web_text,
                            "sources": web_urls, "as_of": None, "status": None,
                            "source_type": "web",
                        }
            # 联网也 miss → LLM 通用知识兜底
            return {
                "province": None,
                "context": "",
                "sources": [], "as_of": None, "status": None,
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

    # 跨省对比页→精简
    if prov_name == "跨省对比":
        context = _cross_province_summary(prov_text)
        return {
            "province": prov_name,
            "context": context,
            "sources": [],
            "as_of": as_of, "status": status,
            "source_type": "wiki",
        }

    # 3. 从省页 section 别名/标题定位关键词 (替代硬编码 market_kw)
    sections = _parse_sections(prov_text)
    # 提取问题中的关键词(去掉省份名/别名/常见停用词)
    clean = question
    for aliases in PROVINCE_ALIASES.values():
        for a in aliases:
            clean = clean.replace(a, "")
    keywords = [w for w in re.split(r"[，,。．\s]+", clean) if len(w) >= 2]
    if not keywords:
        keywords = [clean.strip()]

    hits = []
    for kw in keywords:
        hits.extend(_match_sections(sections, kw))
    # 去重
    seen = set()
    hits = [s for s in hits if not (s["title"] in seen or seen.add(s["title"]))]

    if not hits:
        # wiki section miss → 用速查表兜底
        qt = _quick_table(prov_text)
        if qt:
            # 提取省页中所有源文件 token（去重）
            all_tokens = re.findall(r"token=([A-Za-z0-9]{15,})", prov_text)
            wiki_tokens = set(PROVINCES.values()) | {INDEX_TOKEN, CROSS_PROVINCE_TOKEN}
            sources = list(dict.fromkeys(t for t in all_tokens if t not in wiki_tokens))
            return {
                "province": prov_name,
                "context": f"知识库暂无精确匹配此问题的 section，以下是 {prov_name} 省页速查表，请基于此回答概述性问题:\n\n{qt}",
                "sources": [f"https://example-value-0071/file/{t}" for t in sources[:5]],
                "as_of": as_of,
                "status": status,
                "source_type": "wiki",
            }
        # 速查表也没有 → 联网兜底
        if allow_web:
            web_result = _anysearch_search(question)
            if web_result:
                web_text, web_urls = web_result
                if web_urls:
                    return {
                        "province": prov_name,
                        "context": f"知识库暂无此信息({prov_name}页可查 section)，以下为联网检索结果:\n{web_text}",
                        "sources": web_urls,
                        "as_of": as_of,
                        "status": status + " +联网检索",
                        "source_type": "web",
                    }

        # 联网也 miss → LLM 通用知识兜底
        return {
            "province": prov_name,
            "context": f"知识库暂无此信息({prov_name}页)。请基于通用知识回答，并标注为非知识库内容。",
            "sources": [],
            "as_of": as_of,
            "status": status,
            "source_type": "llm_general",
        }

    qt = _quick_table(prov_text)
    blocks = []
    if qt:
        blocks.append(qt + "\n")
    for s in hits:
        body = "\n".join(l for l in s["lines"] if l.strip()
                         and not l.strip().startswith("- 别名"))
        blocks.append(f"[{prov_name}·{s['title']}]\n{body}")

    # 追加相关版本链条目
    for kw in keywords:
        evo = _evolution_entries(prov_text, kw)
        if evo:
            blocks.append(f"## 相关参数演变\n{evo}")
            break

    context = "\n\n".join(blocks)

    # sources: 从全页筛与命中 section 相关的文件URL
    # (URL集中在文件索引表格, 不在section正文, 需用别名/标题做过滤器)
    filter_kw = set()
    for s in hits:
        filter_kw.add(s["title"])
        filter_kw.update(s["aliases"])
        for part in re.split(r"[()（）\s]+", s["title"]):
            if len(part) >= 2:
                filter_kw.add(part)
    sources = []
    # 1) 文件索引表: 同行含 filter_kw 的完整URL
    lines = prov_text.split("\n")
    for line in lines:
        urls = re.findall(r"https://pfcip80h4d\.feishu\.cn/file/([A-Za-z0-9]+)", line)
        if urls and any(kw in line for kw in filter_kw):
            sources.extend(urls)
    # 2) 命中 section 正文里的 token=XXX 引用
    for s in hits:
        for line in s["lines"]:
            tokens = re.findall(r"token=([A-Za-z0-9]{15,})", line)
            sources.extend(tokens)
    # 去重
    sources = list(dict.fromkeys(sources))

    # 过滤掉 wiki 页本身的 token（省页索引、跨省对比页等）
    wiki_tokens = set(PROVINCES.values()) | {INDEX_TOKEN, CROSS_PROVINCE_TOKEN}
    sources = [t for t in sources if t not in wiki_tokens]

    return {
        "province": prov_name,
        "context": context,
        "sources": [f"https://example-value-0071/file/{t}" for t in sources[:5]],
        "as_of": as_of,
        "status": status,
        "source_type": "wiki",
    }


def ask(question, allow_web=True, on_token=None):
    result = query(question, allow_web=allow_web)
    source_type = result.get("source_type", "wiki")

    # 三级兜底: wiki → web → llm_general
    if source_type == "llm_general":
        answer = _llm_summarize_general(question, on_token=on_token)
        reminders = ["以下基于AI通用知识，非知识库内容，仅供参考"]
        _log_to_base(question, answer, result.get("province"), "N/A", "N/A", [])
        return {
            "answer": answer,
            "sources": result["sources"],
            "timeliness": None,
            "reminders": reminders,
            "source_type": "llm_general",
        }

    if source_type == "web":
        answer = _llm_summarize(question, result["context"], result.get("as_of"), result.get("status"), on_token=on_token)
        reminders = ["以上信息来自联网检索，非知识库预置内容，请核实时效性"]
        if result.get("province") is None:
            reminders.append("未识别省份")
        _log_to_base(question, answer, result.get("province"), result.get("as_of"), result.get("status"), result["context"])
        return {
            "answer": answer,
            "sources": result["sources"],
            "timeliness": {
                "province": result.get("province"),
                "as_of": result.get("as_of"),
                "status": result.get("status"),
            } if result.get("province") else None,
            "reminders": reminders,
            "source_type": "web",
        }

    # source_type == "wiki" (正常路径)
    if result["province"] is None:
        answer = _llm_summarize(question, result["context"], None, None, on_token=on_token)
        _log_to_base(question, answer, None, "N/A", "N/A", [])
        return {
            "answer": answer,
            "sources": result["sources"],
            "timeliness": None,
            "reminders": ["未识别省份"],
            "source_type": "wiki",
        }

    answer = _llm_summarize(question, result["context"], result["as_of"], result["status"], on_token=on_token)

    reminders = []
    if result["status"] and "待" in result["status"]:
        reminders.append(f"结论status={result['status']}, 待人复核确认")

    _log_to_base(question, answer, result["province"], result["as_of"], result["status"], result["context"])

    return {
        "answer": answer,
        "sources": result["sources"],
        "timeliness": {
            "province": result["province"],
            "as_of": result["as_of"],
            "status": result["status"],
        },
        "reminders": reminders,
        "source_type": "wiki",
    }


# === Base 自动记录（可选：未内置 BASE_TOKEN / BASE_TABLE 则跳过日志） ===
BASE_TOKEN = ""
BASE_TABLE = ""

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
