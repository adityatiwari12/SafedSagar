"""add knowledge graph

Adds kg_nodes / kg_edges - the legal knowledge graph built by
`python -m app.kg.build` from source_documents plus the curated,
provenance-checked domain layer in app/kg/curated_edges.yaml. Every edge
carries source_doc_id (+ optional source_section / source_chunk_id) that
the builder has resolved against source_documents before inserting.
Expand-only migration; nothing else changes.

Revision ID: 81df68522f5c
Revises: 1e68098d2a7e
Create Date: 2026-09-22 02:03:31.140095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81df68522f5c'
down_revision: Union[str, None] = '1e68098d2a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NODE_TYPES = (
    "statute", "rules", "treaty", "provision", "authority", "product_category",
    "ip_type", "concept", "case", "guidance",
)
_RELATIONS = (
    "CONTAINS", "REFERS_TO", "IMPLEMENTS", "AMENDS", "ADMINISTERED_BY",
    "APPLIES_TO", "GOVERNED_BY", "RELATES_TO", "INTERPRETS",
)
_ORIGINS = ("structural", "extracted", "curated")


def upgrade() -> None:
    node_type = sa.Enum(*_NODE_TYPES, name="kg_node_type")
    relation = sa.Enum(*_RELATIONS, name="kg_relation")
    origin = sa.Enum(*_ORIGINS, name="kg_edge_origin")

    op.create_table(
        "kg_nodes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("node_type", node_type, nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("doc_id", sa.String(), nullable=True),
        sa.Column("section_or_article", sa.String(), nullable=True),
        sa.UniqueConstraint("key", name="ux_kg_nodes_key"),
    )
    op.create_index("ix_kg_nodes_doc_section", "kg_nodes", ["doc_id", "section_or_article"])

    op.create_table(
        "kg_edges",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("src_id", sa.Uuid(as_uuid=True), sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dst_id", sa.Uuid(as_uuid=True), sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation", relation, nullable=False),
        sa.Column("source_doc_id", sa.String(), nullable=False),
        sa.Column("source_section", sa.String(), nullable=True),
        sa.Column("source_chunk_id", sa.String(), nullable=True),
        sa.Column("origin", origin, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.UniqueConstraint("src_id", "dst_id", "relation", name="ux_kg_edges_src_dst_rel"),
    )
    op.create_index("ix_kg_edges_src", "kg_edges", ["src_id"])
    op.create_index("ix_kg_edges_dst", "kg_edges", ["dst_id"])


def downgrade() -> None:
    op.drop_index("ix_kg_edges_dst", table_name="kg_edges")
    op.drop_index("ix_kg_edges_src", table_name="kg_edges")
    op.drop_table("kg_edges")
    op.drop_index("ix_kg_nodes_doc_section", table_name="kg_nodes")
    op.drop_table("kg_nodes")
    sa.Enum(name="kg_edge_origin").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="kg_relation").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="kg_node_type").drop(op.get_bind(), checkfirst=True)
