"""add case messages

Adds case_messages - the back-and-forth thread between a Case's own user
and its assigned reviewer (Phase 23's expert-escalation loop: ... expert
assigned -> review -> additional information if required -> expert
response -> user notification -> closure). Expand-only; nothing else
changes.

Revision ID: 5c64bc93a0f2
Revises: 81df68522f5c
Create Date: 2026-09-22 22:32:20.171608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c64bc93a0f2'
down_revision: Union[str, None] = '81df68522f5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    case_message_kind = sa.Enum(
        "note", "info_request", "info_response", "expert_response", name="case_message_kind"
    )

    op.create_table(
        "case_messages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("author_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_role", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("kind", case_message_kind, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_case_messages_case_id", "case_messages", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_case_messages_case_id", table_name="case_messages")
    op.drop_table("case_messages")
    sa.Enum(name="case_message_kind").drop(op.get_bind(), checkfirst=True)
