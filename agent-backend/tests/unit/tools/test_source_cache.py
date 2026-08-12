"""源文件磁盘缓存的行为契约。

source_cache 是零配置依赖模块，可直接 import，不需要 policy_ask 那套
monkeypatch-settings-再-import 的 fixture。
"""
import json
import os
import time

import pytest

from tools import source_cache


TOKEN = "exampleToken000000000000078"
CONTENT = b"%PDF-1.7\n fake pdf bytes \x00\xff"
FILENAME = "20241217_蒙西_容量电费实施细则(试行).pdf"
CONTENT_TYPE = "application/pdf"
TTL = 7 * 86400


def _write_sample(cache_dir, token=TOKEN, content=CONTENT):
    source_cache.write(cache_dir, token, content, FILENAME, CONTENT_TYPE)


def test_write_then_read_round_trips_binary_and_chinese_filename(tmp_path):
    _write_sample(tmp_path)

    result = source_cache.read(tmp_path, TOKEN, TTL)

    assert result == (CONTENT, FILENAME, CONTENT_TYPE)


def test_read_returns_none_for_missing_token(tmp_path):
    assert source_cache.read(tmp_path, TOKEN, TTL) is None


def test_read_returns_none_after_ttl_expires(tmp_path):
    _write_sample(tmp_path)
    meta_path = tmp_path / f"{TOKEN}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["cached_at"] = time.time() - TTL - 1
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    assert source_cache.read(tmp_path, TOKEN, TTL) is None


def test_ttl_uses_cached_at_not_file_mtime(tmp_path):
    """命中时会 utime 刷新访问时间；若拿 mtime 当写入时间，过期判定会永远不触发。"""
    _write_sample(tmp_path)
    meta_path = tmp_path / f"{TOKEN}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["cached_at"] = time.time() - TTL - 1
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    # 把两个文件的 mtime/atime 都刷成"刚刚"，模拟被 evict 触碰过。
    now = time.time()
    for path in (tmp_path / f"{TOKEN}.bin", meta_path):
        os.utime(path, (now, now))

    assert source_cache.read(tmp_path, TOKEN, TTL) is None


def test_read_returns_none_when_meta_missing(tmp_path):
    _write_sample(tmp_path)
    (tmp_path / f"{TOKEN}.json").unlink()

    assert source_cache.read(tmp_path, TOKEN, TTL) is None


def test_read_returns_none_when_meta_corrupted(tmp_path):
    """meta 损坏必须降级为未命中，不能把异常抛给下载主路径。"""
    _write_sample(tmp_path)
    (tmp_path / f"{TOKEN}.json").write_text("{ not json", encoding="utf-8")

    assert source_cache.read(tmp_path, TOKEN, TTL) is None


def test_read_hit_refreshes_access_time_for_eviction(tmp_path):
    _write_sample(tmp_path)
    bin_path = tmp_path / f"{TOKEN}.bin"
    stale = time.time() - 10_000
    os.utime(bin_path, (stale, stale))

    assert source_cache.read(tmp_path, TOKEN, TTL) is not None
    assert bin_path.stat().st_atime > stale


def test_write_leaves_no_tmp_files(tmp_path):
    _write_sample(tmp_path)

    assert not list(tmp_path.glob("*.tmp"))
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        f"{TOKEN}.bin",
        f"{TOKEN}.json",
    ]


def test_write_creates_missing_cache_dir(tmp_path):
    nested = tmp_path / "source_files"

    _write_sample(nested)

    assert source_cache.read(nested, TOKEN, TTL) is not None


def test_write_overwrites_previous_content(tmp_path):
    _write_sample(tmp_path)
    _write_sample(tmp_path, content=b"newer bytes")

    content, _filename, _content_type = source_cache.read(tmp_path, TOKEN, TTL)
    assert content == b"newer bytes"


@pytest.mark.parametrize("token", ["", "   ", "../escape", "a/b", "a\\b", "with space"])
def test_unsafe_tokens_never_touch_disk(tmp_path, token):
    """token 直接拼路径，非法字符必须在写入前就被挡掉。"""
    source_cache.write(tmp_path, token, CONTENT, FILENAME, CONTENT_TYPE)

    assert source_cache.read(tmp_path, token, TTL) is None
    assert not list(tmp_path.rglob("*.bin"))


def test_evict_removes_oldest_accessed_until_under_limit(tmp_path):
    for index, token in enumerate(["Aaa000", "Bbb111", "Ccc222"]):
        source_cache.write(tmp_path, token, b"x" * 100, FILENAME, CONTENT_TYPE)
        stamp = time.time() - (10_000 - index * 1000)  # Aaa 最旧，Ccc 最新
        for suffix in (".bin", ".json"):
            os.utime(tmp_path / f"{token}{suffix}", (stamp, stamp))

    freed = source_cache.evict(tmp_path, max_bytes=250)

    assert freed == 100
    assert not (tmp_path / "Aaa000.bin").exists()
    assert (tmp_path / "Bbb111.bin").exists()
    assert (tmp_path / "Ccc222.bin").exists()


def test_evict_removes_meta_alongside_binary(tmp_path):
    """只删 .bin 会留下孤儿 .json，下次 read 仍判为未命中但目录越积越脏。"""
    source_cache.write(tmp_path, "Aaa000", b"x" * 100, FILENAME, CONTENT_TYPE)

    source_cache.evict(tmp_path, max_bytes=0)

    assert not list(tmp_path.iterdir())


def test_evict_keeps_everything_when_under_limit(tmp_path):
    _write_sample(tmp_path)

    assert source_cache.evict(tmp_path, max_bytes=10 * 1024 * 1024) == 0
    assert source_cache.read(tmp_path, TOKEN, TTL) is not None


def test_evict_tolerates_missing_directory(tmp_path):
    assert source_cache.evict(tmp_path / "never-created", max_bytes=1) == 0
