"""按应用和终端用户隔离的中台访问令牌内存缓存。"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class _TokenEntry:
    value: str
    expires_at: float


class MiddlePlatformTokenCache:
    def __init__(self, *, refresh_skew_seconds: int = 60):
        self._refresh_skew_seconds = refresh_skew_seconds
        self._entries: dict[tuple[str, str], _TokenEntry] = {}

    def get(self, key: tuple[str, str]) -> str | None:
        entry = self._entries.get(key)
        if entry is None or entry.expires_at - time.time() <= self._refresh_skew_seconds:
            return None
        return entry.value

    def put(self, key: tuple[str, str], token: str, expires_in: int) -> None:
        self._entries[key] = _TokenEntry(token, time.time() + expires_in)

    def delete(self, key: tuple[str, str]) -> None:
        self._entries.pop(key, None)


middle_platform_token_cache = MiddlePlatformTokenCache()
