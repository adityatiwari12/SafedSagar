"""Pure applicability rules for the ABS (Access and Benefit-Sharing)
assessment wizard (Phase 9).

Sibling of app.compliance.rules and bound by the same non-negotiable
constraint (CLAUDE.md): this is a compliance aid, not a legal
determination. `derive_preliminary_framework` never asserts a product
*is* compliant, never invents a statute section/rule number, and never
claims live TKDL retrieval (TKDL access is NDA-restricted to ~17 patent
offices - see CLAUDE.md caveat #1). Any `applicable_provisions` citation
is attached separately by app.abs.service.attach_evidence, which resolves
against real `source_documents` rows - this module only produces
structural, plain-language description and next steps.

No I/O, no DB access - pure function over the assessment's answerable
fields. tests/test_abs.py asserts (mirroring test_compliance.py's
regression test) that no branch this function can produce contains a
legal-reference pattern (section/rule/regulation/clause/schedule/article
followed by a number).
"""

from __future__ import annotations

from typing import TypedDict


class AssessmentFields(TypedDict, total=False):
    is_biological_resource: bool | None
    origin: str | None
    sourcing: str | None
    involves_traditional_knowledge: bool | None
    purpose: str | None
    user_entity_category: str | None


_TKDL_NOTE = (
    "This product involves traditional knowledge. TKDL is not independently "
    "searchable here - access is restricted under NDA to a small set of "
    "patent offices worldwide - so this is a pointer, not a search result: "
    "TKDL prior art likely exists for this and the CSIR-TKDL unit should be "
    "contacted directly. Benefit-sharing obligations toward the TK holder(s) "
    "should also be considered alongside whichever ABS framework applies "
    "below."
)


def _is_unanswered(value: object) -> bool:
    return value is None or value == "unknown"


def derive_preliminary_framework(assessment_fields: AssessmentFields) -> tuple[str, list[str]]:
    """Which ABS framework/process likely applies, in structural
    (never legal-citation) language, plus a list of next steps.

    - Not a biological resource -> no ABS framework applies, said plainly.
    - Not yet known whether it's a biological resource -> say that's the
      first thing needed, nothing else can be inferred yet.
    - Biological resource sourced from India -> domestic BD Act / NBA
      pathway is likely relevant; commercial purpose raises the stakes
      over research-only; foreign entity vs Indian individual/company
      changes which NBA approval track is likely relevant (structural
      distinction only - no provision numbers hardcoded here).
    - Biological resource sourced outside India -> international
      frameworks (CBD/Nagoya) are the relevant lens; domestic NBA process
      is explicitly said not to apply the same way, not left silent.
    - Origin not yet known -> say the framework depends on origin, ask
      for it.
    - Traditional knowledge involved -> TKDL/prior-art pointer note is
      appended regardless of which resource framework applies.
    - Any other field left unknown -> named in a closing "still needed"
      note rather than guessed at.
    """
    is_bio = assessment_fields.get("is_biological_resource")
    origin = assessment_fields.get("origin")
    sourcing = assessment_fields.get("sourcing")
    involves_tk = assessment_fields.get("involves_traditional_knowledge")
    purpose = assessment_fields.get("purpose")
    entity = assessment_fields.get("user_entity_category")

    if is_bio is None:
        return (
            "Not enough information yet to determine an ABS framework: "
            "confirm whether this product involves a biological resource "
            "(or a derivative of one) before anything further can be "
            "assessed.",
            ["Answer whether the product involves a biological resource or a derivative of one."],
        )

    if is_bio is False:
        return (
            "This product has not been identified as involving a biological "
            "resource, so no Access and Benefit-Sharing framework applies "
            "based on the information provided.",
            [],
        )

    parts: list[str] = []
    next_steps: list[str] = []

    if origin == "india":
        parts.append(
            "Because this biological resource is sourced from India, the "
            "domestic Biological Diversity Act framework and the National "
            "Biodiversity Authority (NBA) approval pathway are likely "
            "relevant."
        )
        if purpose == "commercial":
            parts.append(
                "Commercial use raises the compliance stakes further than "
                "research-only use and is likely to require a fuller NBA "
                "approval process."
            )
        elif purpose == "research_only":
            parts.append(
                "Research-only use may qualify for a lighter NBA process than "
                "commercial use, though an NBA intimation or approval step can "
                "still apply."
            )
        if entity == "foreign_entity":
            parts.append(
                "As a foreign entity (or an entity with non-Indian "
                "participation), prior NBA approval is likely to be required "
                "before accessing or using the resource - this is a stricter "
                "track than the one available to Indian individuals."
            )
        elif entity == "indian_individual":
            parts.append(
                "As an Indian individual, a lighter NBA intimation-based "
                "process may apply rather than the foreign-entity approval "
                "track, but this still needs confirming case-by-case."
            )
        elif entity == "indian_company":
            parts.append(
                "As an Indian company, an NBA approval or registration step "
                "likely applies, with the exact track depending on factors "
                "such as company size and ownership - not something to guess "
                "at here."
            )
        next_steps.append(
            "Determine which NBA approval/registration track applies, based on entity category and purpose."
        )
        next_steps.append(
            "Prepare to register or file with the State Biodiversity Board / National Biodiversity Authority as applicable."
        )
    elif origin == "outside_india":
        parts.append(
            "Because this biological resource is sourced from outside India, "
            "India's Biological Diversity Act / NBA process is not the "
            "applicable lens here. International frameworks - the Convention "
            "on Biological Diversity and the Nagoya Protocol, together with "
            "the source country's own access-and-benefit-sharing regime - are "
            "the relevant frameworks instead."
        )
        next_steps.append(
            "Identify the source country's own ABS regime and competent national authority, and its consent/permit requirements."
        )
        next_steps.append(
            "Check whether the source country is a Nagoya Protocol party and what its Prior Informed Consent process requires."
        )
    else:
        parts.append(
            "Which framework applies depends on where this biological "
            "resource originates: sourced from India points to the domestic "
            "Biological Diversity Act / NBA pathway, sourced from outside "
            "India points instead to the international CBD/Nagoya lens. "
            "Origin needs to be answered before this can be narrowed down."
        )

    if involves_tk:
        parts.append(_TKDL_NOTE)
        next_steps.append("Contact the CSIR-TKDL unit for a prior-art/TKDL awareness check (TKDL is not independently searchable).")
    elif involves_tk is None:
        pass  # covered by the "still needed" note below.

    missing: list[str] = []
    if _is_unanswered(origin):
        missing.append("origin of the biological resource (India vs outside India)")
    if _is_unanswered(sourcing):
        missing.append("how the resource is sourced (wild-collected vs cultivated)")
    if _is_unanswered(purpose):
        missing.append("intended purpose (commercial vs research-only)")
    if _is_unanswered(entity):
        missing.append("the user's entity category (Indian individual, Indian company, or foreign entity)")
    if involves_tk is None:
        missing.append("whether traditional knowledge is involved")

    if missing:
        parts.append("This is a preliminary read only - to give a more confident answer, still need: " + "; ".join(missing) + ".")

    return " ".join(parts), next_steps


def is_assessment_complete(assessment_fields: AssessmentFields) -> bool:
    """True once every answerable field has a definite (non-null,
    non-"unknown") answer, or once `is_biological_resource` is False
    (a definitive "no ABS framework applies" answer needs nothing else).
    Used by app.abs.service to set the wizard's own `status` column -
    kept here, next to the logic it mirrors, rather than duplicated in
    the service layer.
    """
    is_bio = assessment_fields.get("is_biological_resource")
    if is_bio is None:
        return False
    if is_bio is False:
        return True
    return (
        not _is_unanswered(assessment_fields.get("origin"))
        and not _is_unanswered(assessment_fields.get("sourcing"))
        and not _is_unanswered(assessment_fields.get("purpose"))
        and not _is_unanswered(assessment_fields.get("user_entity_category"))
        and assessment_fields.get("involves_traditional_knowledge") is not None
    )
