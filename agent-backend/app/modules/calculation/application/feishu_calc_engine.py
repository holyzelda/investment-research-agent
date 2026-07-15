"""calculation 应用层 · 测算执行引擎（状态机 + 轮询 + 校验）。

职责（PRD US-1.4 / §1.3.2）：在一个**已给定的飞书副本**上跑一次测算——
    writing → computing → reading → validating → snapshotting → completed

- 副本归属在外层：copy/复用由重试策略负责（见 retry_policy），引擎只接收 doc_token 执行。
  这样任何中途异常都不会丢失副本句柄（doc_token 始终由重试循环持有），从根上杜绝副本泄漏。
- 写入：API_INPUT（全部入参）+ API_META（request_id/参数hash/模板版本）。
- 等算判定：轮询 API_META，仅当 status=done 且回写 request_id 一致才读 API_OUTPUT（防串号/旧值）。
- 校验：request_id 与参数hash 双校验；不一致按可重试处理（带 doc_token 供复用），不读/不采信 output。
- 快照：SNAPSHOTTING 阶段调用可选 snapshot_hook（本层不关心持久化细节）。

错误按 domain.execution 的 Retryable/NonRetryable 抛出，交由重试策略决策。
本引擎不做重试自身——重试是外层策略的职责，保持单一职责、可测。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from app.modules.calculation.domain.execution import (
    CalcStatus,
    RetryableCalcError,
)
from app.modules.calculation.domain.ports import FeishuGateway


@dataclass
class EngineContext:
    """快照钩子入参：引擎已知的本次测算 I/O 上下文。"""
    doc_token: str
    request_id: str
    param_hash: str
    api_input: dict
    api_output: dict
    meta: dict


@dataclass
class EngineResult:
    status: CalcStatus
    doc_token: str
    request_id: str
    api_output: dict
    meta: dict
    transitions: list = field(default_factory=list)


SnapshotHook = Callable[[EngineContext], Awaitable[None]]


class FeishuCalcEngine:
    def __init__(
        self,
        gateway: FeishuGateway,
        *,
        poll_interval: float = 3.0,
        poll_timeout: float = 10.0,
        snapshot_hook: Optional[SnapshotHook] = None,
    ):
        self._gateway = gateway
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout
        self._snapshot_hook = snapshot_hook

    async def run(
        self,
        *,
        api_input: dict,
        request_id: str,
        param_hash: str,
        doc_token: str,
        template_version: Optional[str] = None,
    ) -> EngineResult:
        # doc_token 由重试策略提供（新副本或复用副本）；引擎不复制、不持有副本生命周期。
        transitions = []

        # writing：API_INPUT + API_META
        await self._gateway.write_input(doc_token, api_input)
        await self._gateway.write_meta(doc_token, {
            "request_id": request_id,
            "param_hash": param_hash,
            "template_version": template_version,
        })
        transitions.append(CalcStatus.WRITING)

        # computing：轮询等算完成
        meta = await self._poll_until_done(doc_token, request_id)
        transitions.append(CalcStatus.COMPUTING)

        # 防串号：回写 request_id 必须一致，否则不读 output，按可重试处理
        if meta.get("request_id") != request_id:
            raise RetryableCalcError(
                "API_META 回写 request_id 与本次不一致（疑似串号/旧值）",
                code="request_id_mismatch",
                request_id=request_id,
                doc_token=doc_token,
            )

        # reading
        api_output = await self._gateway.read_output(doc_token)
        transitions.append(CalcStatus.READING)

        # validating：参数hash 一致性（META 带 hash 时校验，读到旧值则可重试）
        meta_hash = meta.get("param_hash")
        if meta_hash is not None and meta_hash != param_hash:
            raise RetryableCalcError(
                "参数hash 校验不通过（读到非本次产出）",
                code="param_hash_mismatch",
                request_id=request_id,
                doc_token=doc_token,
            )
        transitions.append(CalcStatus.VALIDATING)

        # snapshotting：落库钩子（3.4 注入；未注入则空过）
        if self._snapshot_hook is not None:
            await self._snapshot_hook(EngineContext(
                doc_token=doc_token,
                request_id=request_id,
                param_hash=param_hash,
                api_input=api_input,
                api_output=api_output,
                meta=meta,
            ))
        transitions.append(CalcStatus.SNAPSHOTTING)

        transitions.append(CalcStatus.COMPLETED)
        return EngineResult(
            status=CalcStatus.COMPLETED,
            doc_token=doc_token,
            request_id=request_id,
            api_output=api_output,
            meta=meta,
            transitions=transitions,
        )

    async def _poll_until_done(self, doc_token: str, request_id: str) -> dict:
        """按间隔轮询 API_META 直到 status=done；超总时长抛可重试（等算超时）。"""
        loop = asyncio.get_event_loop()
        start = loop.time()
        while True:
            meta = await self._gateway.read_meta(doc_token)
            if meta.get("status") == "done":
                return meta
            if loop.time() - start >= self._poll_timeout:
                raise RetryableCalcError(
                    "等算超时（轮询未在总超时内变为 done）",
                    code="compute_timeout",
                    request_id=request_id,
                    doc_token=doc_token,
                )
            await asyncio.sleep(self._poll_interval)
