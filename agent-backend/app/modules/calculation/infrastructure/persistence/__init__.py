"""calculation 基础设施 · 持久化（ORM/DAO）。

7 类快照 + 会话/消息/任务，落 MySQL 库 ir_agent。
导入 orm 即把模型注册进 Base.metadata；建表 DDL 由 ORM 生成（见 sql/ir_agent_schema.sql）。
"""
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationTaskORM,
    ConversationORM,
    DataSnapshotORM,
    FeishuIoSnapshotORM,
    InputSnapshotORM,
    MessageSnapshotORM,
    ReportGenerationTaskORM,
    ReportSnapshotORM,
)

__all__ = [
    "ConversationORM",
    "MessageSnapshotORM",
    "CalculationTaskORM",
    "CalculationResultSnapshotORM",
    "InputSnapshotORM",
    "DataSnapshotORM",
    "FeishuIoSnapshotORM",
    "ReportGenerationTaskORM",
    "ReportSnapshotORM",
]
