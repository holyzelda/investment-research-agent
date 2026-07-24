"""中台对话代理服务测试。"""

import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config.settings import MiddlePlatformConfig
from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import ConversationORM
from app.modules.middle_platform.application.chat_proxy_service import ChatProxyService
from app.modules.middle_platform.application.token_cache import MiddlePlatformTokenCache
from app.modules.middle_platform.infrastructure.http_client import PlatformAccessToken
from app.modules.platform_access.domain.models import CurrentUser


_SESSION_START = (
    'event: session_start\n'
    'id: frame-1\n'
    'data: {"event":"session_start","session":{"session_id":"mp-42"},"data":{}}\n\n'
).encode()
_QUESTION = (
    'event: question\n'
    'id: frame-2\n'
    'data: {"event":"question","session":{"session_id":"mp-42"},"data":{"text":"请补充项目功率"}}\n\n'
).encode()


class FakeMiddlePlatformClient:
    def __init__(self, chunks):
        self.chunks = chunks
        self.issued_for = []
        self.payloads = []

    async def issue_token(self, *, user_id, user_name):
        self.issued_for.append((user_id, user_name))
        return PlatformAccessToken(value="platform-token", expires_in=3600)

    async def stream_chat(self, *, access_token, payload):
        self.payloads.append((access_token, payload))
        for chunk in self.chunks:
            yield chunk


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


def _service(client):
    return ChatProxyService(
        MiddlePlatformConfig(
            base_url="http://middle-platform",
            app_id="ir-agent",
            app_secret="secret",
        ),
        client=client,
        token_cache=MiddlePlatformTokenCache(refresh_skew_seconds=0),
    )


async def _collect(chunks):
    return b"".join([chunk async for chunk in chunks])


@pytest.mark.asyncio
async def test_first_chat_creates_conversation_relays_sse_and_persists_session(session):
    client = FakeMiddlePlatformClient([_SESSION_START[:28], _SESSION_START[28:] + _QUESTION])
    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="测算甘肃 2H 储能项目",
        conversation_id=None,
    )

    assert await _collect(stream.chunks) == _SESSION_START + _QUESTION
    conversation = await session.get(ConversationORM, stream.conversation_id)
    assert conversation.title == "测算甘肃 2H 储能项目"
    assert conversation.middle_platform_session_id == "mp-42"
    assert client.issued_for == [("u-1", "张三")]
    payload = client.payloads[0][1]
    assert payload["session_id"] is None
    assert payload["header"] == {"userId": "u-1", "username": "%E5%BC%A0%E4%B8%89"}
    assert payload["message"].endswith(
        f'<ir_system_context>{{"conversation_id":{stream.conversation_id}}}</ir_system_context>'
    )


@pytest.mark.asyncio
async def test_existing_conversation_reuses_platform_session(session):
    conversation = ConversationORM(
        user_id="u-1",
        username="张三",
        middle_platform_session_id="mp-old",
    )
    session.add(conversation)
    await session.commit()
    client = FakeMiddlePlatformClient([_QUESTION])

    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="补充 100MW",
        conversation_id=conversation.id,
    )

    await _collect(stream.chunks)
    assert client.payloads[0][1]["session_id"] == "mp-old"


@pytest.mark.asyncio
async def test_different_session_id_does_not_overwrite_existing_mapping(session):
    conversation = ConversationORM(
        user_id="u-1",
        username="张三",
        middle_platform_session_id="mp-old",
    )
    session.add(conversation)
    await session.commit()
    incoming = _SESSION_START.replace(b'"mp-42"', b'"mp-new"')
    client = FakeMiddlePlatformClient([incoming])

    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="继续测算",
        conversation_id=conversation.id,
    )

    body = await _collect(stream.chunks)
    assert body.startswith(b"event: error\n")
    assert json.loads(body.split(b"data: ", 1)[1]) ["msg"] == "中台会话映射冲突"
    assert (await session.get(ConversationORM, conversation.id)).middle_platform_session_id == "mp-old"
