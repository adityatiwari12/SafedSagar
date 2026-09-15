"""Decide whether to flag this answer for human IP-facilitator escalation
(FR-11) - safe abstention over a confident-sounding guess (CLAUDE.md
caveat #3, PRD Non-Goals). This node only decides; Phase 6 wires the
decision into the actual EscalationItem queue once conversations are
persisted."""

from __future__ import annotations

from app.graph.state import GraphState


def escalate_if_needed(state: GraphState) -> dict:
    confidence_level = state.get("confidence_level", "low")
    validated_citations = state.get("validated_citations", [])
    product_classification = state.get("product_classification")

    if confidence_level == "low":
        return {
            "escalate": True,
            "escalation_reason": "Low confidence: insufficient validated "
            "sources for this question. A human IP facilitator should review.",
        }

    if not validated_citations:
        return {
            "escalate": True,
            "escalation_reason": "No citations could be validated against "
            "the retrieved sources.",
        }

    if product_classification == "unclear":
        return {
            "escalate": True,
            "escalation_reason": "The product/formulation could not be "
            "classified from the question - guidance may not apply.",
        }

    return {"escalate": False, "escalation_reason": None}
