"""连测试库 ir_agent · 测算任务接口 e2e（真实留痕）。

关键链路：POST /tasks → V1 且状态 completed；GET status/result 脱离飞书读快照；
同会话再发 → V2（不覆盖）。用 dependency_overrides 把 get_db_session 指向真实测试库。
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.session import get_db_session
from app.main import app

_HEADERS = {"X-User-Id": "1001", "X-User-Name": "__pytest__"}


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

    # 结果三模块来自 report_snapshot
    rr = await client.get(f"/ir/calc/tasks/{task1}/result")
    rep = rr.json()["data"]
    assert rep["basicInfo"]["province"] == "甘肃"
    assert rep["basicInfo"]["nodeName"] == "兰州东"
    assert rep["advanced"]["debtServiceCoverage"]["cashflowRatio"] == [
        1.12, 1.24, 0.0, None, 1.36, 1.48,
    ]

    # 同会话再发 → V2（不覆盖）
    r2 = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
        "conversation_id": conv_id,
    })
    assert r2.json()["data"]["version"] == "V2"


@pytest.mark.asyncio
async def test_missing_task_returns_404(client):
    r = await client.get("/ir/calc/tasks/99999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_task_failure_is_persisted_and_readable(client, monkeypatch):
    """引擎不可重试失败 → 落 failed 任务（真实留痕）→ GET 读回 error。"""
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
            feishu=calc_factory.get_settings().feishu,
        )

    monkeypatch.setattr(calc_router, "build_task_service", _failing_task_service)

    r = await client.post("/ir/calc/tasks", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    })
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["status"] == "failed"
    assert d["error"]["code"] == "feishu_auth_401"

    # 失败任务落库留痕，状态查询脱离飞书读回 error
    rs = await client.get(f"/ir/calc/tasks/{d['taskId']}")
    body = rs.json()["data"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == "feishu_auth_401"

