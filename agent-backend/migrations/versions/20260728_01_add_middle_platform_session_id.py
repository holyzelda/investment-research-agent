"""Add middle_platform_session_id mapping column to ir_conversation.

Revision ID: 20260728_01
Revises: 20260724_01
Create Date: 2026-07-28

The middle-platform session id is a distinct identity from the local
conversation UUID. It is null until the platform returns it on the
session_start event, then persisted for multi-turn continuation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260728_01"
down_revision: Union[str, None] = "20260724_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ir_conversation")}
    if "middle_platform_session_id" not in columns:
        op.add_column(
            "ir_conversation",
            sa.Column("middle_platform_session_id", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("ir_conversation", "middle_platform_session_id")
