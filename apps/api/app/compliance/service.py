"""Compliance-checklist generation and evidence attachment (Phase 10).

`generate_checklist` is the only place a ComplianceItem row gets created,
and it is deliberately idempotent/non-destructive: re-running it must never
clobber a status/notes/evidence a user has already set, and reclassifying a
product marks a no-longer-applicable item `not_applicable` rather than
deleting it, so the item's history survives.

`attach_evidence` reuses the app's existing retrieve/rerank nodes (the same
functions the chat pipeline uses for citations) rather than a second
retrieval path, and verifies every chunk against `source_documents` before
trusting it - the same mechanical check `validate_citations` does for chat
answers, applied here so a checklist item never shows a fabricated
doc_id/section_or_article.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.rules import applicable_areas
from app.db.models import ComplianceArea, ComplianceItem, ComplianceStatus, Product, SourceDocument, User
from app.graph.nodes.rerank import rerank
from app.graph.nodes.retrieve import retrieve
from app.graph.state import GraphState

_NOT_APPLICABLE_REASON = "No longer applicable to this product's current classification."

# How many top reranked chunks to keep as evidence per item.
_EVIDENCE_TOP_K = 3


async def generate_checklist(db: AsyncSession, product: Product, actor: User) -> list[ComplianceItem]:
    """Create any missing checklist items for `product` and mark any item
    that's no longer applicable (after a reclassification) as
    `not_applicable`. Never touches an existing item's status, notes, or
    evidence otherwise - `actor` is accepted for interface symmetry with
    `attach_evidence`/the router's audit call, not used to mutate rows here
    (audit logging is the router's responsibility, not this service's).
    """
    pairs = applicable_areas(product.product_classification)
    reason_by_area: dict[ComplianceArea, str] = dict(pairs)

    result = await db.execute(select(ComplianceItem).where(ComplianceItem.product_id == product.id))
    existing_by_area = {item.area: item for item in result.scalars().all()}

    for area, reason in pairs:
        if area not in existing_by_area:
            item = ComplianceItem(product_id=product.id, area=area, applicability_reason=reason)
            db.add(item)
            existing_by_area[area] = item

    for area, item in existing_by_area.items():
        if area not in reason_by_area and item.status != ComplianceStatus.not_applicable:
            item.status = ComplianceStatus.not_applicable
            item.applicability_reason = _NOT_APPLICABLE_REASON

    await db.flush()

    result = await db.execute(
        select(ComplianceItem).where(ComplianceItem.product_id == product.id).order_by(ComplianceItem.area)
    )
    return list(result.scalars().all())


def _build_retrieval_query(area: ComplianceArea, product: Product) -> str:
    parts = [area.value.replace("_", " "), product.name]
    if product.product_classification:
        parts.append(product.product_classification.replace("_", " "))
    if product.intended_use:
        parts.append(product.intended_use)
    if product.claims:
        parts.append(product.claims)
    return " - ".join(part for part in parts if part)


async def attach_evidence(db: AsyncSession, item: ComplianceItem, product: Product) -> None:
    """Run the real retrieval pipeline for `item`'s area and store the top
    reranked chunks as evidence, enriched with `authority` from
    `source_documents`. Only chunks that verify against that table are
    kept - if nothing verifies (or retrieval returns nothing relevant),
    `item.evidence` is set to an empty list, never filled in by hand.
    """
    query = _build_retrieval_query(item.area, product)
    state: GraphState = {
        "retrieval_query": query,
        "jurisdiction": product.jurisdiction,
        "doc_type": None,
    }
    state.update(await retrieve(state))
    state.update(rerank(state))
    reranked_chunks = state.get("reranked_chunks", [])[:_EVIDENCE_TOP_K]

    verified_evidence: list[dict] = []
    for chunk in reranked_chunks:
        row = await db.get(SourceDocument, chunk["id"])
        if row is None:
            continue
        # Mirror validate_citations' mechanical check: trust the
        # (doc_id, section_or_article) pair only because it actually
        # matches the source_documents row, not just because retrieve/
        # rerank said so.
        if row.doc_id != chunk["doc_id"] or row.section_or_article != chunk["section_or_article"]:
            continue
        verified_evidence.append(
            {
                "doc_id": row.doc_id,
                "section_or_article": row.section_or_article,
                "title": row.title,
                "authority": row.authority,
                "source_url": row.source_url,
            }
        )

    item.evidence = verified_evidence
