"""calculation 基础设施 · 飞书客户端（Mock 实现）。

方案A：系统只读写接口区 API_INPUT/API_OUTPUT/API_META。
异步端口的内存 Mock：记录写入、回放预置结果，read_meta 默认立即 done 且回写 request_id
（薄片主链路与引擎 happy path 均可用；需要模拟 computing/串号的场景在测试里用专门的 double）。
Batch3 将新增 HttpFeishuGateway 实现同一 FeishuGateway 端口，接真实飞书 API。
"""
from typing import Optional

from app.modules.calculation.domain.ports import FeishuGateway


class MockFeishuGateway(FeishuGateway):
    """内存 Mock：记录写入、回放预置结果。"""

    def __init__(self, output: dict | None = None):
        self.written: dict[str, dict] = {}   # doc_token -> API_INPUT payload
        self.meta: dict[str, dict] = {}       # doc_token -> API_META
        self._output = output or {}
        self._copy_seq = 0
        self.last_copy_name: Optional[str] = None

    async def copy_template(self, name: Optional[str] = None) -> str:
        self._copy_seq += 1
        self.last_copy_name = name
        return f"mock-doc-{self._copy_seq}"

    async def write_input(self, doc_token: str, payload: dict) -> None:
        self.written[doc_token] = dict(payload)

    async def write_meta(self, doc_token: str, meta: dict) -> None:
        self.meta[doc_token] = dict(meta)

    async def read_meta(self, doc_token: str) -> dict:
        # 立即完成，并回写与写入一致的 request_id（防串号校验通过）
        written = self.meta.get(doc_token, {})
        return {"status": "done", "request_id": written.get("request_id")}

    async def read_output(self, doc_token: str) -> dict:
        return dict(self._output)

    def last_payload(self) -> dict | None:
        if not self.written:
            return None
        return next(reversed(self.written.values()))
