"""Create ir_calculation_share table for calculation result sharing.

Revision ID: 20260813_01
Revises: 20260811_01
Create Date: 2026-08-13

Adds:
- ir_calculation_share table with share_code_hash, share_code_ciphertext, duration_days, expires_at, revoked_at
- Indexes on owner_user_id and conversation_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260813_01"
down_revision: Union[str, None] = "20260811_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ir_calculation_share",
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_user_id", sa.String(64), nullable=False),
        sa.Column("share_code_hash", sa.String(64), nullable=False,
                  comment="分享码 SHA-256 哈希，用于公开查询"),
        sa.Column("share_code_ciphertext", sa.String(256), nullable=False,
                  comment="分享码加密存储，用于管理端回显"),
        sa.Column("duration_days", sa.SmallInteger(), nullable=False, server_default=sa.text("7"),
                  comment="有效期天数：7/14/30"),
        sa.Column("expires_at", sa.DateTime(), nullable=False,
                  comment="过期时间（创建时间 + duration_days）"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True,
                  comment="主动撤销时间"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_code_hash", name="uq_ir_calculation_share_hash"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ir_conversation.id"],),
        sa.ForeignKeyConstraint(["task_id"], ["ir_calculation_task.id"],),
    )
    op.create_index(
        "ix_ir_calculation_share_owner", "ir_calculation_share", ["owner_user_id"],
    )
    op.create_index(
        "ix_ir_calculation_share_conv", "ir_calculation_share", ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ir_calculation_share_conv", table_name="ir_calculation_share")
    op.drop_index("ix_ir_calculation_share_owner", table_name="ir_calculation_share")
    op.drop_table("ir_calculation_share")