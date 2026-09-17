"""add cases and expert_reviews tables

Adds Case (docs/product/rbac-full-implementation-spec.md Section 6),
superseding EscalationItem - every answered chat turn gets a row, not
just escalated ones. Adds ExpertReview (the review-action history).
escalation_items stays in place, unread by new code (expand->migrate->
contract, spec Section 2's own precedent) - dropped in a later migration.

Revision ID: 33fed748deec
Revises: a18b27770761
Create Date: 2026-09-17 17:27:04.157313

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33fed748deec'
down_revision: Union[str, None] = 'a18b27770761'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    case_risk_level = sa.Enum("low", "medium", "high", name="case_risk_level")
    case_status = sa.Enum(
        "open", "in_progress", "awaiting_user_input", "escalated", "resolved", "closed",
        name="case_status",
    )
    case_queue = sa.Enum("ip", "regulatory", "legal", name="case_queue")
    expert_review_action = sa.Enum(
        "approve", "modify", "reject", "request_info", "escalate", name="expert_review_action"
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("product_classification", sa.String(), nullable=True),
        sa.Column("ip_types", sa.JSON(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("regulatory_issues", sa.JSON(), nullable=True),
        sa.Column("abs_tk_flags", sa.JSON(), nullable=True),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("confidence_level", sa.String(), nullable=True),
        sa.Column("risk_level", case_risk_level, nullable=False),
        sa.Column("status", case_status, nullable=False),
        sa.Column("queue", case_queue, nullable=True),
        sa.Column("assigned_to_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_summary", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cases_status_queue", "cases", ["status", "queue"])
    op.create_index("ix_cases_user_id", "cases", ["user_id"])

    op.create_table(
        "expert_reviews",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_role", sa.String(), nullable=False),
        sa.Column("action", expert_review_action, nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("expert_reviews")
    op.drop_index("ix_cases_user_id", table_name="cases")
    op.drop_index("ix_cases_status_queue", table_name="cases")
    op.drop_table("cases")
    sa.Enum(name="expert_review_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_queue").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_risk_level").drop(op.get_bind(), checkfirst=True)
