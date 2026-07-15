"""Batch 4.6 conversation history and resource ownership acceptance tests."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    MessageSnapshotORM,
    ReportSnapshotORM,
)

_USER_1 = {"X-User-Id": "history-user-1", "X-User-Name": "User One"}
_USER_2 = {"X-User-Id": "history-user-2", "X-User-Name": "User Two"}


def test_conversation_deleted_at_is_nullable():
    column = ConversationORM.__table__.c.deleted_at
    assert column.nullable is True


@pytest.fixture
async def history_context():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    now = datetime(2026, 7, 15, 9, 0, 0)
    async with maker() as session:
        older = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Older active",
            created_at=now,
        )
        newer = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Newer active",
            created_at=now + timedelta(minutes=1),
        )
        deleted = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Deleted",
            created_at=now + timedelta(minutes=20),
        )
        foreign = ConversationORM(
            user_id="history-user-2",
            username="User Two",
            title="Foreign",
            created_at=now + timedelta(minutes=30),
        )
        empty_failed = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Failed only",
            created_at=now + timedelta(minutes=40),
        )
        session.add_all([older, newer, deleted, foreign, empty_failed])
        await session.flush()

        deleted.deleted_at = now + timedelta(minutes=21)
        session.add_all([
            MessageSnapshotORM(
                conversation_id=newer.id,
                role="assistant",
                content="second",
                created_at=now + timedelta(minutes=5),
            ),
            MessageSnapshotORM(
                conversation_id=newer.id,
                role="user",
                content="first",
                created_at=now + timedelta(minutes=4),
            ),
            MessageSnapshotORM(
                conversation_id=older.id,
                role="user",
                content="latest activity",
                created_at=now + timedelta(minutes=8),
            ),
        ])
        old_task = CalculationTaskORM(
            conversation_id=older.id,
            version="V1",
            status="completed",
            request_id="req-old",
            created_at=now + timedelta(minutes=2),
        )
        v2 = CalculationTaskORM(
            conversation_id=newer.id,
            version="V2",
            status="completed",
            request_id="req-v2",
            created_at=now + timedelta(minutes=7),
        )
        v1 = CalculationTaskORM(
            conversation_id=newer.id,
            version="V1",
            status="failed",
            request_id="req-v1",
            error_code="failed-v1",
            error_message="failed first",
            created_at=now + timedelta(minutes=6),
        )
        foreign_task = CalculationTaskORM(
            conversation_id=foreign.id,
            version="V1",
            status="completed",
            request_id="req-foreign",
            created_at=now + timedelta(minutes=31),
        )
        deleted_task = CalculationTaskORM(
            conversation_id=deleted.id,
            version="V1",
            status="completed",
            request_id="req-deleted",
            created_at=now + timedelta(minutes=22),
        )
        empty_failed_task = CalculationTaskORM(
            conversation_id=empty_failed.id,
            version="V1",
            status="failed",
            request_id="req-empty-failed",
            error_code="template_broken",
            error_message="接口区损坏",
            created_at=now + timedelta(minutes=41),
        )
        session.add_all([old_task, v2, v1, foreign_task, deleted_task, empty_failed_task])
        await session.flush()
        session.add_all([
            ReportSnapshotORM(task_id=v2.id, payload={"marker": "v2"}),
            ReportSnapshotORM(task_id=foreign_task.id, payload={"marker": "foreign"}),
            ReportSnapshotORM(task_id=deleted_task.id, payload={"marker": "deleted"}),
        ])
        await session.commit()

        ids = {
            "older": older.id,
            "newer": newer.id,
            "deleted": deleted.id,
            "foreign": foreign.id,
            "v2": v2.id,
            "foreign_task": foreign_task.id,
            "deleted_task": deleted_task.id,
        }

    async def override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=_USER_1,
        ) as client:
            yield client, maker, ids
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_returns_current_users_active_conversations_by_latest_activity(history_context):
    client, _, ids = history_context

    response = await client.get("/ir/conversations")

    assert response.status_code == 200
    # deleted（软删）、foreign（他人）、empty_failed（仅失败无消息）均不出现
    assert response.json()["data"]["items"] == [
        {
            "conversationId": ids["older"],
            "title": "Older active",
            "createdAt": "2026-07-15T09:00:00",
            "latestVersion": "V1",
            "latestStatus": "completed",
        },
        {
            "conversationId": ids["newer"],
            "title": "Newer active",
            "createdAt": "2026-07-15T09:01:00",
            "latestVersion": "V2",
            "latestStatus": "completed",
        },
    ]


@pytest.mark.asyncio
async def test_detail_replays_messages_and_versions_in_fixed_order(history_context):
    client, _, ids = history_context

    response = await client.get(f"/ir/conversations/{ids['newer']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["conversationId"] == ids["newer"]
    assert data["title"] == "Newer active"
    assert [(message["role"], message["content"]) for message in data["messages"]] == [
        ("user", "first"),
        ("assistant", "second"),
    ]
    assert [version["version"] for version in data["versions"]] == ["V1", "V2"]
    assert data["versions"][0]["result"] is None
    assert data["versions"][1] == {
        "taskId": ids["v2"],
        "version": "V2",
        "status": "completed",
        "result": {"marker": "v2"},
    }
    assert "reports" not in data


@pytest.mark.asyncio
async def test_delete_soft_deletes_conversation_and_preserves_children(history_context):
    client, maker, ids = history_context
    async with maker() as session:
        before = {
            "messages": await session.scalar(select(func.count()).select_from(MessageSnapshotORM)),
            "tasks": await session.scalar(select(func.count()).select_from(CalculationTaskORM)),
            "reports": await session.scalar(select(func.count()).select_from(ReportSnapshotORM)),
        }

    response = await client.delete(f"/ir/conversations/{ids['newer']}")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "conversationId": ids["newer"],
        "deleted": True,
    }
    async with maker() as session:
        conversation = await session.get(ConversationORM, ids["newer"])
        assert conversation.deleted_at is not None
        after = {
            "messages": await session.scalar(select(func.count()).select_from(MessageSnapshotORM)),
            "tasks": await session.scalar(select(func.count()).select_from(CalculationTaskORM)),
            "reports": await session.scalar(select(func.count()).select_from(ReportSnapshotORM)),
        }
    assert after == before
    assert (await client.get("/ir/conversations")).json()["data"]["items"] == [
        {
            "conversationId": ids["older"],
            "title": "Older active",
            "createdAt": "2026-07-15T09:00:00",
            "latestVersion": "V1",
            "latestStatus": "completed",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path_key", [
    ("get", "conversation"),
    ("delete", "conversation"),
    ("get", "status"),
    ("get", "result"),
    ("post", "append"),
])
async def test_cross_user_resources_return_404(history_context, method, path_key):
    client, _, ids = history_context
    paths = {
        "conversation": f"/ir/conversations/{ids['foreign']}",
        "status": f"/ir/calc/tasks/{ids['foreign_task']}",
        "result": f"/ir/calc/tasks/{ids['foreign_task']}/result",
        "append": "/ir/calc/tasks",
    }
    kwargs = {}
    if path_key == "append":
        kwargs["json"] = {
            "province": "甘肃",
            "capacity_mwh": 800,
            "power_mw": 200,
            "conversation_id": ids["foreign"],
        }

    response = await getattr(client, method)(paths[path_key], **kwargs)

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["status", "result"])
async def test_tasks_in_soft_deleted_conversation_return_404(history_context, path):
    client, _, ids = history_context
    suffix = "/result" if path == "result" else ""

    response = await client.get(f"/ir/calc/tasks/{ids['deleted_task']}{suffix}")

    assert response.status_code == 404
