"""Derives a Case's risk_level/status/queue from the graph's existing
output - no new AI call. escalate_if_needed (app/graph/nodes/
escalate_if_needed.py) already decides WHETHER a case needs a human;
this module decides HOW risky and WHICH queue, reusing that decision
rather than re-deriving it from confidence alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models import CaseQueue, CaseRiskLevel, CaseStatus

# spec Section 8: case.queue = legal only reachable when risk_level==high
# AND an ambiguous/complex/ABS-sensitive/sensitive-TK signal is present -
# never just because a case is high-risk for an ordinary reason (e.g. low
# confidence on a routine trademark question stays in the ip queue).
_LEGAL_TRIGGER_IP_TYPES = frozenset({"access_and_benefit_sharing"})


@dataclass(frozen=True)
class CaseOutcome:
    risk_level: CaseRiskLevel
    status: CaseStatus
    queue: CaseQueue | None


def derive_case_outcome(
    *,
    escalate: bool,
    confidence_level: str,
    product_classification: str | None,
    ip_types: list[str],
    abs_tk_flags: dict | None,
) -> CaseOutcome:
    if not escalate:
        risk = CaseRiskLevel.medium if confidence_level == "medium" else CaseRiskLevel.low
        return CaseOutcome(risk_level=risk, status=CaseStatus.resolved, queue=None)

    risk = CaseRiskLevel.high if confidence_level == "low" else CaseRiskLevel.medium

    is_ambiguous_or_sensitive = (
        product_classification == "unclear"
        or bool(_LEGAL_TRIGGER_IP_TYPES & set(ip_types))
        or bool(
            abs_tk_flags
            and (abs_tk_flags.get("biological_resource_likely") or abs_tk_flags.get("traditional_knowledge_likely"))
        )
    )
    if is_ambiguous_or_sensitive:
        queue = CaseQueue.legal
    elif "drug_regulatory" in ip_types:
        queue = CaseQueue.regulatory
    else:
        queue = CaseQueue.ip

    return CaseOutcome(risk_level=risk, status=CaseStatus.escalated, queue=queue)
