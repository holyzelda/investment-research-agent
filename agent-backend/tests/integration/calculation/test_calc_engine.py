"""测算状态机引擎 · 关键链路测试（mock 网关，不落库）。

只测有防护价值的关键节点：
1. happy path：computing→done、request_id 匹配 → 状态机走到 completed 且读到 output。
2. 防串号：request_id 不匹配 → 抛可重试（带 doc_token 供复用），且**不读** output。
3. 等算超时：一直 computing → 抛可重试（compute_timeout）。
4. 副本归属在外层：引擎只在给定 doc_token 上执行，自身**从不复制**副本。
"""
import pytest

from app.modules.calculation.application.feishu_calc_engine import FeishuCalcEngine
from app.modules.calculation.domain.execution import CalcStatus, RetryableCalcError
from app.modules.calculation.domain.ports import FeishuGateway

RID = "req-happy-001"
OUTPUT = {"project_irr": 8.5, "first_year_total_revenue": 8600}
DOC = "fake-doc-1"


class FakeGateway(FeishuGateway):
    """可编程网关：read_meta 按序列返回（最后一项重复），记录调用便于断言。"""

    def __init__(self, meta_sequence: list[dict], output: dict | None = None):
        self._meta_seq = list(meta_sequence)
        self._output = output or {}
        self.copy_calls = 0
        self.input_writes: list[tuple[str, dict]] = []
        self.meta_writes: list[tuple[str, dict]] = []
        self.read_output_calls = 0

    async def copy_template(self, name=None) -> str:
        self.copy_calls += 1
        return f"fake-doc-{self.copy_calls}"

    async def write_input(self, doc_token, payload):
        self.input_writes.append((doc_token, dict(payload)))

    async def write_meta(self, doc_token, meta):
        self.meta_writes.append((doc_token, dict(meta)))

    async def read_meta(self, doc_token):
        return self._meta_seq.pop(0) if len(self._meta_seq) > 1 else self._meta_seq[0]

    async def read_output(self, doc_token):
        self.read_output_calls += 1
        return dict(self._output)


def _engine(gw, **kw):
    return FeishuCalcEngine(gw, poll_interval=0.001, poll_timeout=0.05, **kw)


@pytest.mark.asyncio
async def test_happy_path_runs_state_machine_to_completed():
    gw = FakeGateway([{"status": "computing"}, {"status": "done", "request_id": RID}], OUTPUT)
    result = await _engine(gw).run(
        api_input={"province": "甘肃"}, request_id=RID, param_hash="h1", doc_token=DOC
    )

    assert result.status is CalcStatus.COMPLETED
    assert result.doc_token == DOC
    assert result.api_output["project_irr"] == 8.5
    assert result.transitions == [
        CalcStatus.WRITING, CalcStatus.COMPUTING,
        CalcStatus.READING, CalcStatus.VALIDATING, CalcStatus.SNAPSHOTTING, CalcStatus.COMPLETED,
    ]
    # 引擎从不复制副本（副本归属在重试层），只在给定副本上写入
    assert gw.copy_calls == 0
    assert gw.meta_writes[0][0] == DOC
    assert gw.meta_writes[0][1]["request_id"] == RID


@pytest.mark.asyncio
async def test_request_id_mismatch_is_retryable_and_output_not_read():
    gw = FakeGateway([{"status": "done", "request_id": "OTHER"}], OUTPUT)
    with pytest.raises(RetryableCalcError) as ei:
        await _engine(gw).run(api_input={}, request_id=RID, param_hash="h1", doc_token=DOC)
    assert ei.value.code == "request_id_mismatch"
    assert ei.value.doc_token == DOC   # 带回副本供复用
    assert gw.read_output_calls == 0   # 不匹配绝不读 output


@pytest.mark.asyncio
async def test_compute_timeout_is_retryable():
    gw = FakeGateway([{"status": "computing"}], OUTPUT)  # 永远 computing
    with pytest.raises(RetryableCalcError) as ei:
        await _engine(gw).run(api_input={}, request_id=RID, param_hash="h1", doc_token=DOC)
    assert ei.value.code == "compute_timeout"
    assert ei.value.doc_token == DOC   # 带回副本供复用
