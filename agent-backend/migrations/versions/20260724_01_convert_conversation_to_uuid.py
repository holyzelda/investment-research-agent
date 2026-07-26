"""Convert conversation identity to UUID strings.

Revision ID: 20260724_01
Revises: 20260715_01
Create Date: 2026-07-24

This migration intentionally clears existing calculation/report conversation data.
The UUID conversation contract supersedes the earlier numeric-ID contract and
this project does not retain legacy conversation records for this rollout.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260724_01"
down_revision: Union[str, None] = "20260715_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONVERSATION_CHILDREN = (
    "ir_message_snapshot",
    "ir_calculation_task",
    "ir_report_generation_task",
    "ir_report_snapshot",
)


def _drop_conversation_foreign_keys(bind) -> None:
    inspector = sa.inspect(bind)
    for table_name in _CONVERSATION_CHILDREN:
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") == "ir_conversation":
                op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def _drop_middle_platform_mapping(bind) -> None:
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ir_conversation")}
    if "middle_platform_session_id" not in columns:
        return
    for index in inspector.get_indexes("ir_conversation"):
        if "middle_platform_session_id" in index["column_names"]:
            op.drop_index(index["name"], table_name="ir_conversation")
    op.drop_column("ir_conversation", "middle_platform_session_id")


def upgrade() -> None:
    bind = op.get_bind()

    # This is a deliberate destructive cutover. Remove all records whose
    # relationship relies on the retired numeric conversation identifier.
    for table_name in (
        "ir_data_snapshot",
        "ir_feishu_io_snapshot",
        "ir_input_snapshot",
        "ir_calculation_result_snapshot",
        "ir_report_snapshot",
        "ir_report_generation_task",
        "ir_message_snapshot",
        "ir_calculation_task",
        "ir_conversation",
    ):
        op.execute(sa.text(f"DELETE FROM {table_name}"))

    _drop_conversation_foreign_keys(bind)
    _drop_middle_platform_mapping(bind)

    op.alter_column(
        "ir_conversation",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.String(length=36),
        existing_autoincrement=True,
        autoincrement=False,
    )
    for table_name in _CONVERSATION_CHILDREN:
        op.alter_column(
            table_name,
            "conversation_id",
            existing_type=sa.BigInteger(),
            type_=sa.String(length=36),
        )
        op.create_foreign_key(
            f"fk_{table_name}_conversation_id",
            table_name,
            "ir_conversation",
            ["conversation_id"],
            ["id"],
        )


def downgrade() -> None:
    raise RuntimeError("UUID conversation migration is destructive and cannot be downgraded")
