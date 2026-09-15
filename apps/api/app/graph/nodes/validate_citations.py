"""Mechanical check: does every citation the LLM claimed actually appear
in the chunk set it was given? This is the main anti-hallucination lever
per CLAUDE.md - a citation not present in the retrieved set is stripped
and flagged, never trusted just because the model asserted it.
"""

from __future__ import annotations

from app.graph.state import GraphState


def validate_citations(state: GraphState) -> dict:
    retrieved = state.get("reranked_chunks", [])
    raw_citations = state.get("raw_citations", [])

    retrieved_keys = {(c["doc_id"], c["section_or_article"]) for c in retrieved}

    validated = []
    rejected = []
    for citation in raw_citations:
        key = (citation["doc_id"], citation["section_or_article"])
        if key in retrieved_keys:
            validated.append(citation)
        else:
            rejected.append(citation)

    return {"validated_citations": validated, "rejected_citations": rejected}
