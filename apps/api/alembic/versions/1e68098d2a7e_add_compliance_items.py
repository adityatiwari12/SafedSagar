"""add compliance items

Adds ComplianceItem (Phase 10) - a product's regulatory-compliance
checklist. Which areas apply to a product is derived structurally from its
product_classification (app.compliance.rules), never hardcoded as a legal
claim; status defaults to `unknown` and evidence is only ever populated by
running the existing retrieve/rerank pipeline over source_documents.
Expand-only migration; nothing else changes.

Revision ID: 1e68098d2a7e
Revises: 17c0535837b2
Create Date: 2026-09-22 01:14:13.959407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e68098d2a7e'
down_revision: Union[str, None] = '17c0535837b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    compliance_area = sa.Enum(
        "classification",
        "manufacturing",
        "ingredients",
        "safety_evidence",
        "labelling",
        "claims",
        "advertising",
        "licensing",
        "food_requirements",
        "cosmetic_requirements",
        name="compliance_area",
    )
    compliance_status = sa.Enum(
        "unknown", "action_required", "under_review", "complete", "not_applicable",
        name="compliance_status",
    )

    op.create_table(
        "compliance_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", sa.Uuid(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("area", compliance_area, nullable=False),
        sa.Column("status", compliance_status, nullable=False, server_default="unknown"),
        sa.Column("applicability_reason", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_compliance_items_product_id", "compliance_items", ["product_id"])
    op.create_unique_constraint(
        "ux_compliance_item_product_area", "compliance_items", ["product_id", "area"]
    )


def downgrade() -> None:
    op.drop_constraint("ux_compliance_item_product_area", "compliance_items", type_="unique")
    op.drop_index("ix_compliance_items_product_id", table_name="compliance_items")
    op.drop_table("compliance_items")
    sa.Enum(name="compliance_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="compliance_area").drop(op.get_bind(), checkfirst=True)
