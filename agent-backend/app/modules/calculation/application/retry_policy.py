"""calculation 应用层 · 智能重试策略（可重试 vs 不可重试）。

分类（PRD US-1.4）：
- 可重试：网络超时、飞书 5xx、限流 429、等算超时、request_id/hash 不匹配
    → 复用同副本从头重试，最多 max_retries 次；超限标记 failed，提示"多次重试失败，请联系管理员"并带 request_id。
- 不可重试：鉴权 401/403、副本模板不存在(404)、接口区结构损坏、参数校验非法
    → 直接失败不重试，提示对应原因。

引擎抛出的 Retryable/NonRetryableCalcError 直接采信；真实飞书网关抛出的 httpx 原始异常由
classify_error 归类。重试是外层控制流，引擎自身不重试（单一职责）。
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

import httpx

from app.modules.calculation.application.feishu_calc_engine import EngineResult
from app.modules.calculation.domain.execution import (
    CalcError,
    NonRetryableCalcError,
    RetryableCalcError,
)

# run_attempt(doc_token)：在给定副本上跑一次引擎执行
RunAttempt = Callable[[Optional[str]], Awaitable[EngineResult]]
# copy_template()：复制一个新副本，返回 doc_token
CopyTemplate = Callable[[], Awaitable[str]]


def classify_error(
    exc: Exception, *, request_id: Optional[str] = None, doc_token: Optional[str] = None
) -> CalcError:
    """把任意异常归类为 Retryable / NonRetryableCalcError。已是 CalcError 则原样返回。"""
    if isinstance(exc, CalcError):
        return exc

    # 网络超时/连接抖动 → 可重试
    if isinstance(exc, httpx.TimeoutException):
        return RetryableCalcError(
            f"网络超时：{exc}", code="network_timeout", request_id=request_id, doc_token=doc_token
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429 or 500 <= status < 600:  # 限流 / 飞书 5xx → 可重试
            return RetryableCalcError(
                f"飞书返回 {status}", code=f"feishu_{status}",
                request_id=request_id, doc_token=doc_token,
            )
        if status in (401, 403):  # 鉴权失败 → 不可重试
            return NonRetryableCalcError(
                "飞书鉴权失败，请联系管理员", code=f"feishu_auth_{status}",
                request_id=request_id, doc_token=doc_token,
            )
        if status == 404:  # 副本/模板不存在 → 不可重试
            return NonRetryableCalcError(
                "飞书副本模板不存在，请联系管理员", code="feishu_template_missing",
                request_id=request_id, doc_token=doc_token,
            )
        return NonRetryableCalcError(
            f"飞书返回 {status}", code=f"feishu_{status}",
            request_id=request_id, doc_token=doc_token,
        )
    if isinstance(exc, httpx.TransportError):  # 连接失败等传输层错误 → 可重试
        return RetryableCalcError(
            f"网络异常：{exc}", code="network_error", request_id=request_id, doc_token=doc_token
        )

    # 未知错误：不盲目重试
    return NonRetryableCalcError(
        f"未知错误：{exc}", code="unknown", request_id=request_id, doc_token=doc_token
    )


class RetryPolicy:
    def __init__(self, max_retries: int = 3):
        self._max = max_retries

    async def run_with_retry(
        self, run_attempt: RunAttempt, *, request_id: str, copy_template: CopyTemplate
    ) -> EngineResult:
        """执行一次测算并按分类智能重试；副本归属在本层，复用同副本；超限抛终态失败。

        副本生命周期由本循环持有（不在引擎里）：
        - doc_token 为空 → 先复制新副本再执行；复制自身失败则本轮异常，doc_token 仍为空，下轮重新复制。
        - 副本已存在 → 后续每次重试都复用它（不再复制），从根上避免中途异常导致的副本泄漏。
        """
        doc_token: Optional[str] = None
        retries = 0
        while True:
            try:
                if doc_token is None:
                    doc_token = await copy_template()
                return await run_attempt(doc_token)
            except Exception as raw:  # noqa: BLE001
                err = classify_error(raw, request_id=request_id, doc_token=doc_token)
                if isinstance(err, NonRetryableCalcError):
                    raise err from raw
                # 可重试：钉住副本以复用（引擎抛出的错误可能带更精确的 doc_token）
                if err.doc_token:
                    doc_token = err.doc_token
                retries += 1
                if retries > self._max:
                    raise NonRetryableCalcError(
                        "多次重试失败，请联系管理员",
                        code="max_retries_exceeded",
                        request_id=request_id,
                        doc_token=doc_token,
                    ) from raw
