"""
kb-ask-api: 储能投研知识库问答服务
用飞书 Python SDK (lark_oapi) 替代 lark-cli, 纯 Python 零 npm 依赖。
v2.1: 单文件整合版，保留现有对外接口，加入别名路由、section 定位、跨省对比、缓存和更完整的来源抽取。
"""

import json
import re
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

import lark_oapi as lark

# 加载 .env（保持单文件入口行为）
_env_path = Path(__file__).with_name(".env")
if _env_path.exists():
    with _env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# === 飞书配置(保持当前实现，不改成从环境变量读取) ===
APP_ID = "example-value-0063"
APP_SECRET = "example-value-0011"
INDEX_TOKEN = "exampleToken000000000000012"

TMP_DIR = Path(__file__).parent / "_tmp_download"
CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_TTL = 3600  # 省页缓存1小时

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

# 问题停用词：用于 section 定位时去掉无意义词
QUESTION_STOPWORDS = {
    "请问", "麻烦", "现在", "最新", "最近", "当前", "今年", "明年", "哪年", "哪个", "哪家",
    "多少", "多少钱", "什么", "怎么", "如何", "是否", "能否", "有没有", "可以", "能不能",
    "一个", "一度电", "一下", "大概", "大约", "左右", "情况", "政策", "规则", "参数", "结算",
}

# 兜底市场关键词(保留旧版语义)
MARKET_KW = {
    "中长期": ["中长期", "双边", "日融合", "多边交易"],
    "现货": ["现货", "日前", "实时", "节点电价", "LMP"],
    "容量补偿": ["容量补偿", "容量电价", "容量电费", "容量"],
    "调峰": ["调峰", "深调峰", "启停"],
    "调频": ["调频", "AGC", "APC", "调频里程"],
    "需求响应": ["需求响应", "需求侧"],
}

# === LLM 配置(保持当前实现) ===
LLM_BASE_URL = os.environ.get("KB_ASK_LLM_URL", "http://qileerouter.jd-ecenter.com")
LLM_API_KEY = os.environ.get("KB_ASK_LLM_API_KEY", "example-value-0013")
LLM_MODEL = os.environ.get("KB_ASK_LLM_MODEL", "deepseek-v4-flash")

SYSTEM_PROMPT = "你是储能电力交易投研知识库的问答助手。基于 wiki 认知层检索到的信息回答投研问题。规则: 1.直接回答,含关键数值和约束。2.时效差异按年份区分。3.结论带依据(用文件名,不暴露原始token)。4.信息不足如实说'知识库暂无'。5.版本更替/跨市场互斥/结论待确认等风险在末尾提醒。6.简洁,不展开wiki没有的内容。7.引用的文件URL直接输出,不转成token格式。"

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


def _download(token):
    """下载飞书文件, 带本地缓存, 返回本地路径。"""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{token}.md"
    if cache_path.exists():
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
        if cache_path.exists():  # 下载失败但旧缓存可用
            return str(cache_path)
        raise RuntimeError(f"下载失败(token={token[:12]}...): code={resp.code}, msg={resp.msg}")

    cache_path.write_bytes(resp.raw.content)
    return str(cache_path)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _strip_internal_tokens(text):
    """剥掉内部 token 标识, 保留完整 URL 给用户点击。"""
    text = re.sub(r"token=[A-Za-z0-9]{15,}", "", text)
    text = re.sub(r"https://pfcip80h4d\.feishu\.cn/file/[A-Za-z0-9]+", "", text)
    return text


def _llm_summarize(question, context, as_of, status):
    safe_context = _strip_internal_tokens(context)
    prompt = f"用户问题: {question}\n\n检索到的信息:\n{safe_context}\n\n时效: as_of={as_of}, status={status}"

    body = json.dumps({
        "model": LLM_MODEL,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")

    api_url = LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"
    req = Request(api_url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {LLM_API_KEY}")

    try:
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except URLError as e:
        return f"[LLM调用失败: {e}]\n\n{context}"
    except (KeyError, IndexError, json.JSONDecodeError):
        return context


def _parse_sections(text):
    """解析省页为 [{title, aliases, body, lines}]."""
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
    """关键词定位: 别名精确表→标题子串→正文兜底。"""
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
    """抽取速查表。"""
    m = re.search(r"(## 速查表.*?)(?=\n## |\Z)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _evolution_entries(text, keyword):
    """抽取参数演变日志中相关条目。"""
    m = re.search(r"## 参数演变日志.*?(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        return ""
    blocks = re.findall(r"(### .+?)(?=\n### |\Z)", m.group(0), re.DOTALL)
    rel = [b.strip() for b in blocks if keyword in b.split("\n")[0]]
    return "\n\n".join(rel)


def _extract_keywords(question):
    clean = question
    for aliases in PROVINCE_ALIASES.values():
        for a in aliases:
            clean = clean.replace(a, "")
    parts = [w.strip() for w in re.split(r"[，,。．\s]+", clean) if w.strip()]
    keywords = []
    for w in parts:
        if len(w) < 2:
            continue
        if w in QUESTION_STOPWORDS:
            continue
        keywords.append(w)
    if not keywords:
        tail = clean.strip()
        if tail:
            keywords = [tail]
    return keywords


def _legacy_market_hits(question, sections):
    hits = []
    for market, kws in MARKET_KW.items():
        if any(k in question for k in kws):
            hits.extend(_match_sections(sections, market))
    # 去重
    seen = set()
    unique = []
    for s in hits:
        if s["title"] in seen:
            continue
        seen.add(s["title"])
        unique.append(s)
    return unique


def _build_context_for_province(question, prov_name, prov_text, cross_mode=False):
    """根据问题从单省页抽取上下文。"""
    sections = _parse_sections(prov_text)
    keywords = _extract_keywords(question)

    hits = []
    for kw in keywords:
        hits.extend(_match_sections(sections, kw))

    # 去重
    seen = set()
    hits = [s for s in hits if not (s["title"] in seen or seen.add(s["title"]))]

    # 没命中时, 用旧版市场关键词兜底
    if not hits:
        hits = _legacy_market_hits(question, sections)

    # 交叉对比时, 允许更宽一些: 仍然没命中就把标准市场段都带上
    if not hits and cross_mode:
        for market in MARKET_KW:
            hits.extend(_match_sections(sections, market))
        seen = set()
        hits = [s for s in hits if not (s["title"] in seen or seen.add(s["title"]))]

    if not hits:
        section_list = "\n".join(
            f"  {'  ' if s.get('level') else ''}{s['title']}"
            + (f"  [别名: {', '.join(s['aliases'])}]" if s.get('aliases') else "")
            for s in sections
        )
        return {
            "province": prov_name,
            "context": f"知识库暂无此信息({prov_name}页可查 section):\n{section_list}\n\n→ 换关键词重试, 或请求回 raw 源文件搜索。",
            "sources": [],
            "as_of": None,
            "status": None,
        }

    qt = _quick_table(prov_text)
    blocks = []
    if qt:
        blocks.append(qt + "\n")

    for s in hits:
        body = "\n".join(
            l for l in s["lines"] if l.strip() and not l.strip().startswith("- 别名")
        )
        blocks.append(f"[{prov_name}·{s['title']}]\n{body}")

    for kw in keywords:
        evo = _evolution_entries(prov_text, kw)
        if evo:
            blocks.append(f"## 相关参数演变\n{evo}")
            break

    context = "\n\n".join(blocks)

    # sources: 从全页筛与命中 section 相关的文件 URL
    filter_kw = set()
    for s in hits:
        filter_kw.add(s["title"])
        filter_kw.update(s["aliases"])
        for part in re.split(r"[()（）\s]+", s["title"]):
            if len(part) >= 2:
                filter_kw.add(part)

    sources = []
    for line in prov_text.split("\n"):
        urls = re.findall(r"https://pfcip80h4d\.feishu\.cn/file/([A-Za-z0-9]+)", line)
        if urls and any(kw in line for kw in filter_kw):
            sources.extend(urls)

    for s in hits:
        for line in s["lines"]:
            tokens = re.findall(r"token=([A-Za-z0-9]{15,})", line)
            sources.extend(tokens)

    # 去重并过滤掉 wiki 页本身的 token
    sources = list(dict.fromkeys(sources))
    wiki_tokens = set(PROVINCES.values()) | {INDEX_TOKEN}
    sources = [t for t in sources if t not in wiki_tokens]

    m = re.search(r"as_of:\s*(\S+)", prov_text)
    as_of = m.group(1) if m else "未知"
    m = re.search(r"status:\s*(.+)", prov_text)
    status = m.group(1).strip() if m else "草稿"

    return {
        "province": prov_name,
        "context": context,
        "sources": [f"https://example-value-0071/file/{t}" for t in sources[:5]],
        "as_of": as_of,
        "status": status,
    }


def _collect_targets(question):
    matched = []
    for std_name, aliases in PROVINCE_ALIASES.items():
        if any(alias in question for alias in aliases):
            matched.append(std_name)

    is_cross = any(kw in question for kw in CROSS_PROVINCE_KW) or len(matched) >= 2
    if is_cross:
        if matched:
            return "跨省对比", matched, True
        return "跨省对比", list(PROVINCES.keys()), True

    if matched:
        return matched[0], [matched[0]], False

    return None, [], False


def query(question):
    index_path = _download(INDEX_TOKEN)
    _ = _read(index_path)

    province_name, targets, cross_mode = _collect_targets(question)

    if not targets:
        return {
            "province": None,
            "context": f"未识别省份。覆盖: {list(PROVINCES.keys())}。",
            "sources": [],
            "as_of": None,
            "status": None,
        }

    if len(targets) > 1 or cross_mode:
        blocks = []
        all_sources = []
        as_of_list = []
        status_list = []
        for prov in targets:
            prov_path = _download(PROVINCES[prov])
            prov_text = _read(prov_path)
            result = _build_context_for_province(question, prov, prov_text, cross_mode=True)
            blocks.append(result["context"])
            all_sources.extend(result["sources"])
            if result.get("as_of"):
                as_of_list.append(f"{prov}:{result['as_of']}")
            if result.get("status"):
                status_list.append(f"{prov}:{result['status']}")
        return {
            "province": province_name,
            "context": "\n\n=====\n\n".join([f"[{prov}]\n{ctx}" for prov, ctx in zip(targets, blocks)]),
            "sources": list(dict.fromkeys(all_sources))[:5],
            "as_of": " | ".join(as_of_list) if as_of_list else "多省汇总",
            "status": " | ".join(status_list) if status_list else "多省汇总",
        }

    prov_name = targets[0]
    prov_path = _download(PROVINCES[prov_name])
    prov_text = _read(prov_path)
    return _build_context_for_province(question, prov_name, prov_text, cross_mode=False)


def ask(question):
    result = query(question)

    if result["province"] is None:
        return {
            "answer": result["context"],
            "sources": [],
            "timeliness": None,
            "reminders": ["未识别省份"],
        }

    answer = _llm_summarize(question, result["context"], result["as_of"], result["status"])

    reminders = []
    if result["status"] and "待" in result["status"]:
        reminders.append(f"结论status={result['status']}, 待人复核确认")

    return {
        "answer": answer,
        "sources": result["sources"],
        "timeliness": {
            "province": result["province"],
            "as_of": result["as_of"],
            "status": result["status"],
        },
        "reminders": reminders,
    }


BANNER = """
╔══════════════════════════════════════╗
║     储能投研知识库问答               ║
║     蒙西 · 宁夏 · 甘肃 + 跨省对比    ║
║     输入 quit 退出                   ║
╚══════════════════════════════════════╝
"""


def main():
    print(BANNER)
    try:
        q = input("\n>> 请输入问题: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n再见")
        return

    if not q:
        print("\n再见")
        return
    if q.lower() in ("quit", "exit", "q"):
        print("\n再见")
        return

    print("...检索中")
    try:
        r = ask(q)
        print(f"\n[答案] {r['answer']}")
        if r.get("sources"):
            print(f"\n[依据]")
            for s in r["sources"]:
                print(f"   {s}")
        if r.get("timeliness"):
            t = r["timeliness"]
            print(f"\n[时效] {t.get('province','')} | as_of={t.get('as_of','')} | {t.get('status','')}")
        if r.get("reminders"):
            for rem in r["reminders"]:
                print(f"[!] {rem}")
    except Exception as e:
        print(f"[出错] {e}")


if __name__ == "__main__":
    main()
