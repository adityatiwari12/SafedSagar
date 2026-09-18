"""add case product_id

Wires Case to Product (deferred at Case-creation time in
33fed748deec because `products` didn't exist yet - it does now, per
2e559aead469). Nullable FK + index; expand-only, nothing else changes.

Revision ID: 17c0535837b2
Revises: 2e559aead469
Create Date: 2026-09-18 13:08:48.140089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17c0535837b2'
down_revision: Union[str, None] = '2e559aead469'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("product_id", sa.Uuid(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
    )
    op.create_index("ix_cases_product_id", "cases", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_cases_product_id", table_name="cases")
    op.drop_column("cases", "product_id")
