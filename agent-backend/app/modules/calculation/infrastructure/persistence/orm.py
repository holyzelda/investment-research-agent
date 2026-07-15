"""calculation 持久化 · ORM 模型（ir_agent 库）。

方案A + 快照可脱离飞书：一次测算落 7 类快照，历史展示只依赖 report_snapshot。
表名统一前缀 `ir_`，避免与团队其它库表名冲突。

JSON 列用 SQLAlchemy 通用 `JSON` 类型：MySQL 落 JSON 列、sqlite 落 TEXT，
应用层读写皆为 Python dict/list，跨库一致。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base

# 自增主键类型：MySQL 用 BIGINT；sqlite 只有 INTEGER PRIMARY KEY 才自增，故加 variant。
_PK = BigInteger().with_variant(Integer, "sqlite")


class _PkTimestamp:
    """自增主键 + 创建时间（快照只增不改，无需 updated_at）。"""

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ConversationORM(_PkTimestamp, Base):
    """会话：归属字段 user_id/username 来自平台注入 header（不做登录校验）。"""

    __tablename__ = "ir_conversation"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class MessageSnapshotORM(_PkTimestamp, Base):
    """消息快照：会话回放（user/assistant 角色 + 文本内容）。"""

    __tablename__ = "ir_message_snapshot"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)


class CalculationTaskORM(_PkTimestamp, Base):
    """测算任务：状态机流转 + 版本 + 飞书副本 + request_id/参数hash。"""

    __tablename__ = "ir_calculation_task"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(16), nullable=False)  # V1/V2/V3…
    # created→copying→writing→computing→reading→validating→snapshotting→completed / failed / timeout
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="created")
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    param_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    feishu_copy_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class InputSnapshotORM(_PkTimestamp, Base):
    """入参快照：本次冻结入参（组装后 assembled.api_input 等）。"""

    __tablename__ = "ir_input_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class DataSnapshotORM(_PkTimestamp, Base):
    """数据快照：取数中间态（表2开关/两档基准/电价库均价等派生数据）。"""

    __tablename__ = "ir_data_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class FeishuIoSnapshotORM(_PkTimestamp, Base):
    """飞书 I/O 快照：API_INPUT / API_OUTPUT / API_META 全量（排障与校验）。"""

    __tablename__ = "ir_feishu_io_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, index=True
    )
    api_input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    api_output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    api_meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ReportSnapshotORM(_PkTimestamp, Base):
    """报告快照：结果三模块 + 图表底层数值（环形/折线），历史展示唯一数据源。"""

    __tablename__ = "ir_report_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
