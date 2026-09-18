"""add products table

Adds Product (docs/product/rbac-full-implementation-spec.md Section 6,
Phase 3) - the ownership+org-scoped product/formulation dossier. Expand-
only migration; nothing else changes.

Revision ID: 2e559aead469
Revises: 33fed748deec
Create Date: 2026-09-18 12:49:00.995167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e559aead469'
down_revision: Union[str, None] = '33fed748deec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("product_classification", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("intended_use", sa.String(), nullable=True),
        sa.Column("claims", sa.String(), nullable=True),
        sa.Column("manufacturing_info", sa.String(), nullable=True),
        sa.Column("target_market", sa.String(), nullable=True),
        sa.Column("development_stage", sa.String(), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=True),
        sa.Column("biological_resources", sa.JSON(), nullable=True),
        sa.Column("ip_status", sa.JSON(), nullable=True),
        sa.Column("regulatory_status", sa.JSON(), nullable=True),
        sa.Column("abs_tk_status", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_products_owner_user_id", "products", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_products_owner_user_id", table_name="products")
    op.drop_table("products")
