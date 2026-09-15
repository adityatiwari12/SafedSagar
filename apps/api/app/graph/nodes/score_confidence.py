"""Deterministic confidence scoring from mechanical signals only - no LLM
call, so it can't itself hallucinate. Feeds escalate_if_needed and FR-07's
confidence indicator."""

from __future__ import annotations

from app.graph.state import GraphState

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


def score_confidence(state: GraphState) -> dict:
    retrieved_count = len(state.get("reranked_chunks", []))
    validated = state.get("validated_citations", [])
    rejected = state.get("rejected_citations", [])
    total_claimed = len(validated) + len(rejected)

    if retrieved_count == 0:
        score = 0.0
    elif total_claimed == 0:
        # Nothing was retrieved-and-cited: the model gave an uncited
        # answer (or the "no relevant sources" fallback) rather than a
        # sourced one. Not zero (chunks did exist) but clearly weaker
        # than a fully-cited answer.
        score = 0.2
    else:
        validity_ratio = len(validated) / total_claimed
        coverage = min(retrieved_count / 3, 1.0)  # a couple of good chunks is already decent coverage
        score = 0.7 * validity_ratio + 0.3 * coverage

    if score >= HIGH_THRESHOLD:
        level = "high"
    elif score >= MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    return {"confidence_score": round(score, 2), "confidence_level": level}
