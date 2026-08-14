"""中台对话代理服务测试。"""

import json
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config.settings import MiddlePlatformConfig
from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    MessageSnapshotORM,
)
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


def _service(client, maker=None):
    return ChatProxyService(
        MiddlePlatformConfig(
            chat_url="http://middle-platform/api/v1/chat/diag",
            app_id="ir_agent",
            app_secret="secret",
        ),
        client=client,
        token_cache=MiddlePlatformTokenCache(refresh_skew_seconds=0),
        sessionmaker=maker,
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
    # header 含网关安全的会话标识与身份字段
    assert payload["header"]["X-IR-Conversation-Id"] == stream.conversation_id
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
    assert client.payloads[0][1]["header"]["X-IR-Conversation-Id"] == conversation.id


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


async def _conversation_messages(db_session, conversation_id):
    from sqlalchemy import select as sa_select
    return (await db_session.execute(
        sa_select(MessageSnapshotORM)
        .where(MessageSnapshotORM.conversation_id == conversation_id)
        .order_by(MessageSnapshotORM.id.asc())
    )).scalars().all()


@pytest.mark.asyncio
async def test_start_chat_persists_real_user_input_verbatim(session):
    """首轮对话：输入框原文（含首尾空白清理后）精确落为用户消息。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    client = FakeMiddlePlatformClient([_question("mp-session-1")])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="  测算甘肃 200MW/800MWh 储能项目收益率  ",
        conversation_id=None,
    )

    await _collect(stream.chunks)

    await session.commit()
    messages = await _conversation_messages(session, stream.conversation_id)
    # 真实用户原文精确落库；question 事件是用户当时可见的 assistant 追问，也应保留
    user_messages = [m for m in messages if m.role == "user"]
    assert len(user_messages) == 1
    assert user_messages[0].message_type == "text"
    assert user_messages[0].content == "测算甘肃 200MW/800MWh 储能项目收益率"
    assert user_messages[0].payload is None
    assert any(m.role == "assistant" and m.content == "请补充项目功率" for m in messages)


@pytest.mark.asyncio
async def test_multi_turn_persists_each_real_user_input(session):
    """多轮对话：每轮真实输入都落库（而非结构化的测算摘要）。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
    )
    session.add(conversation)
    await session.commit()

    client = FakeMiddlePlatformClient([_question("mp-session-1")])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="功率调整到 400MW",
        conversation_id=conversation.id,
    )
    await _collect(stream.chunks)

    await session.commit()
    messages = await _conversation_messages(session, conversation.id)
    # 每轮真实输入原样保留（而非结构化测算摘要），同时保留 assistant 追问
    assert [m.content for m in messages if m.role == "user"] == ["功率调整到 400MW"]
    assert any(m.role == "assistant" and m.content == "请补充项目功率" for m in messages)


def _completion_frame(session_id: str, task_id: int, version: str) -> bytes:
    return (
        "event: answer\n"
        "id: frame-3\n"
        f'data: {{"event":"answer","session":{{"session_id":"{session_id}"}},"data":{{'
        f'"answer":"已按 {version} 完成测算，详见下方结果",'
        f'"biz":[{{"tool":"create_calculation_task","payload":{{"data":{{"taskId":{task_id}}}}}}}]'
        f'}}}}\n\n'
    ).encode()


@pytest.mark.asyncio
async def test_answer_with_calc_task_attaches_text_to_completion_payload(session):
    """匹配计算任务的 answer：回答文本写入对应 completion 的 payload.answer_text。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
        middle_platform_session_id="mp-session-1",
    )
    session.add(conversation)
    task = CalculationTaskORM(
        conversation_id=conversation.id,
        version="V1",
        status="completed",
        request_id="req-1",
        param_hash="hash",
        feishu_copy_url="doc",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    session.add(MessageSnapshotORM(
        conversation_id=conversation.id,
        role="assistant",
        content="V1 测算完成",
        message_type="calculation_completed",
        payload={"event_type": "calculation_completed", "task_id": task.id, "version": "V1"},
    ))
    await session.commit()

    client = FakeMiddlePlatformClient([_completion_frame("mp-session-1", task.id, "V1")])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="重新测算",
        conversation_id=conversation.id,
    )
    await _collect(stream.chunks)

    await session.commit()
    messages = await _conversation_messages(session, conversation.id)
    # 用户真实输入 + completion（已被附加 answer_text，无新增普通 assistant 消息）
    completion = [m for m in messages if m.message_type == "calculation_completed"][0]
    assert completion.payload["answer_text"] == "已按 V1 完成测算，详见下方结果"
    assert completion.content == "V1 测算完成"
    assert len([m for m in messages if m.role == "assistant"]) == 1


@pytest.mark.asyncio
async def test_plain_answer_writes_assistant_text_message(session):
    """普通问答（无计算任务）：answer 文本落为独立 assistant 消息。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
    )
    session.add(conversation)
    await session.commit()

    answer_frame = (
        "event: answer\n"
        "id: frame-3\n"
        'data: {"event":"answer","session":{"session_id":"mp-session-1"},"data":{"answer":"普通问答的回答内容"}}\n\n'
    ).encode()
    client = FakeMiddlePlatformClient([answer_frame])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="介绍一下储能市场",
        conversation_id=conversation.id,
    )
    await _collect(stream.chunks)

    await session.commit()
    messages = await _conversation_messages(session, conversation.id)
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].message_type == "text"
    assert messages[1].content == "普通问答的回答内容"


@pytest.mark.asyncio
async def test_empty_answer_writes_no_extra_message(session):
    """answer 为空/缺失：不产生多余历史消息。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    conversation = ConversationORM(
        id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
        user_id="u-1",
        username="张三",
    )
    session.add(conversation)
    await session.commit()

    empty_frame = (
        "event: answer\n"
        "id: frame-3\n"
        'data: {"event":"answer","session":{"session_id":"mp-session-1"},"data":{"answer":"   "}}\n\n'
    ).encode()
    client = FakeMiddlePlatformClient([empty_frame])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="空回答测试",
        conversation_id=conversation.id,
    )
    await _collect(stream.chunks)

    await session.commit()
    messages = await _conversation_messages(session, conversation.id)
    assert [m.role for m in messages] == ["user"]


@pytest.mark.asyncio
async def test_error_event_persists_assistant_error_message(session):
    """中台显式错误既透传给前端，也作为 AI 消息进入历史回放。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(session.bind, expire_on_commit=False)
    error_frame = (
        "event: error\n"
        'data: {"code":500,"msg":"测算服务暂时不可用","data":null}\n\n'
    ).encode()
    client = FakeMiddlePlatformClient([error_frame])
    stream = await _service(client, maker=maker).start_chat(
        session=session,
        user=CurrentUser(user_id="u-1", username="张三"),
        message="测算甘肃项目",
        conversation_id=None,
    )

    body = await _collect(stream.chunks)

    assert body == error_frame
    messages = await _conversation_messages(session, stream.conversation_id)
    assert [(message.role, message.message_type) for message in messages] == [
        ("user", "text"),
        ("assistant", "calculation_error"),
    ]
    assert messages[1].content == "测算失败：测算服务暂时不可用"
    assert messages[1].payload == {
        "event_type": "calculation_error",
        "error_code": "middle_platform_error",
    }
