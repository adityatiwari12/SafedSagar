from app.cases.service import derive_case_outcome
from app.db.models import CaseQueue, CaseRiskLevel, CaseStatus


def test_low_confidence_escalates_to_legal_queue_high_risk():
    """spec Section 8's OR: risk_level==high is independently sufficient for
    legal queue, even with no explicit ambiguous/sensitive signal."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="low", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.high
    assert outcome.status == CaseStatus.open
    assert outcome.queue == CaseQueue.legal


def test_unclear_classification_routes_to_legal_queue():
    """spec Section 8's OR: an ambiguous/ABS-sensitive/sensitive-TK signal
    is independently sufficient for legal queue, regardless of risk level."""
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


def test_none_ip_types_does_not_raise_and_falls_back_to_no_signal():
    """ip_types can be None (key present, value null) rather than an empty
    list - must not raise, and should behave as if no ip_type signal was
    present."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="cosmetic",
        ip_types=None, abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.status == CaseStatus.open
    assert outcome.queue == CaseQueue.ip


def test_non_dict_abs_tk_flags_does_not_raise_and_falls_back_to_no_signal():
    """abs_tk_flags could theoretically be a non-dict truthy value - must
    be treated the same as None (no signal) rather than raising
    AttributeError on .get()."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags="not a dict",
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.status == CaseStatus.open
    assert outcome.queue == CaseQueue.ip


def test_medium_risk_alone_with_no_signal_routes_to_ip_queue():
    """spec Section 8's OR: medium risk alone (without high risk or a
    signal) does NOT route to legal — only high risk or a signal does."""
    outcome = derive_case_outcome(
        escalate=True, confidence_level="medium", product_classification="cosmetic",
        ip_types=["trademark"], abs_tk_flags=None,
    )
    assert outcome.risk_level == CaseRiskLevel.medium
    assert outcome.status == CaseStatus.open
    assert outcome.queue == CaseQueue.ip
