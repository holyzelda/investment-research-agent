"""calculation 持久化 · ORM 模型（ir_agent 库）。

方案A + 快照可脱离飞书：一次测算落 7 类快照，历史展示只依赖 report_snapshot。
表名统一前缀 `ir_`，避免与团队其它库表名冲突。

JSON 列用 SQLAlchemy 通用 `JSON` 类型：MySQL 落 JSON 列、sqlite 落 TEXT，
应用层读写皆为 Python dict/list，跨库一致。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
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


class ConversationORM(Base):
    """会话：UUID 为本应用会话标识；中台 session_id 独立存于映射列。"""

    __tablename__ = "ir_conversation"
    __table_args__ = (
        Index("ix_ir_conv_user_deleted_activity", "user_id", "deleted_at", "last_activity_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="最近活动时间：会话创建/新消息/新测算时更新，用于历史列表排序",
    )
    # 中台会话 id：首轮对话未回传前为空，session_start 事件回写后多轮回填。
    middle_platform_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )


class MessageSnapshotORM(_PkTimestamp, Base):
    """消息快照：会话时间线（可见文本与轻量事件载荷）。"""

    __tablename__ = "ir_message_snapshot"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="text", server_default="text"
    )
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)


class CalculationTaskORM(_PkTimestamp, Base):
    """测算任务：状态机流转 + 版本 + 飞书副本 + request_id/参数hash。"""

    __tablename__ = "ir_calculation_task"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ir_conversation.id"), nullable=False, index=True
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
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class DataSnapshotORM(_PkTimestamp, Base):
    """数据快照：取数中间态（表2开关/两档基准/电价库均价等派生数据）。"""

    __tablename__ = "ir_data_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class FeishuIoSnapshotORM(_PkTimestamp, Base):
    """飞书 I/O 快照：API_INPUT / API_OUTPUT / API_META 全量（排障与校验）。"""

    __tablename__ = "ir_feishu_io_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True, index=True
    )
    api_input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    api_output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    api_meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class SpotStationORM(Base):
    """节点站点维表：预计算任务维护，调整面板按省份读取为节点下拉选项。"""

    __tablename__ = "ir_spot_station"

    province: Mapped[str] = mapped_column(String(64), primary_key=True)
    station_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)


class ConversationSpotContextORM(Base):
    """会话级上传现货电价：仅保存文件摘要与 19 个 K 的聚合结果。"""

    __tablename__ = "ir_conversation_spot_context"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_ir_conv_spot_context_conversation"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("ir_conversation.id"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    context_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="CNY/MWh")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_day_count: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_day_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    k_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class CalculationResultSnapshotORM(_PkTimestamp, Base):
    """测算结果快照：三模块与图表底层数值，历史展示唯一数据源。"""

    __tablename__ = "ir_calculation_result_snapshot"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ReportGenerationTaskORM(_PkTimestamp, Base):
    """报告生成过程：可恢复状态与面向用户的步骤进度，不保存正式报告内容。"""

    __tablename__ = "ir_report_generation_task"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="generating", server_default="generating"
    )
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    current_step: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    report_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ReportSnapshotORM(_PkTimestamp, Base):
    """正式报告快照：仅预留未来成功生成后的完整报告载荷。"""

    __tablename__ = "ir_report_snapshot"
    __table_args__ = (
        Index("ix_ir_report_snapshot_conversation_created_at", "conversation_id", "created_at"),
    )

    report_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False, unique=True
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_conversation.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CalculationShareORM(_PkTimestamp, Base):
    """测算结果分享记录：每个测算版本最多一个有效分享链接。"""

    __tablename__ = "ir_calculation_share"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ir_conversation.id"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ir_calculation_task.id"), nullable=False
    )
    owner_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    share_code_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="分享码 SHA-256 哈希，用于公开查询"
    )
    share_code_ciphertext: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="分享码加密存储，用于管理端回显"
    )
    duration_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, comment="有效期天数：7/14/30"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="过期时间（创建时间 + duration_days）"
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="主动撤销时间"
    )
