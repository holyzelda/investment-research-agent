"""calculation 应用层 · 测算任务编排（发起→执行→快照→版本）。

一次 POST /ir/calc/tasks 的用例：
1. 会话：无 conversation_id 则新建（V1）；有则在其下追加（版本递增，不覆盖）。
2. 组装四来源入参，生成 request_id 与 param_hash。
3. 引擎 + 智能重试执行（复用同副本）；成功→映射结果 DTO + 落 7 类快照；失败→落 failed 任务。
4. 返回 {conversationId, taskId, version, status}。

状态/结果查询是纯读快照，不再触飞书（脱离飞书可用）。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import FeishuConfig
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.calculation.application.feishu_calc_engine import FeishuCalcEngine
from app.modules.calculation.application.conversation_history_service import ConversationHistoryService
from app.modules.calculation.application.output_mapper import map_output_to_result
from app.modules.calculation.application.param_assembler import ParamAssembler
from app.modules.calculation.application.retry_policy import RetryPolicy
from app.modules.calculation.application.report_source_freezer import freeze_report_sources
from app.modules.calculation.application.snapshot_service import SnapshotService
from app.modules.calculation.domain.execution import CalcError
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.domain.ports import FeishuGateway
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
)


def _param_hash(api_input: dict) -> str:
    canon = json.dumps(api_input, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _min_input(basics: ProjectBasics) -> dict:
    return {
        "province": basics.province,
        "city": basics.city,
        "capacityMwh": basics.capacity_mwh,
        "powerMw": basics.power_mw,
        "nodeName": basics.node_name,
        "voltageKv": basics.voltage_kv,
    }


def _fmt_num(x) -> str:
    """副本名里的数字：200.0→'200'，800.5→'800.5'（避免出现 .0）。"""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def build_copy_name(basics: ProjectBasics, *, now: Optional[datetime] = None) -> str:
    """飞书副本命名：城市-节点(有则加)-功率/容量-时间(到秒)。

    例：宁夏-200/400-20260710091435；带节点：宁夏-东站-200/400-20260710091435。
    now 可注入，便于测试固定时间戳。
    """
    ts = (now or datetime.now()).strftime("%Y%m%d%H%M%S")
    parts = [basics.province]
    if basics.city:
        parts.append(basics.city)
    if basics.node_name:
        parts.append(basics.node_name)
    parts.append(f"{_fmt_num(basics.power_mw)}/{_fmt_num(basics.capacity_mwh)}")
    parts.append(ts)
    return "-".join(parts)


class CalculationTaskService:
    def __init__(
        self,
        assembler: ParamAssembler,
        gateway: FeishuGateway,
        engine: FeishuCalcEngine,
        retry: RetryPolicy,
        snapshot: SnapshotService,
        feishu: FeishuConfig,
    ):
        self._assembler = assembler
        self._gateway = gateway
        self._engine = engine
        self._retry = retry
        self._snapshot = snapshot
        self._feishu = feishu

    def _template_token_for(self, api_input: dict) -> str:
        operation_years = api_input.get("operation_years", 15)
        if operation_years == 15:
            return self._feishu.template_token_15_years
        if operation_years == 20:
            return self._feishu.template_token_20_years
        raise ValidationException("项目运营期仅支持15年或20年")

    async def create_and_run(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        username: str,
        basics: ProjectBasics,
        conversation_id: Optional[str] = None,
        param_overrides: Optional[dict] = None,
        trigger: Optional[str] = None,
    ) -> dict:
        request_id = uuid.uuid4().hex
        try:
            conversation_id, version, previous_input, previous_task_id = await self._resolve_version(
                session, conversation_id, user_id, username, basics
            )
        except (ValidationException, NotFoundException) as e:
            error_message = str(e)[:500]
            if conversation_id is not None and isinstance(e, ValidationException):
                await ConversationHistoryService().append_calculation_error(
                    session,
                    conversation_id=conversation_id,
                    error_message=error_message,
                    error_code=e.code,
                )
            return {
                "conversationId": conversation_id,
                "taskId": None,
                "version": None,
                "status": "failed",
                "taskCreated": False,
                "requestId": request_id,
                "error": {
                    "code": e.code,
                    "message": error_message,
                    "requestId": request_id,
                    "retryCount": 0,
                },
            }

        # 现货组装和飞书执行都可能持续较久。前面的版本查询（以及 V1
        # 创建会话的 flush）不能让主库连接跨越这段同步/远程调用时间。
        # 提交后，快照服务会在执行完成后为结果写入开启新的事务。
        await session.commit()

        assembled = self._assembler.assemble(
            basics, overrides=param_overrides, previous_input=previous_input)
        change_meta = self._build_change_meta(
            previous_task_id=previous_task_id,
            previous_input=previous_input,
            api_input=assembled.api_input,
            param_overrides=param_overrides,
            basics=basics,
        )
        param_hash = _param_hash(assembled.api_input)
        template_token = self._template_token_for(assembled.api_input)
        copy_name = build_copy_name(basics)  # 城市-节点-功率/容量-时间，副本创建时定格

        try:
            engine_result = await self._retry.run_with_retry(
                lambda doc_token: self._engine.run(
                    api_input=assembled.api_input,
                    request_id=request_id,
                    param_hash=param_hash,
                    doc_token=doc_token,
                ),
                request_id=request_id,
                copy_template=lambda: self._gateway.copy_template(template_token, copy_name),
            )
        except CalcError as e:
            error_message = str(e)[:500]
            task = CalculationTaskORM(
                conversation_id=conversation_id,
                version=version,
                status="failed",
                request_id=request_id,
                param_hash=param_hash,
                error_code=e.code,
                error_message=error_message,
                retry_count=e.retry_count,
            )
            session.add(task)
            await session.commit()
            await ConversationHistoryService().append_calculation_error(
                session,
                conversation_id=conversation_id,
                error_message=error_message,
                task_id=task.id,
                error_code=e.code,
            )
            return {
                "conversationId": conversation_id,
                "taskId": task.id,
                "version": version,
                "status": "failed",
                "taskCreated": True,
                "requestId": request_id,
                "error": {
                    "code": e.code,
                    "message": error_message,
                    "requestId": request_id,
                    "retryCount": e.retry_count,
                },
            }

        result_dto = map_output_to_result(
            basics, assembled, engine_result.api_output,
            version=version, request_id=request_id,
        )
        report_sources = await freeze_report_sources(
            self._gateway,
            doc_token=engine_result.doc_token,
            api_input=assembled.api_input,
            config=self._feishu,
        )
        task_id = await self._snapshot.persist_success(
            session,
            conversation_id=conversation_id,
            version=version,
            request_id=request_id,
            param_hash=param_hash,
            doc_token=engine_result.doc_token,
            assembled=assembled,
            api_output=engine_result.api_output,
            api_meta=engine_result.meta,
            result=result_dto,
            min_input=_min_input(basics),
            change_meta=change_meta,
            report_sources=report_sources,
            trigger=trigger,
            assistant_message=f"{version} 测算完成",
        )
        return {
            "conversationId": conversation_id,
            "taskId": task_id,
            "version": version,
            "status": "completed",
            "taskCreated": True,
            "requestId": request_id,
            "input": assembled.api_input,  # 本次冻结入参，供前端调整面板下次重算时做种子基线
            "changeMeta": change_meta,
        }

    async def _resolve_version(
        self, session, conversation_id, user_id, username, basics
    ) -> tuple[str, str, Optional[dict], Optional[int]]:
        if conversation_id is None:
            conversation_id = await self._snapshot.create_conversation(
                session, user_id=user_id, username=username,
                title=f"{basics.province} 储能测算",
            )
            return conversation_id, "V1", None, None
        conversation = (await session.execute(
            select(ConversationORM).where(
                ConversationORM.id == conversation_id,
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if conversation is None:
            raise NotFoundException("会话不存在")

        previous_input, previous_task_id = await self._latest_completed_input(session, conversation_id)
        if previous_input is not None and previous_input.get("province") != basics.province:
            # 省份在会话内永久锁定（PRD 2026-07-15 确认）：修改省份必须新建会话重新提问
            raise ValidationException("省份在当前会话中不可修改，请新建会话后重新测算")

        n = await session.scalar(
            select(func.count()).select_from(CalculationTaskORM)
            .where(
                CalculationTaskORM.conversation_id == conversation_id,
                CalculationTaskORM.status == "completed",
            )
        )
        return conversation_id, f"V{(n or 0) + 1}", previous_input, previous_task_id

    async def _latest_completed_input(self, session, conversation_id: str) -> tuple[Optional[dict], Optional[int]]:
        """最近一次成功版本冻结的 api_input（现货依赖比较 + 省份锁定校验的基线）。"""
        latest_task = (await session.execute(
            select(CalculationTaskORM)
            .where(
                CalculationTaskORM.conversation_id == conversation_id,
                CalculationTaskORM.status == "completed",
            )
            .order_by(CalculationTaskORM.created_at.desc(), CalculationTaskORM.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        if latest_task is None:
            return None, None
        snapshot = (await session.execute(
            select(InputSnapshotORM).where(InputSnapshotORM.task_id == latest_task.id)
        )).scalar_one_or_none()
        if snapshot is None:
            return None, latest_task.id
        return snapshot.payload.get("apiInput"), latest_task.id

    @staticmethod
    def _build_change_meta(
        *, previous_task_id: Optional[int], previous_input: Optional[dict],
        api_input: dict, param_overrides: Optional[dict], basics: ProjectBasics,
    ) -> dict:
        if previous_input is None:
            return {}
        # 过滤 null 值：中台路径可能提交值=null 的键（AI 未提及的参数），
        # 面板路径只提交用户实际改动的参数（增量语义），不含 null。
        # 基线参数（规模/节点/电压）始终视为 submitted。
        submitted = set(
            k for k, v in (param_overrides or {}).items()
            if v is not None and (previous_input is None or previous_input.get(k) != v)
        ) | {
            "power_mw", "capacity_mwh", "city", "node_name", "voltage_kv",
        }
        changed = {
            key for key in set(previous_input) | set(api_input)
            if previous_input.get(key) != api_input.get(key)
        }
        explicit = sorted(changed & submitted)
        derived = sorted(changed - set(explicit))
        return {
            "previousTaskId": previous_task_id,
            "explicitOverrideKeys": explicit,
            "derivedChangedKeys": derived,
        }
