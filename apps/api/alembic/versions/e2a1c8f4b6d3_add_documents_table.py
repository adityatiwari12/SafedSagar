"""add documents table

Adds Document (Phase 28) - secure document storage, the foundation the
label/advertisement analyser (Phase 11) and the researcher workspace
build on next. Bytes live on local disk (app.documents.storage); this
table is the metadata/ownership record only. Expand-only migration;
nothing else changes.

Revision ID: e2a1c8f4b6d3
Revises: 92676ca2c889
Create Date: 2026-09-22 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a1c8f4b6d3'
down_revision: Union[str, None] = '92676ca2c889'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    document_kind = sa.Enum(
        "label", "certificate", "formulation_sheet", "correspondence", "other", name="document_kind"
    )
    document_status = sa.Enum("active", "deleted", name="document_status")

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("product_id", sa.Uuid(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("case_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False, unique=True),
        sa.Column("doc_kind", document_kind, nullable=False),
        sa.Column("status", document_status, nullable=False, server_default="active"),
        sa.Column("uploaded_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    op.create_index("ix_documents_product_id", "documents", ["product_id"])
    op.create_index("ix_documents_case_id", "documents", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_index("ix_documents_product_id", table_name="documents")
    op.drop_index("ix_documents_owner_user_id", table_name="documents")
    op.drop_table("documents")
    sa.Enum(name="document_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="document_kind").drop(op.get_bind(), checkfirst=True)
