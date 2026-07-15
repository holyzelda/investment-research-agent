"""
kb-ask-api: 储能投研知识库问答服务
用飞书 Python SDK (lark_oapi) 替代 lark-cli, 纯 Python 零 npm 依赖。
"""

import json
import re
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

import lark_oapi as lark

# === 飞书配置(内部使用,已内置) ===
APP_ID = "example-value-0063"
APP_SECRET = "example-value-0011"
INDEX_TOKEN = "exampleToken000000000000012"

TMP_DIR = Path(__file__).parent / "_tmp_download"

PROVINCES = {
    "蒙西": "exampleToken000000000000014",
    "宁夏": "exampleToken000000000000016",
    "甘肃": "exampleToken000000000000018",
}

# === LLM 配置(已内置, 环境变量可覆盖) ===
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
    """用飞书 SDK 下载文件, 返回本地路径"""
    TMP_DIR.mkdir(exist_ok=True)
    path = TMP_DIR / token[:20]

    client = _get_client()
    req = lark.BaseRequest.builder() \
        .http_method(lark.HttpMethod.GET) \
        .uri(f"/open-apis/drive/v1/files/{token}/download") \
        .token_types({lark.AccessTokenType.TENANT}) \
        .build()

    resp = client.request(req)
    if not resp.success():
        raise RuntimeError(f"下载失败(token={token[:12]}...): code={resp.code}, msg={resp.msg}")

    path.write_bytes(resp.raw.content)
    return str(path)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _llm_summarize(question, context, as_of, status):
    # 剥掉内部token和URL, 只留文件名(不暴露给用户)
    safe_context = re.sub(r'token=[A-Za-z0-9]{15,}', '', context)
    safe_context = re.sub(r'https://pfcip80h4d\.feishu\.cn/file/[A-Za-z0-9]+', '', safe_context)
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


def query(question):
    index_path = _download(INDEX_TOKEN)
    index_text = _read(index_path)

    matched = None
    for name, tok in PROVINCES.items():
        if name in question:
            matched = (name, tok)
            break

    if not matched:
        return {
            "province": None,
            "context": f"未识别省份。覆盖: {list(PROVINCES.keys())}。",
            "sources": [], "as_of": None, "status": None,
        }

    prov_name, prov_token = matched
    prov_path = _download(prov_token)
    prov_text = _read(prov_path)

    m = re.search(r"as_of:\s*(\S+)", prov_text)
    as_of = m.group(1) if m else "未知"
    m = re.search(r"status:\s*(.+)", prov_text)
    status = m.group(1).strip() if m else "草稿"

    market_kw = {
        "中长期": ["中长期", "双边", "日融合"],
        "现货": ["现货", "日前", "实时", "节点电价"],
        "容量补偿": ["容量补偿", "容量电价", "容量电费"],
        "调峰": ["调峰", "深调峰", "启停"],
        "调频": ["调频", "AGC"],
        "需求响应": ["需求响应", "需求侧"],
    }
    relevant = [m for m, kws in market_kw.items() if any(k in question for k in kws)]

    if not relevant:
        return {
            "province": prov_name,
            "context": f"未识别市场关键词。{prov_name}页覆盖: {list(market_kw.keys())}。",
            "sources": [], "as_of": as_of, "status": status,
        }

    blocks = []
    for market in relevant:
        pattern = rf"(### {market}.*?)(?=\n### |\n---|\Z)"
        m = re.search(pattern, prov_text, re.DOTALL)
        if m:
            block_text = m.group(1).strip()
            # 保留block全文(含子行参数值), 只去掉别名行(冗余)和空行
            lines = [l for l in block_text.split("\n") if l.strip() and not l.strip().startswith("- 别名")]
            blocks.append(f"[{prov_name}·{market}]\n" + "\n".join(lines[:30]))  # 上限30行防过长
        else:
            blocks.append(f"[{prov_name}·{market}] block未找到")

    context = "\n\n".join(blocks)
    sources = re.findall(r"https://pfcip80h4d\.feishu\.cn/file/([A-Za-z0-9]+)", prov_text)

    return {
        "province": prov_name,
        "context": context,
        "sources": [f"https://example-value-0071/file/{t}" for t in sources[:5]],
        "as_of": as_of,
        "status": status,
    }


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


def main():
    """
    简单的测试入口
    """
    question = "宁夏最新中长期政策"
    print(f"提问: {question}\n{'-' * 50}")

    result = ask(question)

    print(f"回答: {result['answer']}")
    print(f"\n来源: {result['sources']}")
    print(f"时效信息: {result['timeliness']}")
    if result['reminders']:
        print(f"提醒: {result['reminders']}")


# --- 程序入口 ---
if __name__ == "__main__":
    main()