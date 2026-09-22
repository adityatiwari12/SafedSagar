"""add abs assessments

Adds AbsAssessment (Phase 9) - a product's Access and Benefit-Sharing
questionnaire. One row per product (unique FK), upserted in place rather
than duplicated on re-save. `preliminary_framework`/`next_steps` are
system-derived by app.abs.rules from the answerable fields, never a
hardcoded legal claim; `applicable_provisions` is only ever populated by
app.abs.service.attach_evidence running the existing retrieve/rerank
pipeline over source_documents, same shape/rule as ComplianceItem.evidence.
Expand-only migration; nothing else changes.

Revision ID: 92676ca2c889
Revises: 5c64bc93a0f2
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92676ca2c889'
down_revision: Union[str, None] = '5c64bc93a0f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    abs_resource_origin = sa.Enum("india", "outside_india", "unknown", name="abs_resource_origin")
    abs_resource_sourcing = sa.Enum("wild_collected", "cultivated", "both", "unknown", name="abs_resource_sourcing")
    abs_resource_purpose = sa.Enum("commercial", "research_only", "unknown", name="abs_resource_purpose")
    abs_entity_category = sa.Enum(
        "indian_individual", "indian_company", "foreign_entity", "unknown", name="abs_entity_category"
    )
    abs_assessment_status = sa.Enum("not_started", "in_progress", "complete", name="abs_assessment_status")

    op.create_table(
        "abs_assessments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", sa.Uuid(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("is_biological_resource", sa.Boolean(), nullable=True),
        sa.Column("resource_description", sa.String(), nullable=True),
        sa.Column("origin", abs_resource_origin, nullable=True),
        sa.Column("sourcing", abs_resource_sourcing, nullable=True),
        sa.Column("involves_traditional_knowledge", sa.Boolean(), nullable=True),
        sa.Column("purpose", abs_resource_purpose, nullable=True),
        sa.Column("user_entity_category", abs_entity_category, nullable=True),
        sa.Column("preliminary_framework", sa.String(), nullable=True),
        sa.Column("applicable_provisions", sa.JSON(), nullable=True),
        sa.Column("next_steps", sa.JSON(), nullable=True),
        sa.Column("status", abs_assessment_status, nullable=False, server_default="not_started"),
        sa.Column("updated_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # product_id is unique=True + index=True on the model - one unique
    # index covers both (Postgres backs a unique constraint with an
    # index automatically), so only one is created here.
    op.create_unique_constraint("ux_abs_assessments_product_id", "abs_assessments", ["product_id"])


def downgrade() -> None:
    op.drop_constraint("ux_abs_assessments_product_id", "abs_assessments", type_="unique")
    op.drop_table("abs_assessments")
    sa.Enum(name="abs_assessment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="abs_entity_category").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="abs_resource_purpose").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="abs_resource_sourcing").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="abs_resource_origin").drop(op.get_bind(), checkfirst=True)
