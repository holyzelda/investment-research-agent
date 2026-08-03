"""连测试库 ir_agent · 测算任务接口 e2e（真实留痕）。

关键链路：POST /tasks → V1 且状态 completed；GET status/result 脱离飞书读快照；
同会话再发 → V2（不覆盖）。用 dependency_overrides 把 get_db_session 指向真实测试库。
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.session import get_db_session
from app.main import app

_HEADERS = {"userId": "1001", "username": "__pytest__"}


@pytest.fixture
async def client(db_engine):
    """e2e 客户端：把 DB 依赖覆盖为真实测试库 session。"""
    maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=_HEADERS) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_task_create_status_result_and_versioning(client):
    # 发起 V1
    r = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200, "node_name": "兰州东",
    })
    assert r.status_code == 200
    d1 = r.json()["data"]
    assert d1["version"] == "V1"
    assert d1["status"] == "completed"
    conv_id, task1 = d1["conversationId"], d1["taskId"]

    # 状态查询（脱离飞书）
    rs = await client.get(f"/ir/calc/tasks/{task1}")
    assert rs.json()["data"]["status"] == "completed"

    # 结果三模块来自 calculation_result_snapshot
    rr = await client.get(f"/ir/calc/tasks/{task1}/result")
    rep = rr.json()["data"]
    assert rep["basicInfo"]["province"] == "甘肃"
    assert rep["basicInfo"]["nodeName"] == "兰州东"
    assert "calculatedAt" in rep  # 结果附带任务落库时间，供前端结果卡展示
    assert rep["advanced"]["debtServiceCoverage"]["cashflowRatio"] == [
        1.12, 1.24, 0.0, None, 1.36, 1.48,
    ]

    # 同会话按中台回调契约再发 → V2（不覆盖）
    r2 = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    }, headers={**_HEADERS, "conversation_id": conv_id})
    d2 = r2.json()["data"]
    assert d2["conversationId"] == conv_id
    assert d2["version"] == "V2"


@pytest.mark.asyncio
async def test_invalid_conversation_id_returns_400(client):
    r = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    }, headers={**_HEADERS, "conversation_id": "not-a-uuid"})

    assert r.status_code == 400
    assert r.json() == {"code": 400, "msg": "conversation_id 格式无效", "data": None}


@pytest.mark.asyncio
async def test_province_change_returns_failed_without_creating_task(client, db_engine):
    from app.modules.calculation.infrastructure.persistence.orm import CalculationTaskORM

    first = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    })
    conversation_id = first.json()["data"]["conversationId"]

    rejected = await client.post("/ir/calc/tasks", json={
        "province": "宁夏", "capacity_mwh": 800, "power_mw": 200,
    }, headers={**_HEADERS, "conversation_id": conversation_id})

    assert rejected.status_code == 200
    data = rejected.json()["data"]
    assert data["conversationId"] == conversation_id
    assert data["status"] == "failed"
    assert data["taskCreated"] is False
    assert data["taskId"] is None
    assert data["version"] is None
    assert data["error"]["code"] == 400
    assert "省份在当前会话中不可修改" in data["error"]["message"]
    assert data["requestId"] == data["error"]["requestId"]

    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        tasks = (await session.execute(
            select(CalculationTaskORM).where(
                CalculationTaskORM.conversation_id == conversation_id
            )
        )).scalars().all()
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_unknown_conversation_returns_failed_result(client):
    conversation_id = "51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6"
    rejected = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    }, headers={**_HEADERS, "conversation_id": conversation_id})

    assert rejected.status_code == 200
    data = rejected.json()["data"]
    assert data["conversationId"] == conversation_id
    assert data["status"] == "failed"
    assert data["taskCreated"] is False
    assert data["taskId"] is None
    assert data["error"]["code"] == 404
    assert data["error"]["message"] == "会话不存在"
    assert data["requestId"] == data["error"]["requestId"]


@pytest.mark.asyncio
async def test_missing_task_returns_404(client):
    r = await client.get("/ir/calc/tasks/99999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_task_failure_is_persisted_and_readable(client, monkeypatch):
    """引擎不可重试失败 → 落 failed 任务（真实留痕）→ GET 读回 error。"""
    from app.core.config.settings import get_settings
    from app.modules.calculation.application import factory as calc_factory
    from app.modules.calculation.application.snapshot_service import SnapshotService
    from app.modules.calculation.application.task_service import CalculationTaskService
    from app.modules.calculation.domain.execution import NonRetryableCalcError
    from app.modules.calculation.domain.ports import FeishuGateway
    from app.modules.calculation.interface import router as calc_router

    class FailingGateway(FeishuGateway):
        async def copy_template(self, template_token, name=None):
            return "doc-fail"

        async def write_input(self, doc_token, payload):
            raise NonRetryableCalcError("模拟飞书鉴权失败", code="feishu_auth_401")

        async def write_meta(self, doc_token, meta):
            return None

        async def read_meta(self, doc_token):
            return {}

        async def read_output(self, doc_token):
            return {}

    def _failing_task_service():
        gw = FailingGateway()
        return CalculationTaskService(
            assembler=calc_factory.build_param_assembler(),
            gateway=gw,
            engine=calc_factory.build_calc_engine(gateway=gw),
            retry=calc_factory.build_retry_policy(),
            snapshot=SnapshotService(),
            feishu=get_settings().feishu,
        )

    monkeypatch.setattr(calc_router, "build_task_service", _failing_task_service)

    r = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    })
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["status"] == "failed"
    assert d["taskCreated"] is True
    assert d["requestId"] == d["error"]["requestId"]
    assert d["error"] == {
        "code": "feishu_auth_401",
        "message": "模拟飞书鉴权失败",
        "requestId": d["error"]["requestId"],
        "retryCount": 0,
    }

    # 失败任务落库留痕，状态查询脱离飞书读回相同 error。
    rs = await client.get(f"/ir/calc/tasks/{d['taskId']}")
    body = rs.json()["data"]
    assert body["status"] == "failed"
    assert body["requestId"] == d["error"]["requestId"]


@pytest.mark.asyncio
async def test_retryable_task_failure_keeps_root_cause_and_retry_count(client, monkeypatch, db_engine):
    """重试耗尽后保留最终飞书根因，并在 POST/DB/GET 间一致。"""
    from app.core.config.settings import get_settings
    from app.modules.calculation.application import factory as calc_factory
    from app.modules.calculation.application.retry_policy import RetryPolicy
    from app.modules.calculation.application.snapshot_service import SnapshotService
    from app.modules.calculation.application.task_service import CalculationTaskService
    from app.modules.calculation.domain.execution import RetryableCalcError
    from app.modules.calculation.domain.ports import FeishuGateway
    from app.modules.calculation.infrastructure.persistence.orm import CalculationTaskORM
    from app.modules.calculation.interface import router as calc_router

    class RetryableGateway(FeishuGateway):
        async def copy_template(self, template_token, name=None):
            return "doc-retry"

        async def write_input(self, doc_token, payload):
            raise RetryableCalcError("飞书副本仍在处理中", code="feishu_601124041")

        async def write_meta(self, doc_token, meta):
            return None

        async def read_meta(self, doc_token):
            return {}

        async def read_output(self, doc_token):
            return {}

    def _retryable_task_service():
        gw = RetryableGateway()
        return CalculationTaskService(
            assembler=calc_factory.build_param_assembler(),
            gateway=gw,
            engine=calc_factory.build_calc_engine(gateway=gw),
            retry=RetryPolicy(max_retries=1),
            snapshot=SnapshotService(),
            feishu=get_settings().feishu,
        )

    monkeypatch.setattr(calc_router, "build_task_service", _retryable_task_service)

    r = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    })
    assert r.status_code == 200
    created = r.json()["data"]
    expected_error = {
        "code": "feishu_601124041",
        "message": "飞书副本仍在处理中",
        "requestId": created["error"]["requestId"],
        "retryCount": 1,
    }
    assert created["status"] == "failed"
    assert created["taskCreated"] is True
    assert created["requestId"] == created["error"]["requestId"]
    assert created["error"] == expected_error

    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        task = (await session.execute(
            select(CalculationTaskORM).where(CalculationTaskORM.id == created["taskId"])
        )).scalar_one()
    assert (task.error_code, task.error_message, task.retry_count) == (
        "feishu_601124041", "飞书副本仍在处理中", 1,
    )

    status = (await client.get(f"/ir/calc/tasks/{created['taskId']}")).json()["data"]
    assert status["requestId"] == expected_error["requestId"]
    assert status["error"] == expected_error


@pytest.mark.asyncio
async def test_task_accepts_duration_only_and_freezes_normalized_basics(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "duration_hours": 2,
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["input"]["power_mw"] == 100
    assert data["input"]["capacity_mwh"] == 200
    assert "duration_hours" not in data["input"]


@pytest.mark.asyncio
async def test_task_accepts_power_and_duration(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "power_mw": 100,
        "duration_hours": 2,
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["input"]["power_mw"] == 100
    assert data["input"]["capacity_mwh"] == 200


@pytest.mark.asyncio
async def test_task_rejects_inconsistent_capacity_power_and_duration(client):
    response = await client.post("/ir/calc/tasks", json={
        "province": "甘肃",
        "capacity_mwh": 150,
        "power_mw": 100,
        "duration_hours": 2,
    })

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert "不一致" in response.json()["msg"]
