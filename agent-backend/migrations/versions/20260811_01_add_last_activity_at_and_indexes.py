"""Add last_activity_at, composite indexes for conversation history list.

Revision ID: 20260811_01
Revises: 20260728_01
Create Date: 2026-08-11

Adds:
- last_activity_at column to ir_conversation (for cursor-based pagination)
- Composite index ix_ir_conv_user_deleted_activity on ir_conversation (user_id, deleted_at, last_activity_at)
- Composite index ix_ir_msg_conv_created on ir_message_snapshot (conversation_id, created_at)
- Composite index ix_ir_task_conv_created_id on ir_calculation_task (conversation_id, created_at, id)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260811_01"
down_revision: Union[str, None] = "20260728_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ir_conversation")}

    # 1. Add last_activity_at column (nullable, backfilled by code)
    if "last_activity_at" not in columns:
        op.add_column(
            "ir_conversation",
            sa.Column("last_activity_at", sa.DateTime(), nullable=True,
                      comment="最近活动时间：会话创建/新消息/新测算时更新，用于历史列表排序"),
        )

    # 2. Composite index for list_active query: WHERE user_id=? AND deleted_at IS NULL
    #    ORDER BY last_activity_at DESC, id DESC LIMIT ?
    op.create_index(
        "ix_ir_conv_user_deleted_activity",
        "ir_conversation",
        ["user_id", "deleted_at", "last_activity_at"],
    )

    # 3. Composite index for MAX(created_at) GROUP BY conversation_id
    existing_msg_indexes = {idx["name"] for idx in inspector.get_indexes("ir_message_snapshot")}
    if "ix_ir_msg_conv_created" not in existing_msg_indexes:
        op.create_index(
            "ix_ir_msg_conv_created",
            "ir_message_snapshot",
            ["conversation_id", "created_at"],
        )

    # 4. Composite index for ORDER BY created_at DESC, id DESC WHERE conversation_id=? LIMIT 1
    existing_task_indexes = {idx["name"] for idx in inspector.get_indexes("ir_calculation_task")}
    if "ix_ir_task_conv_created_id" not in existing_task_indexes:
        op.create_index(
            "ix_ir_task_conv_created_id",
            "ir_calculation_task",
            ["conversation_id", "created_at", "id"],
        )


def downgrade() -> None:
    op.drop_index("ix_ir_task_conv_created_id", table_name="ir_calculation_task")
    op.drop_index("ix_ir_msg_conv_created", table_name="ir_message_snapshot")
    op.drop_index("ix_ir_conv_user_deleted_activity", table_name="ir_conversation")
    op.drop_column("ir_conversation", "last_activity_at")