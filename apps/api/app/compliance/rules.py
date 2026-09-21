"""Pure applicability rules for the compliance checklist (Phase 10).

CLAUDE.md's non-negotiable constraint for this module: "Do not invent real
legal citations or government records." Which checklist *areas* apply to a
product is structural category logic derived from its
`product_classification` - not a legal claim - so it is fine to hardcode
here. What must NEVER appear in this file is a statute name, section
number, rule number, regulation number, or authority-specific legal
requirement text. Every `applicability_reason` below is phrased as a
structural reason ("applies because this product is classified as ..."),
never as a quote or paraphrase of a law. tests/test_compliance.py asserts
this mechanically via a legal-reference regex over every reason this
function can produce, for every value in PRODUCT_CATEGORIES.

No I/O, no DB access - pure function over `product_classification`.
"""

from __future__ import annotations

from app.db.models import ComplianceArea

# The four drug-licensing categories among app.graph.state.PRODUCT_CATEGORIES.
DRUG_CATEGORIES = frozenset(
    {
        "classical_or_generic_medicine",
        "patent_or_proprietary_medicine",
        "new_or_non_classical_drug",
        "phytopharmaceutical",
    }
)

# Always-applicable areas, regardless of classification (as long as the
# question is in scope at all - see the out_of_scope short-circuit below).
_ALWAYS_APPLICABLE: tuple[ComplianceArea, ...] = (
    ComplianceArea.classification,
    ComplianceArea.ingredients,
    ComplianceArea.labelling,
    ComplianceArea.claims,
    ComplianceArea.advertising,
)

_ALWAYS_APPLICABLE_REASONS: dict[ComplianceArea, str] = {
    ComplianceArea.ingredients: (
        "Applies because every formulation's ingredient composition needs to "
        "be documented and reviewed, regardless of category."
    ),
    ComplianceArea.labelling: (
        "Applies because every product intended for sale needs its labelling "
        "reviewed, regardless of category."
    ),
    ComplianceArea.claims: (
        "Applies because every product's stated claims need review, "
        "regardless of category."
    ),
    ComplianceArea.advertising: (
        "Applies because every product's advertising and promotional "
        "material needs review, regardless of category."
    ),
}


def _classification_reason(product_classification: str | None) -> str:
    if product_classification is None or product_classification == "unclear":
        return (
            "This product has not been classified yet; classification needs "
            "to be completed before the rest of this checklist can be "
            "finalized."
        )
    return (
        f"Applies to every product; records this product's classification "
        f"as {product_classification}."
    )


def applicable_areas(product_classification: str | None) -> list[tuple[ComplianceArea, str]]:
    """Which checklist areas apply to a product, with a structural
    (never legal) reason for each.

    - `out_of_scope` -> no checklist at all (the question wasn't about an
      Ayurveda IP/regulatory product in the first place).
    - `None`/`unclear` -> only the always-applicable set; the
      `classification` item's reason says the product needs classifying
      first.
    - The four drug categories add manufacturing/safety_evidence/licensing.
    - `ayurveda_aahara_or_nutraceutical` adds manufacturing/food_requirements.
    - `cosmetic` adds manufacturing/cosmetic_requirements.
    """
    if product_classification == "out_of_scope":
        return []

    areas: list[tuple[ComplianceArea, str]] = [
        (ComplianceArea.classification, _classification_reason(product_classification))
    ]
    areas.extend(
        (area, _ALWAYS_APPLICABLE_REASONS[area]) for area in _ALWAYS_APPLICABLE if area != ComplianceArea.classification
    )

    if product_classification in DRUG_CATEGORIES:
        areas.append(
            (
                ComplianceArea.manufacturing,
                f"Applies because this product is classified as a drug category "
                f"({product_classification}), which involves manufacturing "
                f"process requirements.",
            )
        )
        areas.append(
            (
                ComplianceArea.safety_evidence,
                f"Applies because this product is classified as a drug category "
                f"({product_classification}), which requires safety evidence "
                f"to be assembled and reviewed.",
            )
        )
        areas.append(
            (
                ComplianceArea.licensing,
                f"Applies because this product is classified as a drug category "
                f"({product_classification}), which requires licensing to be "
                f"tracked and reviewed.",
            )
        )
    elif product_classification == "ayurveda_aahara_or_nutraceutical":
        areas.append(
            (
                ComplianceArea.manufacturing,
                "Applies because this product is classified as a food/"
                "nutraceutical, which involves manufacturing process "
                "requirements.",
            )
        )
        areas.append(
            (
                ComplianceArea.food_requirements,
                "Applies because this product is classified as a food/"
                "nutraceutical (ayurveda_aahara_or_nutraceutical).",
            )
        )
    elif product_classification == "cosmetic":
        areas.append(
            (
                ComplianceArea.manufacturing,
                "Applies because this product is classified as a cosmetic, "
                "which involves manufacturing process requirements.",
            )
        )
        areas.append(
            (
                ComplianceArea.cosmetic_requirements,
                "Applies because this product is classified as a cosmetic.",
            )
        )

    return areas
