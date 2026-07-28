"""中台对话代理服务测试。"""

import json
from uuid import UUID

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


def _session_start(session_id: str) -> bytes:
    return (
        "event: session_start\n"
        "id: frame-1\n"
        f'data: {{"event":"session_start","session":{{"session_id":"{session_id}"}},"data":{{}}}}\n\n'
    ).encode()


def _question(session_id: str) -> bytes:
    return (
        "event: question\n"
        "id: frame-2\n"
        f'data: {{"event":"question","session":{{"session_id":"{session_id}"}},"data":{{"text":"请补充项目功率"}}}}\n\n'
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
            chat_url="http://middle-platform/api/v1/chat/diag",
            app_id="ir_agent",
            app_secret="secret",
        ),
        client=client,
        token_cache=MiddlePlatformTokenCache(refresh_skew_seconds=0),
    )


async def _collect(chunks):
    return b"".join([chunk async for chunk in chunks])


@pytest.mark.asyncio
async def test_first_chat_creates_conversation_and_relays_sse(session):
    """首轮对话：新建会话，session_id 为空，透传 SSE，不注入 ir_system_context。"""
    client = FakeMiddlePlatformClient([_question("mp-session-1")])
    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="测算甘肃 2H 储能项目",
        conversation_id=None,
    )

    body = await _collect(stream.chunks)
    UUID(stream.conversation_id)  # 合法 UUID
    assert body == _question("mp-session-1")

    conversation = await session.get(ConversationORM, stream.conversation_id)
    assert conversation.title == "测算甘肃 2H 储能项目"
    assert client.issued_for == [("u-1", "张三")]

    payload = client.payloads[0][1]
    # 首轮中台 session_id 为空
    assert payload["session_id"] is None
    assert payload["app_id"] == "ir_agent"
    assert payload["source_system"] == "ir_agent"
    assert payload["end_user_id"] == "u-1"
    assert payload["end_user_name"] == "张三"
    # message 不含 ir_system_context
    assert "<ir_system_context>" not in payload["message"]
    # header 含 conversation_id 与身份字段
    assert payload["header"]["conversation_id"] == stream.conversation_id
    assert payload["header"]["userid"] == "u-1"
    assert payload["header"]["username"] == "%E5%BC%A0%E4%B8%89"


@pytest.mark.asyncio
async def test_session_start_persists_middle_platform_session_id(session):
    """session_start 事件回写中台 session_id 到映射列。"""
    mp_session_id = "mp-abc-123"
    client = FakeMiddlePlatformClient([_session_start(mp_session_id)])
    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="admin"),
        message="测算宁夏项目",
        conversation_id=None,
    )

    await _collect(stream.chunks)

    await session.refresh(await session.get(ConversationORM, stream.conversation_id))
    conversation = await session.get(ConversationORM, stream.conversation_id)
    assert conversation.middle_platform_session_id == mp_session_id


@pytest.mark.asyncio
async def test_multi_turn_sends_stored_middle_platform_session_id(session):
    """多轮对话：从映射列取中台 session_id 回填到请求 body。"""
    mp_session_id = "mp-stored-session"
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
        middle_platform_session_id=mp_session_id,
    )
    session.add(conversation)
    await session.commit()

    client = FakeMiddlePlatformClient([_question(mp_session_id)])
    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="补充 100MW",
        conversation_id=conversation.id,
    )

    await _collect(stream.chunks)
    assert client.payloads[0][1]["session_id"] == mp_session_id
    assert client.payloads[0][1]["header"]["conversation_id"] == conversation.id


@pytest.mark.asyncio
async def test_malformed_session_start_emits_error(session):
    """session_start 数据格式异常时输出 error 帧。"""
    bad_frame = b"event: session_start\ndata: {not-json}\n\n"
    client = FakeMiddlePlatformClient([bad_frame])
    stream = await _service(client).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="admin"),
        message="测算项目",
        conversation_id=None,
    )

    body = await _collect(stream.chunks)
    assert body.startswith(b"event: error\n")
    assert json.loads(body.split(b"data: ", 1)[1])["msg"] == "中台会话协议异常"
