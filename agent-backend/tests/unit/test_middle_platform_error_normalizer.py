"""Middle-platform error payload normalization tests."""
import json

from app.modules.middle_platform.application.error_normalizer import (
    error_message,
    exception_response,
    normalize_error_record,
)


BUSINESS_MESSAGE = "EPC单价超出允许范围，正确范围为[0.7, 1.1]"


def _wrapped_exception(body: str) -> str:
    return (
        "RuntimeError('HTTP 调用失败: POST /ir/calc/tasks | "
        "HTTPStatusError(\"400 Bad Request for http://internal-6-76.example.invalid:9089/ir/calc/tasks\") "
        f"| body={body}')"
    )


def test_extracts_json_response_body_from_wrapped_exception():
    exception = _wrapped_exception(json.dumps(
        {"code": 400, "msg": BUSINESS_MESSAGE, "data": None},
        ensure_ascii=False,
    ))

    assert exception_response(exception) == {
        "code": 400,
        "msg": BUSINESS_MESSAGE,
        "data": None,
    }


def test_extracts_python_repr_and_handles_brace_inside_message():
    exception = _wrapped_exception(
        "{'code': 400, 'msg': '参数 {epc} 不合法', 'data': None}"
    )

    assert exception_response(exception)["msg"] == "参数 {epc} 不合法"


def test_prefers_structured_response_and_limits_message_length():
    payload = {
        "msg": "外层错误",
        "data": {
            "response": {"code": 400, "msg": "结构化业务错误"},
            "exception": _wrapped_exception('{"code":400,"msg":"异常体错误"}'),
        },
    }
    assert error_message(payload) == "结构化业务错误"
    assert len(error_message({"msg": "错" * 600, "data": {}})) == 500


def test_invalid_exception_does_not_expose_internal_details():
    payload = {
        "data": {
            "response": None,
            "exception": "RuntimeError('POST http://internal-6-76.example.invalid failed without body')",
        },
    }

    assert exception_response(payload["data"]["exception"]) is None
    assert error_message(payload) is None


def test_normalizes_wrapped_error_and_removes_exception():
    payload = {
        "event": "error",
        "data": {
            "tool_name": "create_calculation_task",
            "exception": _wrapped_exception(json.dumps(
                {"code": 400, "msg": BUSINESS_MESSAGE, "data": None},
                ensure_ascii=False,
            )),
            "response": None,
        },
    }
    record = (
        "event: error\n"
        "id: 248\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}"
    ).encode()

    normalized = normalize_error_record(record)
    parsed = json.loads(next(
        line[6:] for line in normalized.decode().splitlines() if line.startswith("data: ")
    ))

    assert parsed["msg"] == BUSINESS_MESSAGE
    assert parsed["data"]["response"] == {
        "code": 400,
        "msg": BUSINESS_MESSAGE,
        "data": None,
    }
    assert "exception" not in parsed["data"]
    assert b"internal-6-76.example.invalid" not in normalized
    assert normalized.startswith(b"event: error\nid: 248\n")


def test_removes_exception_when_structured_response_is_available():
    payload = {
        "event": "error",
        "data": {
            "response": {"code": 400, "msg": "结构化业务错误", "data": None},
            "exception": "RuntimeError('internal http://internal-6-76.example.invalid failure')",
        },
    }
    record = f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}".encode()

    normalized = normalize_error_record(record)
    parsed = json.loads(normalized.decode().split("data: ", 1)[1])

    assert parsed["msg"] == "结构化业务错误"
    assert "exception" not in parsed["data"]
    assert b"internal-6-76.example.invalid" not in normalized


def test_unparseable_exception_uses_safe_fallback_and_plain_errors_are_unchanged():
    plain = b'event: error\ndata: {"msg":"business error","data":null}'
    invalid = b'event: error\ndata: {"data":{"exception":"RuntimeError(no body)","response":null}}'

    assert normalize_error_record(plain) == plain
    parsed = json.loads(normalize_error_record(invalid).decode().split("data: ", 1)[1])
    assert parsed["msg"] == "对话出错"
    assert parsed["data"]["response"]["msg"] == "对话出错"
    assert "exception" not in parsed["data"]
