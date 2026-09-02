"""Batch 4.6 conversation history and resource ownership acceptance tests."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import BackgroundTasks
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.main import app
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
    MessageSnapshotORM,
)
from app.modules.calculation.interface import conversation_router
from app.modules.platform_access.domain.models import CurrentUser, OrganizationUser, UserScope
from app.modules.platform_access.interface.deps import get_user_scope

_USER_1 = {"userId": "history-user-1", "username": "User One"}
_USER_2 = {"userId": "history-user-2", "username": "User Two"}


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
            last_activity_at=now + timedelta(minutes=8),
        )
        newer = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Newer active",
            created_at=now + timedelta(minutes=1),
            last_activity_at=now + timedelta(minutes=7),
        )
        deleted = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Deleted",
            created_at=now + timedelta(minutes=20),
            last_activity_at=now + timedelta(minutes=22),
        )
        foreign = ConversationORM(
            user_id="history-user-2",
            username="User Two",
            title="Foreign",
            created_at=now + timedelta(minutes=30),
            last_activity_at=now + timedelta(minutes=31),
        )
        empty_failed = ConversationORM(
            user_id="history-user-1",
            username="User One",
            title="Failed only",
            created_at=now + timedelta(minutes=40),
            last_activity_at=now + timedelta(minutes=41),
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
            CalculationResultSnapshotORM(task_id=v2.id, payload={"marker": "v2"}),
            CalculationResultSnapshotORM(task_id=foreign_task.id, payload={"marker": "foreign"}),
            CalculationResultSnapshotORM(task_id=deleted_task.id, payload={"marker": "deleted"}),
            InputSnapshotORM(task_id=v2.id, payload={
                "apiInput": {"spot_charge_avg": 0.22},
                "changeMeta": {
                    "previousTaskId": None,
                    "explicitOverrideKeys": [],
                    "derivedChangedKeys": [],
                },
            }),
            InputSnapshotORM(task_id=foreign_task.id, payload={
                "apiInput": {"spot_charge_avg": 0.31},
                "changeMeta": {},
            }),
        ])
        await session.commit()

        ids = {
            "older": older.id,
            "newer": newer.id,
            "deleted": deleted.id,
            "foreign": foreign.id,
            "empty_failed": empty_failed.id,
            "v2": v2.id,
            "v1": v1.id,
            "old_task": old_task.id,
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
    data = response.json()["data"]
    # deleted（软删）、foreign（他人）不出现；仅失败会话仍属于当前用户活跃会话
    assert data["items"] == [
        {
            "conversationId": ids["empty_failed"],
            "title": "Failed only",
            "createdAt": "2026-07-15T09:40:00",
            "lastActivityAt": "2026-07-15T09:41:00",
        },
        {
            "conversationId": ids["older"],
            "title": "Older active",
            "createdAt": "2026-07-15T09:00:00",
            "lastActivityAt": "2026-07-15T09:08:00",
        },
        {
            "conversationId": ids["newer"],
            "title": "Newer active",
            "createdAt": "2026-07-15T09:01:00",
            "lastActivityAt": "2026-07-15T09:07:00",
        },
    ]
    # 由于只有2条且limit=15，没有更多数据
    assert data["nextCursor"] is None


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
    assert [version["version"] for version in data["versions"]] == ["V2"]
    assert data["versions"][0] == {
        "taskId": ids["v2"],
        "version": "V2",
        "status": "completed",
        "card": {
            "version": "V2",
            "warnings": [],
            "basicInfo": {
                "province": None,
                "city": None,
                "nodeName": None,
                "capacityMwh": None,
                "powerMw": None,
                "chargeCost": None,
                "dischargeReturn": None,
                "lossCost": None,
                "actualSpread": None,
            },
            "financial": {
                "projectIrr": None,
                "projectStaticPayback": None,
                "capitalIrr": None,
                "capitalStaticPayback": None,
                "averageProfit": None,
            },
            "advanced": {
                "donut": {
                    "totalRevenue": None,
                    "energyRevenue": None,
                    "capacityRevenue": None,
                    "frequencyRevenue": None,
                    "leaseRevenue": None,
                    "interventionRevenue": None,
                    "subsidyRevenue": None,
                },
                "debtServiceCoverage": {"cashflowRatio": []},
            },
            "calculatedAt": "2026-07-15T09:07:00",
        },
        "changeMeta": {
            "previousTaskId": None,
            "explicitOverrideKeys": [],
            "derivedChangedKeys": [],
        },
        "calculatedAt": "2026-07-15T09:07:00",
    }
    assert "reports" not in data
    assert "input" not in data["versions"][0]
    assert "result" not in data["versions"][0]


@pytest.mark.asyncio
async def test_task_input_returns_owned_completed_frozen_params(history_context):
    client, _, ids = history_context

    response = await client.get(f"/ir/calc/tasks/{ids['v2']}/input")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "taskId": ids["v2"],
        "conversationId": ids["newer"],
        "version": "V2",
        "input": {"spot_charge_avg": 0.22},
        "changeMeta": {
            "previousTaskId": None,
            "explicitOverrideKeys": [],
            "derivedChangedKeys": [],
        },
    }


@pytest.mark.asyncio
async def test_batch_task_inputs_returns_items_in_first_seen_order_and_deduplicates(history_context):
    client, maker, ids = history_context
    async with maker() as session:
        old_task = await session.get(CalculationTaskORM, ids["old_task"])
        session.add(InputSnapshotORM(task_id=old_task.id, payload={
            "apiInput": {"capacity_mwh": 800},
            "changeMeta": {"explicitOverrideKeys": ["capacity_mwh"]},
            "minInput": {"internal": True},
        }))
        await session.commit()

    response = await client.post(
        "/ir/calc/tasks/inputs",
        json={"taskIds": [ids["old_task"], ids["v2"], ids["old_task"]]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "taskId": ids["old_task"],
            "conversationId": ids["older"],
            "version": "V1",
            "input": {"capacity_mwh": 800},
            "changeMeta": {"explicitOverrideKeys": ["capacity_mwh"]},
        },
        {
            "taskId": ids["v2"],
            "conversationId": ids["newer"],
            "version": "V2",
            "input": {"spot_charge_avg": 0.22},
            "changeMeta": {
                "previousTaskId": None,
                "explicitOverrideKeys": [],
                "derivedChangedKeys": [],
            },
        },
    ]
    assert "minInput" not in response.text


@pytest.mark.asyncio
async def test_batch_task_inputs_silently_skips_unavailable_tasks(history_context):
    client, _, ids = history_context

    response = await client.post(
        "/ir/calc/tasks/inputs",
        json={"taskIds": [
            ids["v2"], ids["v1"], ids["deleted_task"], ids["foreign_task"], 999999,
        ]},
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["taskId"] for item in items] == [ids["v2"]]
    assert items[0]["input"] == {"spot_charge_avg": 0.22}


@pytest.mark.asyncio
async def test_admin_can_read_organization_members_batch_task_inputs(history_context):
    client, _, ids = history_context
    app.dependency_overrides[get_user_scope] = lambda: UserScope(
        current_user_id="history-admin",
        is_admin=True,
        users=(
            OrganizationUser(user_id="history-admin", nick_name="Admin"),
            OrganizationUser(user_id="history-user-2", nick_name="User Two"),
        ),
    )

    response = await client.post(
        "/ir/calc/tasks/inputs",
        json={"taskIds": [ids["foreign_task"], ids["v2"]]},
        headers={"userId": "history-admin", "username": "Admin"},
    )

    assert response.status_code == 200
    assert [item["taskId"] for item in response.json()["data"]["items"]] == [
        ids["foreign_task"],
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"taskIds": []},
    {"taskIds": [0]},
    {"taskIds": [-1]},
    {"taskIds": ["not-an-id"]},
    {"taskIds": list(range(1, 52))},
])
async def test_batch_task_inputs_rejects_invalid_request_shape(history_context, payload):
    client, _, _ = history_context

    response = await client.post("/ir/calc/tasks/inputs", json=payload)

    assert response.status_code == 400
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_batch_task_inputs_static_route_is_not_captured_as_task_id(history_context):
    client, _, _ = history_context

    response = await client.post("/ir/calc/tasks/inputs", json={"taskIds": [999999]})

    assert response.status_code == 200
    assert response.json()["data"] == {"items": []}


@pytest.mark.asyncio
async def test_admin_can_read_organization_members_task_result(history_context):
    client, _, ids = history_context
    app.dependency_overrides[get_user_scope] = lambda: UserScope(
        current_user_id="history-admin",
        is_admin=True,
        users=(
            OrganizationUser(user_id="history-admin", nick_name="Admin"),
            OrganizationUser(user_id="history-user-2", nick_name="User Two"),
        ),
    )

    response = await client.get(
        f"/ir/calc/tasks/{ids['foreign_task']}/result",
        headers={"userId": "history-admin", "username": "Admin"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["marker"] == "foreign"


@pytest.mark.asyncio
async def test_admin_can_read_organization_members_task_input(history_context):
    client, _, ids = history_context
    app.dependency_overrides[get_user_scope] = lambda: UserScope(
        current_user_id="history-admin",
        is_admin=True,
        users=(
            OrganizationUser(user_id="history-admin", nick_name="Admin"),
            OrganizationUser(user_id="history-user-2", nick_name="User Two"),
        ),
    )

    response = await client.get(
        f"/ir/calc/tasks/{ids['foreign_task']}/input",
        headers={"userId": "history-admin", "username": "Admin"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "taskId": ids["foreign_task"],
        "conversationId": ids["foreign"],
        "version": "V1",
        "input": {"spot_charge_avg": 0.31},
        "changeMeta": {},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("task_key", ["v1", "old_task", "deleted_task"])
async def test_task_input_returns_404_without_available_snapshot(history_context, task_key):
    client, _, ids = history_context
    app.dependency_overrides.pop(get_user_scope, None)

    response = await client.get(f"/ir/calc/tasks/{ids[task_key]}/input")

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_task_input_returns_404_for_unknown_task(history_context):
    client, _, _ = history_context

    response = await client.get("/ir/calc/tasks/999999/input")

    assert response.status_code == 404
    assert response.json()["data"] is None



    client, maker, ids = history_context
    async with maker() as session:
        before = {
            "messages": await session.scalar(select(func.count()).select_from(MessageSnapshotORM)),
            "tasks": await session.scalar(select(func.count()).select_from(CalculationTaskORM)),
            "results": await session.scalar(select(func.count()).select_from(CalculationResultSnapshotORM)),
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
            "results": await session.scalar(select(func.count()).select_from(CalculationResultSnapshotORM)),
        }
    assert after == before
    assert (await client.get("/ir/conversations")).json()["data"]["items"] == [
        {
            "conversationId": ids["empty_failed"],
            "title": "Failed only",
            "createdAt": "2026-07-15T09:40:00",
            "lastActivityAt": "2026-07-15T09:41:00",
        },
        {
            "conversationId": ids["older"],
            "title": "Older active",
            "createdAt": "2026-07-15T09:00:00",
            "lastActivityAt": "2026-07-15T09:08:00",
        },
    ]


@pytest.mark.asyncio
async def test_delete_attempts_all_distinct_feishu_copies_and_ignores_cleanup_failures(
    history_context, monkeypatch
):
    client, maker, ids = history_context
    attempts = []

    async with maker() as session:
        v2 = await session.get(CalculationTaskORM, ids["v2"])
        v2.feishu_copy_url = "doc-v2"
        session.add_all([
            CalculationTaskORM(
                conversation_id=ids["newer"], version="V3", status="completed",
                request_id="req-v3", feishu_copy_url="doc-v3",
            ),
            CalculationTaskORM(
                conversation_id=ids["newer"], version="V4", status="completed",
                request_id="req-v4", feishu_copy_url="doc-v3",
            ),
        ])
        await session.commit()

    class Gateway:
        async def delete_file(self, doc_token):
            attempts.append(doc_token)
            if doc_token == "doc-v2":
                raise RuntimeError("飞书文件不存在")

    monkeypatch.setattr(conversation_router, "build_feishu_gateway", lambda: Gateway())

    response = await client.delete(f"/ir/conversations/{ids['newer']}")

    assert response.status_code == 200
    assert response.json()["data"] == {"conversationId": ids["newer"], "deleted": True}
    assert set(attempts) == {"doc-v2", "doc-v3"}
    assert len(attempts) == 2
    async with maker() as session:
        conversation = await session.get(ConversationORM, ids["newer"])
        assert conversation.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_route_returns_before_feishu_cleanup_starts(history_context, monkeypatch):
    _, maker, ids = history_context
    builds = []
    attempts = []

    async with maker() as session:
        task = await session.get(CalculationTaskORM, ids["v2"])
        task.feishu_copy_url = "doc-v2"
        await session.commit()

        class Gateway:
            async def delete_file(self, doc_token):
                attempts.append(doc_token)

            async def close(self):
                pass

        def build_gateway():
            builds.append(True)
            return Gateway()

        monkeypatch.setattr(conversation_router, "build_feishu_gateway", build_gateway)
        background_tasks = BackgroundTasks()

        response = await conversation_router.delete_conversation(
            conversation_id=ids["newer"],
            background_tasks=background_tasks,
            user=CurrentUser(user_id="history-user-1", username="User One"),
            session=session,
        )

    assert response["data"] == {"conversationId": ids["newer"], "deleted": True}
    assert builds == []
    assert attempts == []
    assert len(background_tasks.tasks) == 1

    await background_tasks()

    assert builds == [True]
    assert attempts == ["doc-v2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path_key", [
    ("get", "conversation"),
    ("delete", "conversation"),
    ("get", "status"),
    ("get", "result"),
    ("get", "input"),
    ("get", "latest_input"),
    ("post", "append"),
])
async def test_cross_user_resources_return_404(history_context, method, path_key):
    client, _, ids = history_context
    paths = {
        "conversation": f"/ir/conversations/{ids['foreign']}",
        "status": f"/ir/calc/tasks/{ids['foreign_task']}",
        "result": f"/ir/calc/tasks/{ids['foreign_task']}/result",
        "input": f"/ir/calc/tasks/{ids['foreign_task']}/input",
        "latest_input": "/ir/calc/tasks/latest-input",
        "append": "/ir/calc/tasks",
    }
    kwargs = {}
    if path_key == "append":
        kwargs["json"] = {
            "province": "甘肃",
            "capacity_mwh": 800,
            "power_mw": 200,
        }
        kwargs["headers"] = {**_USER_1, "X-IR-Conversation-Id": ids["foreign"]}
    elif path_key == "latest_input":
        kwargs["headers"] = {**_USER_1, "X-IR-Conversation-Id": ids["foreign"]}

    response = await getattr(client, method)(paths[path_key], **kwargs)

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_latest_input_returns_latest_completed_frozen_params(history_context):
    """GET /ir/calc/tasks/latest-input 返回最近一次成功版本的冻结入参。"""
    client, _, ids = history_context

    response = await client.get(
        "/ir/calc/tasks/latest-input",
        headers={**_USER_1, "X-IR-Conversation-Id": ids["newer"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["taskId"] == ids["v2"]  # newer 会话最新成功版本是 V2
    assert data["version"] == "V2"
    assert data["input"] == {"spot_charge_avg": 0.22}


@pytest.mark.asyncio
async def test_latest_input_missing_conversation_header_returns_404(history_context):
    client, _, _ = history_context

    response = await client.get("/ir/calc/tasks/latest-input")

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_latest_input_conversation_without_success_version_returns_404(history_context):
    """会话只有失败任务（empty_failed）时，无成功版本 → 404。"""
    client, _, ids = history_context

    response = await client.get(
        "/ir/calc/tasks/latest-input",
        headers={**_USER_1, "X-IR-Conversation-Id": ids["empty_failed"]},
    )

    assert response.status_code == 404
    assert response.json()["data"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["status", "result"])
async def test_tasks_in_soft_deleted_conversation_return_404(history_context, path):
    client, _, ids = history_context
    suffix = "/result" if path == "result" else ""

    response = await client.get(f"/ir/calc/tasks/{ids['deleted_task']}{suffix}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rename_updates_title_and_lists_new_title(history_context):
    client, _, ids = history_context

    response = await client.patch(
        f"/ir/conversations/{ids['older']}",
        json={"title": "  甘肃 200MW/800MWh 复核  "},
    )

    assert response.status_code == 200
    # 首尾空白被裁剪后落库
    assert response.json()["data"] == {
        "conversationId": ids["older"],
        "title": "甘肃 200MW/800MWh 复核",
    }
    items = (await client.get("/ir/conversations")).json()["data"]["items"]
    titles = {item["conversationId"]: item["title"] for item in items}
    assert titles[ids["older"]] == "甘肃 200MW/800MWh 复核"


@pytest.mark.asyncio
@pytest.mark.parametrize("title", ["", "   "])
async def test_rename_rejects_blank_title(history_context, title):
    client, _, ids = history_context

    response = await client.patch(
        f"/ir/conversations/{ids['newer']}",
        json={"title": title},
    )

    assert response.status_code == 400
    assert response.json()["data"] is None


@pytest.mark.asyncio
async def test_rename_foreign_conversation_returns_404(history_context):
    client, _, ids = history_context

    response = await client.patch(
        f"/ir/conversations/{ids['foreign']}",
        json={"title": "越权改名"},
    )

    assert response.status_code == 404
    assert response.json()["data"] is None
