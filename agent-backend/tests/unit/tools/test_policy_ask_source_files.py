"""源文件白名单与代理下载的契约测试。

复用 test_policy_ask_query_refs 的 fixture 手法：policy_ask 顶层就跑 get_settings()
强校验，必须先 monkeypatch settings 再 import。
"""
import importlib
import sys
from types import SimpleNamespace

import pytest


MODULE_NAME = "tools.policy_ask"
DOMAIN = "feishu.example.test"

PROVINCE_PAGE = f"""---
as_of: 2026-07-31
---

## 容量补偿
- 依据: token=exampleToken000000000000078 (容量电费实施细则, 2026-01)

## 依据文件清单

| 文件 | URL | 类型 |
|---|---|---|
| 容量电费实施细则(试行) | https://{DOMAIN}/file/exampleToken000000000000078 | 容量补偿 |
"""

CROSS_PAGE = f"""---
as_of: 2026-07-20
---

## 表3 · 关键参数对比

| 省份 | URL | 容量补偿 |
|---|---|---|
| 蒙西 | https://{DOMAIN}/file/MxPageTokenAAAAAAAAAAAAAAA | 0.28 |
"""


def _settings():
    feishu = SimpleNamespace(
        app_id="cli-test",
        app_secret="secret",
        index_token="IndexPageTokenZZZZZZZZZZZZZ",
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
    return SimpleNamespace(
        policy_ask=SimpleNamespace(
            feishu=feishu,
            llm=llm,
            anysearch=SimpleNamespace(api_key="", tavily_api_key=""),
            base=SimpleNamespace(token="", table=""),
        )
    )


class _FakeResponse:
    """模拟 lark BaseResponse：success() + raw.headers/content。"""

    def __init__(self, content=b"PDF", headers=None, ok=True):
        self.raw = SimpleNamespace(content=content, headers=headers or {})
        self.code = 0 if ok else 1
        self.msg = "ok" if ok else "permission denied"
        self._ok = ok

    def success(self):
        return self._ok


@pytest.fixture
def policy_ask(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.get_settings", lambda: _settings())
    sys.modules.pop(MODULE_NAME, None)
    module = importlib.import_module(MODULE_NAME)
    monkeypatch.setattr(module, "_download", lambda token, no_cache=False: token)
    monkeypatch.setattr(
        module,
        "_read",
        lambda path: CROSS_PAGE if path == module.CROSS_PROVINCE_TOKEN else PROVINCE_PAGE,
    )
    # 每个用例都从冷缓存开始，否则白名单会跨用例串味。
    monkeypatch.setattr(module, "_source_index", {})
    monkeypatch.setattr(module, "_source_index_at", 0.0)
    # 源文件磁盘缓存同理：所有用例共用一个 token，不隔离的话第二个用例会读到
    # 第一个用例缓存的正文，而且会往真实的 tools/_cache 写垃圾。
    monkeypatch.setattr(module, "SOURCE_CACHE_DIR", tmp_path / "source_files")
    yield module
    sys.modules.pop(MODULE_NAME, None)


# --- 白名单 ---


def test_source_index_collects_policy_files_and_excludes_wiki_skeleton(policy_ask):
    index = policy_ask.source_file_index()

    assert "exampleToken000000000000078" in index
    assert index["exampleToken000000000000078"]["title"] == "容量电费实施细则(试行)"
    # 省页/索引页/跨省页自身是知识库骨架，不该可下载
    assert set(index).isdisjoint(set(policy_ask.PROVINCES.values()) | {
        policy_ask.INDEX_TOKEN, policy_ask.CROSS_PROVINCE_TOKEN
    })


def test_source_index_is_cached_between_calls(policy_ask, monkeypatch):
    """白名单每次请求都重解析 6 个省页的话，下载端点会慢得没法用。"""
    calls = []
    monkeypatch.setattr(policy_ask, "_download", lambda token, no_cache=False: calls.append(token) or token)

    policy_ask.source_file_index()
    first = len(calls)
    policy_ask.source_file_index()

    assert first > 0
    assert len(calls) == first, "第二次调用应命中缓存"


def test_source_index_survives_unreadable_province_page(policy_ask, monkeypatch):
    """某个省页下不下来时，其余省的源文件照样可下载。"""
    def flaky_read(path):
        if path == policy_ask.PROVINCES["蒙西"]:
            raise RuntimeError("下载失败")
        return PROVINCE_PAGE

    monkeypatch.setattr(policy_ask, "_read", flaky_read)

    assert "exampleToken000000000000078" in policy_ask.source_file_index()


# --- 下载 ---


def test_fetch_source_file_rejects_token_outside_whitelist(policy_ask):
    """核心安全边界：任意飞书 token 不能经本服务下载公司云盘文件。"""
    assert policy_ask.fetch_source_file("SomeOtherFileTokenXXXXXXXXX") is None
    # 省页自身也不行
    assert policy_ask.fetch_source_file(policy_ask.PROVINCES["蒙西"]) is None
    assert policy_ask.fetch_source_file("") is None


def test_fetch_source_file_returns_content_with_name_and_type(policy_ask, monkeypatch):
    response = _FakeResponse(
        content=b"%PDF-1.7",
        headers={
            "Content-Type": "application/pdf; charset=utf-8",
            "Content-Disposition": "attachment; filename*=UTF-8''%E5%AE%B9%E9%87%8F%E7%94%B5%E8%B4%B9.pdf",
        },
    )
    monkeypatch.setattr(policy_ask, "_get_client", lambda: SimpleNamespace(request=lambda req: response))

    content, filename, content_type = policy_ask.fetch_source_file("exampleToken000000000000078")

    assert content == b"%PDF-1.7"
    assert filename == "容量电费.pdf"
    assert content_type == "application/pdf", "charset 参数不该混进 media_type"


def test_fetch_source_file_falls_back_to_index_title(policy_ask, monkeypatch):
    """飞书没给 Content-Disposition 时用知识库标题，用户至少知道下的是什么。"""
    response = _FakeResponse(content=b"data", headers={"Content-Type": "application/octet-stream"})
    monkeypatch.setattr(policy_ask, "_get_client", lambda: SimpleNamespace(request=lambda req: response))

    _, filename, _ = policy_ask.fetch_source_file("exampleToken000000000000078")

    assert filename == "容量电费实施细则(试行)"


def test_fetch_source_file_reads_plain_filename_header(policy_ask, monkeypatch):
    response = _FakeResponse(headers={"content-disposition": 'attachment; filename="rule.docx"'})
    monkeypatch.setattr(policy_ask, "_get_client", lambda: SimpleNamespace(request=lambda req: response))

    _, filename, _ = policy_ask.fetch_source_file("exampleToken000000000000078")

    # 响应头大小写不敏感：lark 用 dict() 转存后丢了 requests 的这个特性
    assert filename == "rule.docx"


def test_fetch_source_file_raises_on_feishu_failure(policy_ask, monkeypatch):
    response = _FakeResponse(ok=False)
    monkeypatch.setattr(policy_ask, "_get_client", lambda: SimpleNamespace(request=lambda req: response))

    with pytest.raises(RuntimeError):
        policy_ask.fetch_source_file("exampleToken000000000000078")


# --- 磁盘缓存 ---


def _counting_client(policy_ask, monkeypatch, content=b"%PDF-1.7", headers=None):
    """替换飞书 client 并返回调用计数列表。"""
    calls = []
    response = _FakeResponse(
        content=content,
        headers=headers if headers is not None else {"Content-Type": "application/pdf"},
    )

    def request(req):
        calls.append(req)
        return response

    monkeypatch.setattr(policy_ask, "_get_client", lambda: SimpleNamespace(request=request))
    return calls


def test_fetch_source_file_second_call_hits_disk_cache(policy_ask, monkeypatch):
    """飞书下载 2~9MB 的 PDF 要 5~8 秒；同一文件重复点击不该再打网络。"""
    calls = _counting_client(policy_ask, monkeypatch)

    first = policy_ask.fetch_source_file("exampleToken000000000000078")
    second = policy_ask.fetch_source_file("exampleToken000000000000078")

    assert second == first
    assert len(calls) == 1, "第二次调用应命中磁盘缓存"


def test_fetch_source_file_cache_survives_module_reload(policy_ask, monkeypatch, tmp_path):
    """缓存必须跨进程存活：历史咨询记录点开来源也要秒回。"""
    _counting_client(policy_ask, monkeypatch)
    policy_ask.fetch_source_file("exampleToken000000000000078")

    from tools import source_cache

    cached = source_cache.read(
        tmp_path / "source_files", "exampleToken000000000000078", policy_ask.SOURCE_CACHE_TTL
    )
    assert cached is not None
    assert cached[0] == b"%PDF-1.7"


def test_fetch_source_file_can_bypass_cache(policy_ask, monkeypatch):
    """预取与调试需要强制回源，否则缓存里的坏数据没法刷掉。"""
    calls = _counting_client(policy_ask, monkeypatch)

    policy_ask.fetch_source_file("exampleToken000000000000078")
    policy_ask.fetch_source_file("exampleToken000000000000078", use_cache=False)

    assert len(calls) == 2


def test_cache_never_bypasses_whitelist(policy_ask, monkeypatch):
    """白名单校验必须在读缓存之前：文件被移出知识库后就不能再下载。"""
    _counting_client(policy_ask, monkeypatch)
    policy_ask.fetch_source_file("exampleToken000000000000078")

    # 模拟省页更新后该文件不再在白名单里
    monkeypatch.setattr(policy_ask, "source_file_index", lambda force=False: {})

    assert policy_ask.fetch_source_file("exampleToken000000000000078") is None


def test_fetch_source_file_still_works_when_cache_dir_unwritable(policy_ask, monkeypatch):
    """缓存是加速层，写不进去只是没加速，不能变成新的故障源。"""
    calls = _counting_client(policy_ask, monkeypatch)
    # 拿一个已存在的文件当"目录"，mkdir 必然失败
    blocked = policy_ask.SOURCE_CACHE_DIR.parent / "blocker"
    blocked.parent.mkdir(parents=True, exist_ok=True)
    blocked.write_bytes(b"not a dir")
    monkeypatch.setattr(policy_ask, "SOURCE_CACHE_DIR", blocked / "nested")

    content, filename, _ = policy_ask.fetch_source_file("exampleToken000000000000078")

    assert content == b"%PDF-1.7"
    assert filename == "容量电费实施细则(试行)"
    assert len(calls) == 1
