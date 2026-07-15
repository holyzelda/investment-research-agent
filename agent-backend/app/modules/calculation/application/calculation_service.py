"""calculation 应用层 · 测算服务（薄片 Mock 主链路）。

编排：assemble（四来源组装）→ 飞书写入 API_INPUT → 飞书读取 API_OUTPUT
     → output_mapper → CalculationResult（结果三模块）。

薄片阶段 FeishuGateway 注入 MockFeishuGateway（回放样例 output），
故不依赖真飞书即可端到端跑通、供前端开发。

Batch3 将扩展为完整执行链路（状态机 created→…→completed、request_id/hash 校验、
智能重试、7 类快照落库），并把 gateway 换成 HttpFeishuGateway；本服务是编排点。
"""
from typing import Optional

from app.modules.calculation.application.output_mapper import map_output_to_result
from app.modules.calculation.application.param_assembler import ParamAssembler
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.domain.ports import FeishuGateway
from app.modules.calculation.domain.result import CalculationResult

# 薄片占位 doc_token；Batch3 由"每次新测算复制新副本"生成
_STUB_DOC_TOKEN = "mock-doc"


class CalculationService:
    def __init__(self, assembler: ParamAssembler, feishu: FeishuGateway):
        self._assembler = assembler
        self._feishu = feishu

    async def run(
        self,
        basics: ProjectBasics,
        *,
        doc_token: str = _STUB_DOC_TOKEN,
        version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> CalculationResult:
        assembled = self._assembler.assemble(basics)
        # 只写入参（readonly/output 不写）——writable_inputs 的口径已由组装器保证
        await self._feishu.write_input(doc_token, assembled.api_input)
        api_output = await self._feishu.read_output(doc_token)
        return map_output_to_result(
            basics, assembled, api_output, version=version, request_id=request_id
        )
