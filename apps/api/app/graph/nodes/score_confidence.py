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
        # sourced one. Previously a flat 0.2 regardless of retrieval depth,
        # which forced escalate_if_needed to bounce EVERY uncited answer to
        # a human - including ones where the corpus actually had decent
        # (3+ chunk) coverage of the topic and the model just couldn't
        # cleanly cite it. Deliberate, bounded widening: scaled by coverage
        # so it can now just reach MEDIUM_THRESHOLD (0.4) at 3+ retrieved
        # chunks - skipping forced escalation for a "corpus has real
        # coverage, answer just wasn't cleanly cited" case - while thin
        # coverage (0-2 chunks) still stays low and still escalates. This
        # never manufactures a citation or a fact; it only changes whether
        # a hedged, uncited-but-grounded-in-real-chunks answer is shown
        # directly versus always routed to a human first.
        score = 0.1 + 0.3 * min(retrieved_count / 3, 1.0)
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
