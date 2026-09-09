"""Create conversation-scoped uploaded spot price context.

Revision ID: 20260908_01
Revises: 20260813_01
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260908_01"
down_revision: Union[str, None] = "20260813_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ir_conversation_spot_context",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ready"),
        sa.Column("context_token_hash", sa.String(64), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("price_unit", sa.String(16), nullable=False, server_default="CNY/MWh"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("valid_day_count", sa.Integer(), nullable=False),
        sa.Column("skipped_day_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("k_results", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ir_conversation.id"]),
        sa.UniqueConstraint("conversation_id", name="uq_ir_conv_spot_context_conversation"),
        sa.UniqueConstraint("context_token_hash", name="uq_ir_conv_spot_context_token"),
    )
    op.create_index(
        "ix_ir_conv_spot_context_user", "ir_conversation_spot_context", ["user_id"]
    )
    op.create_index(
        "ix_ir_conv_spot_context_expires", "ir_conversation_spot_context", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_ir_conv_spot_context_expires", table_name="ir_conversation_spot_context")
    op.drop_index("ix_ir_conv_spot_context_user", table_name="ir_conversation_spot_context")
    op.drop_table("ir_conversation_spot_context")
