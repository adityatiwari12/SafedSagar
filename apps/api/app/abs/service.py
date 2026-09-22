"""ABS assessment persistence and evidence attachment (Phase 9).

`save_assessment` is the only place an AbsAssessment row gets created,
and - like app.compliance.service.generate_checklist - it is an upsert:
one row per product, redone in place rather than duplicated, so a
re-saved wizard step never spawns a second row.

`attach_evidence` reuses the app's existing retrieve/rerank nodes (same
functions app.compliance.service.attach_evidence and the chat pipeline
use) rather than a second retrieval path, and verifies every chunk
against `source_documents` before trusting it - a fabricated
doc_id/section_or_article must never reach `applicable_provisions`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abs.rules import AssessmentFields, derive_preliminary_framework, is_assessment_complete
from app.db.models import AbsAssessment, AbsAssessmentStatus, Product, SourceDocument, User
from app.graph.nodes.rerank import rerank
from app.graph.nodes.retrieve import retrieve
from app.graph.state import GraphState

# How many top reranked chunks to keep as evidence.
_EVIDENCE_TOP_K = 3

_ANSWERABLE_FIELDS = (
    "is_biological_resource",
    "resource_description",
    "origin",
    "sourcing",
    "involves_traditional_knowledge",
    "purpose",
    "user_entity_category",
)


def _enum_value(value: object) -> str | None:
    """`row.origin` etc. may be a plain str (just assigned in-memory,
    not yet round-tripped through the DB) or an Enum instance (loaded
    from a prior flush/refresh) - normalize either to its plain string
    value for app.abs.rules, which only knows about strings."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else value


def _fields_for_rules(row: AbsAssessment) -> AssessmentFields:
    return AssessmentFields(
        is_biological_resource=row.is_biological_resource,
        origin=_enum_value(row.origin),
        sourcing=_enum_value(row.sourcing),
        involves_traditional_knowledge=row.involves_traditional_knowledge,
        purpose=_enum_value(row.purpose),
        user_entity_category=_enum_value(row.user_entity_category),
    )


async def save_assessment(
    db: AsyncSession, product: Product, payload: dict, actor: User
) -> AbsAssessment:
    """Full-replace upsert of `product`'s one ABS assessment row. `payload`
    is expected to already carry every answerable field (missing keys
    default to None, i.e. not-yet-answered) - this is a wizard step-save,
    not a partial patch, mirroring the PUT semantics the router enforces.
    """
    result = await db.execute(select(AbsAssessment).where(AbsAssessment.product_id == product.id))
    row = result.scalars().first()
    if row is None:
        row = AbsAssessment(product_id=product.id)
        db.add(row)

    for field in _ANSWERABLE_FIELDS:
        setattr(row, field, payload.get(field))

    framework, next_steps = derive_preliminary_framework(_fields_for_rules(row))
    row.preliminary_framework = framework
    row.next_steps = next_steps
    row.status = (
        AbsAssessmentStatus.complete
        if is_assessment_complete(_fields_for_rules(row))
        else (AbsAssessmentStatus.not_started if row.is_biological_resource is None else AbsAssessmentStatus.in_progress)
    )
    row.updated_by_user_id = actor.id

    await db.flush()
    return row


def _build_retrieval_query(row: AbsAssessment, product: Product) -> str:
    parts = ["access and benefit sharing biological diversity", product.name]
    if row.resource_description:
        parts.append(row.resource_description)
    if row.origin is not None:
        parts.append(_enum_value(row.origin).replace("_", " "))
    if row.sourcing is not None:
        parts.append(_enum_value(row.sourcing).replace("_", " "))
    if row.purpose is not None:
        parts.append(_enum_value(row.purpose).replace("_", " "))
    if row.involves_traditional_knowledge:
        parts.append("traditional knowledge")
    return " - ".join(part for part in parts if part)


async def attach_evidence(db: AsyncSession, assessment: AbsAssessment, product: Product) -> None:
    """Run the real retrieval pipeline for `assessment`'s entered
    resource/TK/ABS terms and store the top reranked chunks as
    `applicable_provisions`, enriched with `authority` from
    `source_documents`. Only chunks that verify against that table are
    kept - if nothing verifies, `applicable_provisions` is set to an
    empty list, never filled in by hand.
    """
    query = _build_retrieval_query(assessment, product)
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

    assessment.applicable_provisions = verified_evidence
