"""政策源文件磁盘缓存：纯文件操作，零配置依赖。

刻意保持只用 ``json``/``os``/``pathlib``/``time``，不 import
``app.core.config.settings`` 或 ``lark_oapi``。原因同 ``tools.policy_refs``：
``tools.policy_ask`` 在模块顶层就跑 ``get_settings()`` 并强校验五省 token，
任何 import 都要完整飞书配置；把缓存逻辑拆出来，单测可直接 import。

缓存是加速层，绝不能成为新的故障源——任何异常一律当"未命中"，退回真实下载。
每个源文件落两份：``{token}.bin``（二进制正文）与 ``{token}.json``（元数据），
分开存是为了读文件名/类型时不必解析整个 blob。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

# 缓存内部键，避免与业务字段混淆。
_META_FILENAME = "filename"
_META_CONTENT_TYPE = "content_type"
_META_CACHED_AT = "cached_at"

# token 直接参与拼路径，必须限死字符集。调用方（fetch_source_file）已先过白名单，
# 这里是纵深防御：``..`` 或分隔符混进来会写到缓存目录之外。
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_token(token):
    token = str(token or "").strip()
    return token if _TOKEN_RE.match(token) else ""


def _bin_path(cache_dir, token):
    return Path(cache_dir) / f"{token}.bin"


def _meta_path(cache_dir, token):
    return Path(cache_dir) / f"{token}.json"


def read(cache_dir, token, ttl):
    """命中且未过期返回 ``(content, filename, content_type)``，否则返回 None。

    TTL 判定用 meta 里的 ``cached_at``，**不用文件 mtime**——命中时下面会
    ``os.utime`` 刷新访问时间供 evict 使用，拿 mtime 当写入时间会算错过期。
    """
    token = _safe_token(token)
    if not token:
        return None
    bin_path = _bin_path(cache_dir, token)
    meta_path = _meta_path(cache_dir, token)
    try:
        if not bin_path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached_at = float(meta.get(_META_CACHED_AT) or 0)
        if ttl and (time.time() - cached_at) >= ttl:
            return None
        content = bin_path.read_bytes()
        # 命中即刷新访问时间，让 evict 能按"最近最少使用"淘汰。
        now = time.time()
        os.utime(bin_path, (now, now))
        os.utime(meta_path, (now, now))
        return (
            content,
            str(meta.get(_META_FILENAME) or ""),
            str(meta.get(_META_CONTENT_TYPE) or "application/octet-stream"),
        )
    except Exception:
        # meta 损坏、磁盘异常、并发删除——一律当未命中。
        return None


def write(cache_dir, token, content, filename, content_type):
    """把源文件写入缓存。失败静默吞掉（缓存写不进只是没加速，不该报错）。

    原子写：先写 ``.tmp`` 再 ``os.replace``（Windows 上同样原子）。多个请求
    并发下载同一文件时，读方绝不会拿到半个文件。
    """
    token = _safe_token(token)
    if not token or content is None:
        return
    directory = Path(cache_dir)
    bin_path = _bin_path(cache_dir, token)
    meta_path = _meta_path(cache_dir, token)
    bin_tmp = bin_path.with_suffix(".bin.tmp")
    meta_tmp = meta_path.with_suffix(".json.tmp")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        bin_tmp.write_bytes(content)
        meta_tmp.write_text(
            json.dumps(
                {
                    _META_FILENAME: str(filename or ""),
                    _META_CONTENT_TYPE: str(content_type or "application/octet-stream"),
                    _META_CACHED_AT: time.time(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        # 先落正文再落元数据：read() 要求两者都在才算命中，元数据后到能避免
        # 读到"有正文没元数据"的中间态。
        os.replace(bin_tmp, bin_path)
        os.replace(meta_tmp, meta_path)
    except Exception:
        for tmp in (bin_tmp, meta_tmp):
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass


def evict(cache_dir, max_bytes):
    """目录内 ``.bin`` 总大小超过 ``max_bytes`` 时，按访问时间最旧优先删除。

    返回释放的字节数。``.bin`` 与 ``.json`` 成对删除，避免留下孤儿元数据。
    防御性设计：正常容量下不会触发，异常一律吞掉不影响主流程。
    """
    directory = Path(cache_dir)
    try:
        if not directory.exists():
            return 0
        entries = []
        total = 0
        for bin_path in directory.glob("*.bin"):
            try:
                stat = bin_path.stat()
            except Exception:
                continue
            entries.append((stat.st_atime, stat.st_size, bin_path))
            total += stat.st_size
        if total <= max_bytes:
            return 0
        # 最旧访问的先删，直到回落到上限之下。
        entries.sort(key=lambda item: item[0])
        freed = 0
        for _atime, size, bin_path in entries:
            if total - freed <= max_bytes:
                break
            meta_path = bin_path.with_suffix(".json")
            for path in (bin_path, meta_path):
                try:
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass
            freed += size
        return freed
    except Exception:
        return 0
