"""calculation 模块 · interface 结果序列化（DTO → 前端 camelCase JSON）。

映射逻辑在 application/result_view.py（与 report_snapshot 落库共用一份），
interface 层仅做转发，保持 domain/result.py 无框架依赖。
"""
from app.modules.calculation.application.result_view import to_report_payload
from app.modules.calculation.domain.result import CalculationResult


def serialize_result(r: CalculationResult) -> dict:
    return to_report_payload(r)
