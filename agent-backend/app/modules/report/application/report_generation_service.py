"""报告生成服务：任务状态、AI 降级与正式快照原子落库。"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Sequence

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.calculation.application.conversation_history_service import ConversationHistoryService
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    ConversationORM,
    DataSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)
from app.modules.report.application.frozen_section_context import build_section_context
from app.modules.report.application.report_builder import build_report_payload
from app.modules.report.application.report_rules import AI_FALLBACK_TEXT, AI_SECTION_RULES


class ReportGenerationService:
    def __init__(self, ai_client, *, ai_concurrency: int = 5):
        if ai_concurrency < 1:
            raise ValueError("报告 AI 并发数必须大于 0")
        self._ai_client = ai_client
        self._ai_concurrency = ai_concurrency
        self._history = ConversationHistoryService()

    async def start(self, session: AsyncSession, *, task_id: int, user_id: str, username: str | None = None) -> dict:
        task = await self._history.require_owned_task(session, task_id=task_id, user_id=user_id)
        if task.status != "completed":
            raise NotFoundException("测算任务不存在")
        report = (await session.execute(
            select(ReportSnapshotORM).where(ReportSnapshotORM.task_id == task.id)
        )).scalar_one_or_none()
        if report is not None:
            return {"status": "completed", "reportId": report.report_id, "taskId": task.id}
        generation = (await session.execute(
            select(ReportGenerationTaskORM).where(ReportGenerationTaskORM.task_id == task.id)
        )).scalar_one_or_none()
        should_run = False
        if generation is None:
            should_run = True
            generation = ReportGenerationTaskORM(
                task_id=task.id,
                conversation_id=task.conversation_id,
                user_id=user_id,
                username=username,
                steps=[self._step(1, "prepare", "读取冻结测算快照", "active")],
                current_step="prepare",
            )
            session.add(generation)
        elif generation.status == "failed":
            should_run = True
            generation.status = "generating"
            generation.steps = [self._step(1, "prepare", "读取冻结测算快照", "active")]
            generation.current_step = "prepare"
            generation.error_code = None
            generation.error_message = None
            generation.report_id = None
            generation.completed_at = None
        await session.commit()
        data = self.serialize_task(generation)
        data["shouldRun"] = should_run
        return data

    async def run(self, session: AsyncSession, *, report_task_id: int) -> None:
        generation = await session.get(ReportGenerationTaskORM, report_task_id)
        if generation is None or generation.status != "generating":
            return
        try:
            task = await self._history.require_owned_task(
                session, task_id=generation.task_id, user_id=generation.user_id
            )
            input_snapshot = (await session.execute(
                select(InputSnapshotORM).where(InputSnapshotORM.task_id == task.id)
            )).scalar_one()
            data_snapshot = (await session.execute(
                select(DataSnapshotORM).where(DataSnapshotORM.task_id == task.id)
            )).scalar_one()
            result_snapshot = (await session.execute(
                select(CalculationResultSnapshotORM).where(CalculationResultSnapshotORM.task_id == task.id)
            )).scalar_one()
            payload = build_report_payload(
                task=task,
                input_snapshot=input_snapshot,
                data_snapshot=data_snapshot,
                result_snapshot=result_snapshot,
            )
            self._complete_step(generation, "prepare", "读取冻结测算快照")
            generation.current_step = "ai"
            generation.steps = [*generation.steps, self._step(
                len(generation.steps) + 1, "ai", "生成智能分析", "active"
            )]
            await session.commit()
            username = generation.username
            if not username:
                conversation = await session.get(ConversationORM, generation.conversation_id)
                username = conversation.username if conversation is not None else None
            if not username:
                raise RuntimeError("报告生成身份信息缺失")
            generation.username = username
            payload["aiSections"] = await self._generate_ai_sections(
                payload, user_id=generation.user_id, username=username
            )
            self._complete_step(generation, "ai", "生成智能分析")
            report_id = uuid.uuid4().hex
            report = ReportSnapshotORM(
                report_id=report_id,
                task_id=task.id,
                conversation_id=task.conversation_id,
                user_id=generation.user_id,
                payload=payload,
            )
            session.add(report)
            generation.status = "completed"
            generation.report_id = report_id
            generation.current_step = None
            generation.completed_at = datetime.now()
            generation.steps = [*generation.steps, self._step(
                len(generation.steps) + 1, "complete", "报告已生成", "completed"
            )]
            session.add(MessageSnapshotORM(
                conversation_id=task.conversation_id,
                role="assistant",
                content="报告已生成",
                message_type="report_generated",
                payload={"event_type": "report_generated", "report_id": report_id, "task_id": task.id},
            ))
            await session.commit()
        except Exception as exc:
            await session.rollback()
            generation = await session.get(ReportGenerationTaskORM, report_task_id)
            if generation is not None:
                generation.status = "failed"
                generation.current_step = None
                generation.error_code = "report_generation_failed"
                generation.error_message = str(exc)[:512]
                generation.steps = [*generation.steps, self._step(
                    len(generation.steps) + 1, "failed", "报告生成失败", "failed"
                )]
                await session.commit()

    async def _generate_ai_sections(self, payload: dict, *, user_id: str, username: str) -> dict:
        semaphore = asyncio.Semaphore(self._ai_concurrency)
        results = await asyncio.gather(*[
            self._generate_one_ai_section(
                rule,
                payload,
                user_id=user_id,
                username=username,
                semaphore=semaphore,
            )
            for rule in AI_SECTION_RULES
        ])
        by_key = dict(results)
        return {rule["key"]: by_key[rule["key"]] for rule in AI_SECTION_RULES}

    async def _generate_one_ai_section(
        self,
        rule: dict,
        payload: dict,
        *,
        user_id: str,
        username: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, dict]:
        key = rule["key"]
        context = build_section_context(rule, payload)
        try:
            async with semaphore:
                logger.info("报告 AI 调用开始：section={}", key)
                text = await self._ai_client.generate_section(
                    rule, context, user_id=user_id, username=username
                )
            text = self._validate_ai_text(text, rule)
            logger.info("报告 AI 调用成功：section={}", key)
            return key, {
                "status": "generated",
                "attempts": 1,
                "usedFallback": False,
                "text": text,
            }
        except Exception as exc:
            code = self._ai_failure_code(exc)
            logger.warning(
                "报告 AI 调用降级：section={} reason={} error={} detail={}",
                key, code, type(exc).__name__, str(exc),
            )
            return key, self._fallback(code, attempts=1)

    @staticmethod
    def _ai_failure_code(exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "ai_timeout"
        if isinstance(exc, httpx.HTTPStatusError):
            return "ai_upstream_rejected"
        if isinstance(exc, httpx.HTTPError):
            return "ai_transport_error"
        if isinstance(exc, ValidationException):
            return "ai_invalid_response"
        return "ai_output_validation_failed"

    @staticmethod
    def _fallback(code: str, *, attempts: int) -> dict:
        return {
            "status": "fallback",
            "attempts": attempts,
            "usedFallback": True,
            "failureCode": code,
            "text": AI_FALLBACK_TEXT,
        }

    @staticmethod
    def _validate_ai_text(text: str, rule: dict) -> str:
        if not isinstance(text, str) or not (cleaned := text.strip()):
            raise ValueError("AI 正文为空")
        if any(metric in cleaned for metric in rule["forbiddenMetrics"]):
            raise ValueError("AI 正文包含禁用指标")
        if len(cleaned) > rule["maxWords"] * 3:
            raise ValueError("AI 正文超过长度限制")
        return cleaned

    async def get_task(self, session: AsyncSession, *, report_task_id: int, user_id: str) -> dict:
        generation = await self._owned_generation(session, report_task_id, user_id)
        return self.serialize_task(generation)

    async def get_report(
        self, session: AsyncSession, *, report_id: str, user_id: str,
        readable_user_ids: Sequence[str] | None = None,
    ) -> ReportSnapshotORM:
        """只读报告快照。readable_user_ids 仅供管理员查看组织成员报告，生成/重生成不放开。"""
        report = (await session.execute(
            select(ReportSnapshotORM).where(
                ReportSnapshotORM.report_id == report_id,
                ReportSnapshotORM.user_id.in_(list(readable_user_ids or [user_id])),
            )
        )).scalar_one_or_none()
        if report is None:
            raise NotFoundException("报告不存在")
        await self._history.require_owned_task(
            session, task_id=report.task_id, user_id=user_id,
            readable_user_ids=readable_user_ids,
        )
        return report

    async def _owned_generation(self, session, report_task_id, user_id):
        generation = (await session.execute(
            select(ReportGenerationTaskORM).where(
                ReportGenerationTaskORM.id == report_task_id,
                ReportGenerationTaskORM.user_id == user_id,
            )
        )).scalar_one_or_none()
        if generation is None:
            raise NotFoundException("报告生成任务不存在")
        await self._history.require_owned_task(session, task_id=generation.task_id, user_id=user_id)
        return generation

    @staticmethod
    def _step(seq, key, title, state, attempt=None):
        item = {"seq": seq, "key": key, "title": title, "state": state, "at": datetime.now().isoformat()}
        if attempt is not None:
            item["attempt"] = attempt
        return item

    def _complete_step(self, generation, key, title, attempt=None):
        generation.steps = [*generation.steps, self._step(
            len(generation.steps) + 1, key, title, "completed", attempt
        )]

    @staticmethod
    def serialize_task(generation):
        return {
            "reportTaskId": generation.id,
            "taskId": generation.task_id,
            "status": generation.status,
            "steps": generation.steps,
            "currentStep": generation.current_step,
            "reportId": generation.report_id,
            "error": ({"code": generation.error_code, "message": generation.error_message}
                      if generation.status == "failed" else None),
        }
