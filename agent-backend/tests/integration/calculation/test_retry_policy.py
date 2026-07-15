"""智能重试策略 · 关键节点测试。

只测有决策价值的分支：
1. 可重试恢复且复用同副本——即使异常不带 doc_token（原始 httpx 网络抖动）也复用，不重复复制。
   （这是 #1 修复的核心：副本归属在重试层，doc_token 不依赖异常带回。）
2. 复制副本本身失败（可重试）→ 下轮重新复制，不复用不存在的副本。
3. 超过重试上限：一直可重试 → 终态失败(max_retries_exceeded)带 request_id，共尝试 1+max 次。
4. 不可重试错误：立即失败、不重试。
5. classify_error：httpx 原始异常正确归类（429/5xx→可重试，401/403/404→不可重试）。
"""
import httpx
import pytest

from app.modules.calculation.application.feishu_calc_engine import EngineResult
from app.modules.calculation.application.retry_policy import RetryPolicy, classify_error
from app.modules.calculation.domain.execution import (
    CalcStatus,
    NonRetryableCalcError,
    RetryableCalcError,
)

RID = "req-retry-001"


def _result(doc_token="doc-1"):
    return EngineResult(CalcStatus.COMPLETED, doc_token, RID, {"ok": 1}, {}, [])


@pytest.mark.asyncio
async def test_retryable_reuses_copy_even_when_error_carries_no_token():
    """网络抖动（原始 httpx 异常、不带 doc_token）时仍复用同一副本、不重复复制。"""
    copies = []
    seen_tokens = []

    async def copy_template():
        token = f"doc-{len(copies) + 1}"
        copies.append(token)
        return token

    async def attempt(doc_token):
        seen_tokens.append(doc_token)
        if len(seen_tokens) < 3:  # 前两次抖动失败：原始网络异常，不带 doc_token
            raise httpx.ReadTimeout("network jitter")
        return _result(doc_token)

    result = await RetryPolicy(max_retries=3).run_with_retry(
        attempt, request_id=RID, copy_template=copy_template
    )
    assert result.status is CalcStatus.COMPLETED
    assert copies == ["doc-1"]                          # 只复制一次
    assert seen_tokens == ["doc-1", "doc-1", "doc-1"]   # 三次都复用同一副本


@pytest.mark.asyncio
async def test_copy_failure_is_retried_without_reusing_nonexistent_copy():
    """复制副本本身失败（可重试）→ 下轮重新复制，不复用空副本。"""
    copy_calls = 0
    seen_tokens = []

    async def copy_template():
        nonlocal copy_calls
        copy_calls += 1
        if copy_calls == 1:
            raise httpx.ConnectError("copy failed")  # 首次复制失败
        return "doc-2"

    async def attempt(doc_token):
        seen_tokens.append(doc_token)
        return _result(doc_token)

    result = await RetryPolicy(max_retries=3).run_with_retry(
        attempt, request_id=RID, copy_template=copy_template
    )
    assert result.status is CalcStatus.COMPLETED
    assert copy_calls == 2            # 首次失败、第二次成功
    assert seen_tokens == ["doc-2"]   # 仅在成功复制后执行一次，未复用空副本


@pytest.mark.asyncio
async def test_exceeds_max_retries_fails_terminally():
    calls = 0

    async def copy_template():
        return "doc-x"

    async def always_retryable(doc_token):
        nonlocal calls
        calls += 1
        raise RetryableCalcError("飞书 503", code="feishu_503", request_id=RID, doc_token="doc-x")

    with pytest.raises(NonRetryableCalcError) as ei:
        await RetryPolicy(max_retries=3).run_with_retry(
            always_retryable, request_id=RID, copy_template=copy_template
        )
    assert ei.value.code == "max_retries_exceeded"
    assert ei.value.request_id == RID
    assert calls == 4  # 1 次初始 + 3 次重试


@pytest.mark.asyncio
async def test_non_retryable_fails_immediately():
    calls = 0

    async def copy_template():
        return "doc-1"

    async def auth_failed(doc_token):
        nonlocal calls
        calls += 1
        raise NonRetryableCalcError("鉴权失败", code="feishu_auth_401", request_id=RID)

    with pytest.raises(NonRetryableCalcError) as ei:
        await RetryPolicy(max_retries=3).run_with_retry(
            auth_failed, request_id=RID, copy_template=copy_template
        )
    assert ei.value.code == "feishu_auth_401"
    assert calls == 1  # 不重试


def _http_status_error(status: int) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://feishu/x")
    resp = httpx.Response(status, request=req)
    return httpx.HTTPStatusError(f"{status}", request=req, response=resp)


@pytest.mark.parametrize("exc,retryable", [
    (httpx.ConnectTimeout("t"), True),
    (httpx.ReadError("e"), True),
    (_http_status_error(429), True),
    (_http_status_error(503), True),
    (_http_status_error(401), False),
    (_http_status_error(403), False),
    (_http_status_error(404), False),
])
def test_classify_raw_httpx_errors(exc, retryable):
    err = classify_error(exc, request_id=RID)
    assert isinstance(err, RetryableCalcError) is retryable
