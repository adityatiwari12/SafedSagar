"""Prior-art / literature search for the Researcher persona.

Reuses the existing hybrid retrieve+rerank pipeline directly
(app.graph.nodes.retrieve/rerank), skipping classify_product/reason_and_cite
entirely - this is a search, not a question-answering call, so it doesn't
need an LLM round trip. That also makes it fast and independent of the
generation model being up.

This is corpus-grounded search over the already-ingested legal/case-law
corpus, framed honestly as "prior-art signals from this corpus" - NOT a
live external patent/publication database. CLAUDE.md marks paid-source
connectors and live external search integrations as explicitly out of
scope for MVP (Phase 4); see also caveat #1 (TKDL is pointer-only, never
live retrieval) - the same "don't imply a live external search we don't
have" principle applies here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, require_permission
from app.db.models import SourceDocument
from app.graph.nodes.rerank import rerank
from app.graph.nodes.retrieve import retrieve
from app.research.schemas import PriorArtResult

router = APIRouter(prefix="/research", tags=["research"])

_SNIPPET_CHARS = 400


@router.get("/prior-art", response_model=list[PriorArtResult])
async def search_prior_art(
    q: str = Query(..., min_length=3, max_length=500),
    jurisdiction: str | None = Query(None),
    _ctx: AuthzContext = Depends(require_permission(Permission.RESEARCH_SEARCH_PRIOR_ART)),
    db: AsyncSession = Depends(get_db),
) -> list[PriorArtResult]:
    state = {"retrieval_query": q, "jurisdiction": jurisdiction, "doc_type": None}
    retrieved = await retrieve(state)
    reranked = rerank({**state, **retrieved})
    chunks = reranked["reranked_chunks"]
    if not chunks:
        return []

    # retrieve/rerank's RetrievedChunk carries only citable fields (no
    # authority/jurisdiction) - re-hydrate the full row for those, same
    # pattern retrieve.py itself uses to hydrate vector-search hits.
    ids = [c["id"] for c in chunks]
    result = await db.execute(select(SourceDocument).where(SourceDocument.id.in_(ids)))
    rows_by_id = {row.id: row for row in result.scalars().all()}

    out: list[PriorArtResult] = []
    for chunk in chunks:
        row = rows_by_id.get(chunk["id"])
        if row is None:
            continue
        out.append(
            PriorArtResult(
                doc_id=row.doc_id,
                title=row.title,
                authority=row.authority,
                jurisdiction=row.jurisdiction.value,
                doc_type=row.doc_type,
                section_or_article=row.section_or_article,
                source_url=row.source_url or "",
                snippet=row.source_text[:_SNIPPET_CHARS],
            )
        )
    return out
