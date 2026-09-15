"""计算失败信息的用户侧呈现规则。

底层执行错误需要保留在日志和任务内部字段中用于排障，但不能沿接口、会话历史
或前端消息把第三方平台名称、错误码和原始响应暴露给用户。
"""
from __future__ import annotations

import re
from typing import Any


_GENERIC_UNAVAILABLE = "测算服务暂时不可用，请稍后重试"
_GENERIC_FAILED = "测算未能完成，请稍后重试"
_GENERIC_CONFIG = "测算服务配置异常，请稍后重试或联系管理员"
_TECHNICAL_CODES = {
    "network_error",
    "network_timeout",
    "unknown",
    "compute_timeout",
    "request_id_mismatch",
    "param_hash_mismatch",
}
_PLATFORM_TEXT = re.compile(r"飞书|feishu|server\s*error|95201", re.IGNORECASE)


def public_calc_error_code(code: Any, message: Any = None) -> str:
    """Return a stable, platform-neutral error code for API consumers."""
    normalized = str(code or "").strip().lower()
    if normalized.startswith("feishu_"):
        if any(part in normalized for part in ("auth", "permission", "not_found", "token")):
            return "calculation_configuration"
        return "calculation_unavailable"
    if normalized in {"network_error", "network_timeout"}:
        return "calculation_unavailable"
    if normalized in _TECHNICAL_CODES:
        return "calculation_failed"
    if isinstance(message, str) and _PLATFORM_TEXT.search(message):
        return "calculation_unavailable"
    return str(code) if code is not None else "calculation_failed"


def public_calc_error_message(message: Any, code: Any = None) -> str:
    """Return a user-safe calculation error message.

    Business validation messages are retained. Technical and platform-originated
    failures are reduced to a stable message without vendor details or raw codes.
    """
    text = str(message or "").strip()
    if text.startswith("测算失败："):
        text = text[len("测算失败："):].strip()
    if not text:
        return _GENERIC_FAILED

    normalized = str(code or "").strip().lower()
    if normalized.startswith("feishu_") or normalized in {"network_error", "network_timeout"}:
        if any(part in normalized for part in ("auth", "permission", "not_found", "token")):
            return _GENERIC_CONFIG
        return _GENERIC_UNAVAILABLE
    if normalized in _TECHNICAL_CODES or _PLATFORM_TEXT.search(text):
        return _GENERIC_UNAVAILABLE if _PLATFORM_TEXT.search(text) else _GENERIC_FAILED
    return text[:500]
