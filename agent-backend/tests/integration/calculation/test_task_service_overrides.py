"""任务编排 · 受控参数覆盖 + 现货依赖重查/继承（Batch5，2026-07-15 确认规则）。

用 sqlite 内存库 + MockFeishuGateway，全程不连真实 MySQL/飞书。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config.settings import FeishuConfig
from app.core.exceptions import NotFoundException, ValidationException
from app.infrastructure.database.base import Base
from app.modules.calculation.application.factory import build_param_assembler
from app.modules.calculation.application.feishu_calc_engine import FeishuCalcEngine
from app.modules.calculation.application.retry_policy import RetryPolicy
from app.modules.calculation.application.snapshot_service import SnapshotService
from app.modules.calculation.application.task_service import CalculationTaskService
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.feishu_client import MockFeishuGateway
from app.modules.calculation.infrastructure.feishu_sample import sample_output
from app.modules.calculation.infrastructure.persistence.orm import InputSnapshotORM


class _CountingSpot:
    def __init__(self, charge=0.2, discharge=0.6):
        self.calls = []
        self._charge = charge
        self._discharge = discharge

    def compute(self, province, node_name, capacity_mwh, power_mw, daily_cycles):
        self.calls.append({
            "node_name": node_name, "capacity_mwh": capacity_mwh,
            "power_mw": power_mw, "daily_cycles": daily_cycles,
        })
        return self._charge, self._discharge


@pytest.fixture
async def session_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


def _service(spot):
    gateway = MockFeishuGateway(output=sample_output())
    return CalculationTaskService(
        assembler=build_param_assembler(spot=spot),
        gateway=gateway,
        engine=FeishuCalcEngine(gateway=gateway, poll_interval=0, poll_timeout=1),
        retry=RetryPolicy(max_retries=0),
        snapshot=SnapshotService(),
        feishu=FeishuConfig(template_token_15_years="template-15", template_token_20_years="template-20"),
    )


def _service_with_templates(spot):
    gateway = MockFeishuGateway(output=sample_output())
    service = CalculationTaskService(
        assembler=build_param_assembler(spot=spot),
        gateway=gateway,
        engine=FeishuCalcEngine(gateway=gateway, poll_interval=0, poll_timeout=1),
        retry=RetryPolicy(max_retries=0),
        snapshot=SnapshotService(),
        feishu=FeishuConfig(template_token_15_years="template-15", template_token_20_years="template-20"),
    )
    return service, gateway


_BASICS = ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200, node_name="祥泰站")


@pytest.mark.asyncio
async def test_v1_selects_15_year_template_by_default(session_maker):
    service, gateway = _service_with_templates(_CountingSpot())
    async with session_maker() as session:
        await service.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
    assert gateway.copy_templates == ["template-15"]


@pytest.mark.asyncio
async def test_same_conversation_can_switch_to_20_year_template(session_maker):
    service, gateway = _service_with_templates(_CountingSpot())
    async with session_maker() as session:
        v1 = await service.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        v2 = await service.create_and_run(
            session,
            user_id="u1",
            username="U1",
            basics=_BASICS,
            conversation_id=v1["conversationId"],
            param_overrides={"operation_years": 20},
        )
    assert v2["input"]["operation_years"] == 20
    assert gateway.copy_templates == ["template-15", "template-20"]


@pytest.mark.asyncio
async def test_invalid_operation_years_does_not_copy_template(session_maker):
    service, gateway = _service_with_templates(_CountingSpot())
    async with session_maker() as session:
        with pytest.raises(ValidationException, match="项目运营期仅支持15年或20年"):
            await service.create_and_run(
                session,
                user_id="u1",
                username="U1",
                basics=_BASICS,
                param_overrides={"operation_years": 14},
            )
    assert gateway.copy_templates == []


@pytest.mark.asyncio
async def test_v1_always_queries_spot(session_maker):
    spot = _CountingSpot()
    svc = _service(spot)
    async with session_maker() as session:
        out = await svc.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS,
        )
    assert out["version"] == "V1"
    assert len(spot.calls) == 1
    assert out["input"]["spot_charge_avg"] == 0.2  # 成功响应携带本次冻结入参，供前端做种子基线


@pytest.mark.asyncio
async def test_recalc_unchanged_dependencies_no_override_inherits_v1_price(session_maker):
    spot = _CountingSpot(charge=0.2, discharge=0.6)
    svc = _service(spot)
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        spot.calls.clear()
        v2 = await svc.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS,
            conversation_id=v1["conversationId"],
        )
    assert v2["version"] == "V2"
    assert spot.calls == []  # 依赖未变、未提交 override → 不查库


@pytest.mark.asyncio
async def test_recalc_manual_spot_override_not_queried_and_frozen(session_maker):
    spot = _CountingSpot(charge=0.2, discharge=0.6)
    svc = _service(spot)
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        spot.calls.clear()
        v2 = await svc.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS,
            conversation_id=v1["conversationId"],
            param_overrides={"spot_charge_avg": 0.35},
        )
        snap = (await session.execute(
            select(InputSnapshotORM).where(InputSnapshotORM.task_id == v2["taskId"])
        )).scalar_one()
    assert spot.calls == []
    assert snap.payload["apiInput"]["spot_charge_avg"] == 0.35
    assert snap.payload["apiInput"]["spot_discharge_avg"] == 0.6  # 未改的一侧沿用 V1


@pytest.mark.asyncio
async def test_v3_inherits_v2_manual_price_without_requery(session_maker):
    spot = _CountingSpot(charge=0.2, discharge=0.6)
    svc = _service(spot)
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        conv = v1["conversationId"]
        await svc.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS,
            conversation_id=conv, param_overrides={"spot_charge_avg": 0.35},
        )
        spot.calls.clear()
        v3 = await svc.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS, conversation_id=conv,
        )
        snap = (await session.execute(
            select(InputSnapshotORM).where(InputSnapshotORM.task_id == v3["taskId"])
        )).scalar_one()
    assert spot.calls == []
    assert snap.payload["apiInput"]["spot_charge_avg"] == 0.35


@pytest.mark.asyncio
async def test_node_change_requeries_spot(session_maker):
    spot = _CountingSpot(charge=0.2, discharge=0.6)
    svc = _service(spot)
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        spot.calls.clear()
        changed = ProjectBasics(
            province="甘肃", capacity_mwh=800, power_mw=200, node_name="新节点",
        )
        await svc.create_and_run(
            session, user_id="u1", username="U1", basics=changed,
            conversation_id=v1["conversationId"],
        )
    assert len(spot.calls) == 1
    assert spot.calls[0]["node_name"] == "新节点"


@pytest.mark.asyncio
async def test_province_locked_after_first_calc(session_maker):
    svc = _service(_CountingSpot())
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        changed_province = ProjectBasics(
            province="宁夏", capacity_mwh=800, power_mw=200, node_name="祥泰站",
        )
        with pytest.raises(ValidationException):
            await svc.create_and_run(
                session, user_id="u1", username="U1", basics=changed_province,
                conversation_id=v1["conversationId"],
            )


@pytest.mark.asyncio
async def test_unknown_conversation_raises_not_found(session_maker):
    svc = _service(_CountingSpot())
    async with session_maker() as session:
        with pytest.raises(NotFoundException):
            await svc.create_and_run(
                session, user_id="u1", username="U1", basics=_BASICS,
                conversation_id="51cf6ef3-5436-4c3a-8ce8-7cc6488d0fa6",
            )


@pytest.mark.asyncio
async def test_cross_user_conversation_is_not_found(session_maker):
    svc = _service(_CountingSpot())
    async with session_maker() as session:
        v1 = await svc.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        with pytest.raises(NotFoundException):
            await svc.create_and_run(
                session, user_id="u2", username="U2", basics=_BASICS,
                conversation_id=v1["conversationId"],
            )
