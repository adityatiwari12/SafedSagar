from app.cases.service import derive_case_outcome
from app.db.models import CaseQueue, CaseRiskLevel, CaseStatus


def test_low_confidence_escalates_to_ip_queue_high_risk():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="low", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.high
    assert outcome.status == CaseStatus.escalated
    assert outcome.queue == CaseQueue.ip


def test_unclear_classification_routes_to_legal_queue():
    """spec Section 8: legal queue only reachable when risk_level==high AND
    an ambiguous/ABS-sensitive/sensitive-TK signal is present - unclear
    classification is the ambiguous-signal case."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="low", product_classification="unclear",
        ip_types=[], abs_tk_flags=None,
    )
    assert outcome.queue == CaseQueue.legal


def test_abs_flag_routes_to_legal_queue():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="cosmetic",
        ip_types=["access_and_benefit_sharing"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.queue == CaseQueue.legal


def test_drug_regulatory_routes_to_regulatory_queue_when_escalated():
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="ayurveda_aahara_or_nutraceutical",
        ip_types=["drug_regulatory"], abs_tk_flags=None,
    )
    assert outcome.queue == CaseQueue.regulatory


def test_non_escalated_case_is_auto_resolved_with_no_queue():
    outcome = derive_case_outcome(
        escalate=False, confidence_level="high", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.low
    assert outcome.status == CaseStatus.resolved
    assert outcome.queue is None


def test_non_escalated_medium_confidence_is_medium_risk_resolved():
    outcome = derive_case_outcome(
        escalate=False, confidence_level="medium", product_classification="cosmetic",
        ip_types=[], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.status == CaseStatus.resolved
    assert outcome.queue is None
