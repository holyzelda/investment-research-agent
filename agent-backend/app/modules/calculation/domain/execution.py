"""calculation 领域 · 测算执行状态机与错误分类（无框架、无 I/O）。

状态机（PRD §1.3.2）：
    created → copying → writing → computing → reading → validating → snapshotting → completed
异常分支：failed / timeout。

错误分两类（3.3 智能重试据此决策）：
- RetryableCalcError：网络超时、飞书 5xx、限流 429、等算超时、request_id 不匹配 —— 复用同副本重试。
- NonRetryableCalcError：鉴权 401/403、副本模板缺失、接口区结构损坏、参数校验非法 —— 直接失败不重试。
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


class CalcStatus(str, Enum):
    CREATED = "created"
    COPYING = "copying"
    WRITING = "writing"
    COMPUTING = "computing"
    READING = "reading"
    VALIDATING = "validating"
    SNAPSHOTTING = "snapshotting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CalcError(Exception):
    """测算执行错误基类，携带机器可读 code / request_id / doc_token。

    doc_token：出错时已复制的副本标识；重试策略据此复用同一副本（不再复制）。
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        request_id: Optional[str] = None,
        doc_token: Optional[str] = None,
        retry_count: int = 0,
    ):
        super().__init__(message)
        self.code = code
        self.request_id = request_id
        self.doc_token = doc_token
        self.retry_count = retry_count


class RetryableCalcError(CalcError):
    """可重试：复用同副本从头重试（最多 N 次）。"""


class NonRetryableCalcError(CalcError):
    """不可重试：直接失败，提示对应原因。"""
