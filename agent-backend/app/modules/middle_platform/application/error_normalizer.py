"""Normalize middle-platform error frames without exposing exception details."""
from __future__ import annotations

import ast
import json
from typing import Any

_MAX_MESSAGE_LENGTH = 500


def _clean_message(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    message = value.strip()
    if not message:
        return None
    return message[:_MAX_MESSAGE_LENGTH]


def _response_message(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    return _clean_message(value.get("msg")) or _clean_message(value.get("message"))


def _balanced_object(text: str, start: int) -> str | None:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def exception_response(exception: object) -> dict[str, Any] | None:
    """Extract the structured ``body=...`` response from a wrapped exception."""
    if not isinstance(exception, str):
        return None
    marker = exception.find("body=")
    if marker < 0:
        return None
    start = exception.find("{", marker + len("body="))
    if start < 0:
        return None
    raw_body = _balanced_object(exception, start)
    if raw_body is None:
        return None
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(raw_body)
        except (ValueError, SyntaxError):
            return None
    return parsed if isinstance(parsed, dict) else None


def error_message(payload: object) -> str | None:
    """Return a user-safe message from a middle-platform error payload."""
    if not isinstance(payload, dict):
        return None
    inner = payload.get("data")
    inner = inner if isinstance(inner, dict) else {}
    return (
        _response_message(inner.get("response"))
        or _clean_message(payload.get("msg"))
        or _clean_message(inner.get("message"))
        or _response_message(exception_response(inner.get("exception")))
    )


def normalize_error_record(record: bytes) -> bytes:
    """Rewrite wrapped HTTP failures as structured SSE errors for the browser."""
    try:
        lines = record.decode("utf-8").split("\n")
        event = next((line[7:].strip() for line in lines if line.startswith("event:")), None)
        if event != "error":
            return record
        raw_data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
        payload = json.loads(raw_data)
        if not isinstance(payload, dict):
            return record
        inner = payload.get("data")
        if not isinstance(inner, dict) or not isinstance(inner.get("exception"), str):
            return record
        response = inner.get("response") if isinstance(inner.get("response"), dict) else None
        wrapped_response = exception_response(inner.get("exception"))
        message = (
            _response_message(response)
            or _clean_message(payload.get("msg"))
            or _clean_message(inner.get("message"))
            or _response_message(wrapped_response)
            or "对话出错"
        )
        response_payload = response or wrapped_response or {}

        normalized_inner = dict(inner)
        normalized_inner.pop("exception", None)
        normalized_inner["response"] = {
            "code": response_payload.get("code"),
            "msg": message,
            "data": response_payload.get("data"),
        }
        normalized_payload = dict(payload)
        normalized_payload["msg"] = message
        normalized_payload["data"] = normalized_inner
        data_line = json.dumps(normalized_payload, ensure_ascii=False, separators=(",", ":"))
        metadata = [line for line in lines if not line.startswith("data:")]
        return "\n".join([*metadata, f"data: {data_line}"]).encode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
        return record
