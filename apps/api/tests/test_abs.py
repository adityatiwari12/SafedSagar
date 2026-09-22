"""Tests for the product ABS (Access and Benefit-Sharing) assessment
wizard (Phase 9). Follows tests/test_compliance.py's style: httpx
`client` + `make_user` fixtures, no direct DB seeding except through the
API itself (aside from the audit-log assertion, which reads Postgres
directly since there's no audit-log endpoint to hit)."""

import re

from sqlalchemy import select

from app.abs.rules import derive_preliminary_framework, is_assessment_complete
from app.db.base import AsyncSessionLocal
from app.db.models import AuditLogEntry

# Same no-fabrication regression check as test_compliance.py: a legal
# reference pattern must never appear in a derived framework description
# or next step (CLAUDE.md: "Do not invent real legal citations or
# government records").
_LEGAL_REFERENCE_RE = re.compile(r"\b(section|sec\.|rule|regulation|reg\.|clause|schedule|article)\s*\d", re.IGNORECASE)


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# derive_preliminary_framework - pure unit tests, no I/O.
# ---------------------------------------------------------------------------


def test_unanswered_is_biological_resource_asks_for_it_first():
    framework, next_steps = derive_preliminary_framework({})
    assert "biological resource" in framework.lower()
    assert len(next_steps) == 1
    assert not _LEGAL_REFERENCE_RE.search(framework)


def test_not_a_biological_resource_means_no_framework_applies():
    framework, next_steps = derive_preliminary_framework({"is_biological_resource": False})
    assert "no access and benefit-sharing framework applies" in framework.lower()
    assert next_steps == []
    assert not _LEGAL_REFERENCE_RE.search(framework)


def test_biological_resource_from_india_mentions_domestic_bd_act_and_nba():
    fields = {
        "is_biological_resource": True,
        "origin": "india",
        "sourcing": "wild_collected",
        "purpose": "commercial",
        "user_entity_category": "indian_company",
        "involves_traditional_knowledge": False,
    }
    framework, next_steps = derive_preliminary_framework(fields)
    assert "biological diversity act" in framework.lower()
    assert "nba" in framework.lower()
    assert len(next_steps) >= 1
    assert not _LEGAL_REFERENCE_RE.search(framework)


def test_commercial_purpose_raises_stakes_over_research_only():
    commercial, _ = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "india", "purpose": "commercial"}
    )
    research, _ = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "india", "purpose": "research_only"}
    )
    assert "commercial use raises" in commercial.lower()
    assert "research-only use may" in research.lower()


def test_foreign_entity_vs_indian_individual_get_different_nba_track_language():
    foreign, _ = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "india", "user_entity_category": "foreign_entity"}
    )
    individual, _ = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "india", "user_entity_category": "indian_individual"}
    )
    assert "foreign entity" in foreign.lower()
    assert "prior nba approval is likely to be required" in foreign.lower()
    assert "indian individual" in individual.lower()
    assert "lighter nba intimation-based process" in individual.lower()
    assert foreign != individual


def test_biological_resource_outside_india_says_domestic_act_not_applicable():
    framework, next_steps = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "outside_india"}
    )
    assert "not the applicable lens" in framework.lower()
    assert "cbd" in framework.lower() or "convention on biological diversity" in framework.lower()
    assert "nagoya" in framework.lower()
    assert len(next_steps) >= 1
    assert not _LEGAL_REFERENCE_RE.search(framework)


def test_unknown_origin_says_framework_depends_on_origin():
    framework, _ = derive_preliminary_framework({"is_biological_resource": True, "origin": "unknown"})
    assert "depends on where this biological" in framework.lower()


def test_traditional_knowledge_adds_tkdl_pointer_note_not_live_retrieval_claim():
    framework, next_steps = derive_preliminary_framework(
        {"is_biological_resource": True, "origin": "india", "involves_traditional_knowledge": True}
    )
    assert "tkdl" in framework.lower()
    assert "not independently searchable" in framework.lower()
    assert any("tkdl" in step.lower() for step in next_steps)
    assert not _LEGAL_REFERENCE_RE.search(framework)


def test_missing_fields_are_named_not_guessed():
    framework, _ = derive_preliminary_framework({"is_biological_resource": True, "origin": "india"})
    assert "still need" in framework.lower()
    assert "sourcing" in framework.lower() or "wild-collected" in framework.lower()


def test_no_branch_output_contains_a_legal_reference_pattern():
    """Regression test mirroring test_compliance.py's: every framework
    string this function can produce, across a representative sweep of
    field combinations, must be phrased structurally - never a quote or
    paraphrase of a specific statute/rule/regulation/section number."""
    bio_values = [None, False, True]
    origins = [None, "india", "outside_india", "unknown"]
    purposes = [None, "commercial", "research_only", "unknown"]
    entities = [None, "indian_individual", "indian_company", "foreign_entity", "unknown"]
    tk_values = [None, True, False]

    for is_bio in bio_values:
        for origin in origins:
            for purpose in purposes:
                for entity in entities:
                    for tk in tk_values:
                        fields = {
                            "is_biological_resource": is_bio,
                            "origin": origin,
                            "sourcing": "unknown",
                            "purpose": purpose,
                            "user_entity_category": entity,
                            "involves_traditional_knowledge": tk,
                        }
                        framework, next_steps = derive_preliminary_framework(fields)
                        assert not _LEGAL_REFERENCE_RE.search(framework), (
                            f"framework for fields={fields!r} looks like a legal citation: {framework!r}"
                        )
                        for step in next_steps:
                            assert not _LEGAL_REFERENCE_RE.search(step), (
                                f"next_step for fields={fields!r} looks like a legal citation: {step!r}"
                            )


def test_is_assessment_complete():
    assert is_assessment_complete({}) is False
    assert is_assessment_complete({"is_biological_resource": False}) is True
    assert (
        is_assessment_complete(
            {
                "is_biological_resource": True,
                "origin": "india",
                "sourcing": "wild_collected",
                "purpose": "commercial",
                "user_entity_category": "indian_company",
                "involves_traditional_knowledge": False,
            }
        )
        is True
    )
    assert (
        is_assessment_complete(
            {
                "is_biological_resource": True,
                "origin": "india",
                "sourcing": "unknown",
                "purpose": "commercial",
                "user_entity_category": "indian_company",
                "involves_traditional_knowledge": False,
            }
        )
        is False
    )


# ---------------------------------------------------------------------------
# HTTP-level: get / put / delete-cascade / authz.
# ---------------------------------------------------------------------------


async def test_get_with_no_assessment_returns_default_not_started(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Neem Extract"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.get(f"/products/{product_id}/abs", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "not_started"
    assert body["id"] is None
    assert body["is_biological_resource"] is None
    assert body["product_id"] == product_id


async def test_put_then_get_round_trip(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Ashwagandha Root Extract"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.put(
        f"/products/{product_id}/abs",
        json={
            "is_biological_resource": True,
            "resource_description": "Ashwagandha root, wild-collected in Madhya Pradesh",
            "origin": "india",
            "sourcing": "wild_collected",
            "involves_traditional_knowledge": True,
            "purpose": "commercial",
            "user_entity_category": "indian_company",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] is not None
    assert body["status"] == "complete"
    assert body["origin"] == "india"
    assert "biological diversity act" in body["preliminary_framework"].lower()
    assert body["next_steps"]

    resp = await client.get(f"/products/{product_id}/abs", headers=headers)
    assert resp.status_code == 200, resp.text
    body2 = resp.json()
    assert body2["id"] == body["id"]
    assert body2["resource_description"] == "Ashwagandha root, wild-collected in Madhya Pradesh"
    assert body2["status"] == "complete"


async def test_resave_is_idempotent_shaped_no_second_row(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Herbal Salve"}, headers=headers)
    product_id = resp.json()["id"]

    first = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "india"},
        headers=headers,
    )
    first_id = first.json()["id"]

    second = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "outside_india", "purpose": "research_only"},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["id"] == first_id
    assert second_body["origin"] == "outside_india"

    from app.db.models import AbsAssessment

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AbsAssessment).where(AbsAssessment.product_id == product_id))
        rows = result.scalars().all()
        assert len(rows) == 1


async def test_omitted_fields_on_put_are_treated_as_not_answered(client, make_user):
    """PUT is a full replace, not a partial patch - omitting a
    previously-answered field on a later PUT must null it out, not leave
    the old value in place."""
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Turmeric Cream"}, headers=headers)
    product_id = resp.json()["id"]

    await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "india", "purpose": "commercial"},
        headers=headers,
    )
    resp = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "india"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["purpose"] is None


async def test_invalid_origin_value_is_400(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Bad Input Product"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "mars"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_put_writes_abs_save_audit_row(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Audit Test Product"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": False},
        headers=headers,
    )
    assessment_id = resp.json()["id"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLogEntry).where(AuditLogEntry.action == "abs.save").order_by(AuditLogEntry.created_at.desc())
        )
        audit = result.scalars().first()
        assert audit is not None
        assert audit.detail["product_id"] == product_id
        assert audit.detail["assessment_id"] == assessment_id


async def test_other_users_product_is_403_on_get_and_put(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Private ABS Product"}, headers=headers_a)
    product_id = resp.json()["id"]

    assert (await client.get(f"/products/{product_id}/abs", headers=headers_b)).status_code == 403
    assert (
        await client.put(
            f"/products/{product_id}/abs", json={"is_biological_resource": True}, headers=headers_b
        )
    ).status_code == 403


async def test_delete_product_with_abs_assessment_returns_204(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "To Delete With ABS"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.put(
        f"/products/{product_id}/abs",
        json={"is_biological_resource": True, "origin": "india"},
        headers=headers,
    )
    assert resp.json()["id"] is not None

    resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    resp = await client.get(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 404


async def test_put_with_evidence_only_cites_real_source_documents(client, make_user):
    """Slow - needs a live Ollama embed call + Chroma query. Whatever
    evidence comes back (possibly none, if the corpus has nothing
    relevant), every doc_id in it must be a real source_documents row -
    never hand-filled, same no-fabrication check as compliance's."""
    from app.db.models import SourceDocument

    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={"name": "Wild Ashwagandha Formulation", "jurisdiction": "india"},
        headers=headers,
    )
    product_id = resp.json()["id"]

    resp = await client.put(
        f"/products/{product_id}/abs?with_evidence=true",
        json={
            "is_biological_resource": True,
            "resource_description": "Ashwagandha root",
            "origin": "india",
            "sourcing": "wild_collected",
            "purpose": "commercial",
            "user_entity_category": "indian_company",
            "involves_traditional_knowledge": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    async with AsyncSessionLocal() as session:
        for ev in body["applicable_provisions"] or []:
            result = await session.execute(
                select(SourceDocument).where(
                    SourceDocument.doc_id == ev["doc_id"],
                    SourceDocument.section_or_article == ev["section_or_article"],
                )
            )
            assert result.scalars().first() is not None, f"evidence cites unknown doc: {ev}"
