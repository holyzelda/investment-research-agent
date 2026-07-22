import json
from types import SimpleNamespace

import pytest
from starlette.requests import Request

import app.core.exceptions as exceptions


def _request(path="/ir/calc/stations"):
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"province=%E5%AE%81%E5%A4%8F",
        "server": ("test", 80),
        "scheme": "http",
        "client": ("test", 1),
    })


@pytest.mark.asyncio
async def test_global_handler_returns_actual_error_in_debug(monkeypatch):
    monkeypatch.setattr(
        exceptions,
        "get_settings",
        lambda: SimpleNamespace(app=SimpleNamespace(debug=True)),
        raising=False,
    )

    response = await exceptions._global_handler(_request(), RuntimeError("table missing"))

    assert response.status_code == 500
    assert json.loads(response.body)["msg"] == "table missing"


@pytest.mark.asyncio
async def test_global_handler_logs_exception_type_and_request_context(monkeypatch):
    messages = []
    monkeypatch.setattr(exceptions.logger, "exception", messages.append)

    await exceptions._global_handler(_request(), RuntimeError("table missing"))

    assert messages
    assert "RuntimeError" in messages[0]
    assert "GET /ir/calc/stations" in messages[0]
    assert "table missing" in messages[0]


@pytest.mark.asyncio
async def test_global_handler_hides_actual_error_outside_debug(monkeypatch):
    monkeypatch.setattr(
        exceptions,
        "get_settings",
        lambda: SimpleNamespace(app=SimpleNamespace(debug=False)),
        raising=False,
    )

    response = await exceptions._global_handler(_request(), RuntimeError("password leaked"))

    assert response.status_code == 500
    assert json.loads(response.body)["msg"] == "服务器内部错误"
