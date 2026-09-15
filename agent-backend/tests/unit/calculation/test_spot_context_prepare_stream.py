import importlib
import json
from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from app.core.exceptions import ValidationException
from app.modules.platform_access.domain.models import CurrentUser


router_module = importlib.import_module("app.modules.calculation.interface.router")


def _upload():
    return UploadFile(file=BytesIO(b"xlsx"), filename="2025.xlsx")


async def _events(response):
    return [json.loads(frame) async for frame in response.body_iterator]


@pytest.mark.asyncio
async def test_prepare_stream_preserves_progress_order(monkeypatch):
    parsed = object()

    def fake_parse(*args, progress_callback=None, **kwargs):
        progress_callback({"phase": "validating", "message": "校验中"})
        return parsed

    async def fake_save(self, session, **kwargs):
        assert kwargs["parsed"] is parsed
        return "context-token", object()

    monkeypatch.setattr(router_module, "parse_uploaded_spot_file", fake_parse)
    monkeypatch.setattr(router_module.SpotContextService, "save_prepared", fake_save)
    monkeypatch.setattr(
        router_module.SpotContextService,
        "summary",
        staticmethod(lambda context: {"status": "ready", "validDays": 2}),
    )

    response = await router_module.prepare_spot_context(
        file=_upload(),
        conversation_id=None,
        user=CurrentUser(user_id="user-1", username="tester"),
        session=object(),
    )

    events = await _events(response)

    assert [event["phase"] for event in events] == [
        "uploading", "validating", "saving", "ready",
    ]
    assert events[-1]["data"] == {
        "status": "ready", "validDays": 2, "contextToken": "context-token",
    }


@pytest.mark.asyncio
async def test_prepare_stream_reads_upload_before_request_cleanup(monkeypatch):
    parsed = object()

    def fake_parse(content, filename, **kwargs):
        assert content == b"xlsx"
        assert filename == "2025.xlsx"
        return parsed

    async def fake_save(self, session, **kwargs):
        assert kwargs["parsed"] is parsed
        return "context-token", object()

    monkeypatch.setattr(router_module, "parse_uploaded_spot_file", fake_parse)
    monkeypatch.setattr(router_module.SpotContextService, "save_prepared", fake_save)
    monkeypatch.setattr(
        router_module.SpotContextService,
        "summary",
        staticmethod(lambda context: {"status": "ready"}),
    )

    upload = _upload()
    response = await router_module.prepare_spot_context(
        file=upload,
        conversation_id=None,
        user=CurrentUser(user_id="user-1", username="tester"),
        session=object(),
    )
    upload.file.close()

    events = await _events(response)

    assert events[-1]["phase"] == "ready"


@pytest.mark.asyncio
async def test_prepare_stream_returns_validation_error_frame(monkeypatch):
    def fake_parse(*args, **kwargs):
        raise ValidationException("电价文件校验失败：表头不匹配")

    monkeypatch.setattr(router_module, "parse_uploaded_spot_file", fake_parse)

    response = await router_module.prepare_spot_context(
        file=_upload(),
        conversation_id=None,
        user=CurrentUser(user_id="user-1", username="tester"),
        session=object(),
    )

    events = await _events(response)

    assert events[-1] == {
        "phase": "error",
        "message": "电价文件校验失败：表头不匹配",
    }
    assert all(event["phase"] != "saving" for event in events)


@pytest.mark.asyncio
async def test_prepare_stream_returns_save_error_frame(monkeypatch):
    monkeypatch.setattr(router_module, "parse_uploaded_spot_file", lambda *args, **kwargs: object())

    async def fake_save(self, session, **kwargs):
        raise ValidationException("会话不存在")

    monkeypatch.setattr(router_module.SpotContextService, "save_prepared", fake_save)

    response = await router_module.prepare_spot_context(
        file=_upload(),
        conversation_id=None,
        user=CurrentUser(user_id="user-1", username="tester"),
        session=object(),
    )

    events = await _events(response)

    assert [event["phase"] for event in events] == ["uploading", "saving", "error"]
    assert events[-1]["message"] == "会话不存在"
