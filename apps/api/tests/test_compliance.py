"""Tests for the product compliance checklist (Phase 10).

Follows tests/test_products.py's style: httpx `client` + `make_user`
fixtures, no direct DB seeding except through the API itself (aside from
the audit-log assertion, which reads Postgres directly since there's no
audit-log endpoint to hit)."""

import re

from sqlalchemy import select

from app.compliance.rules import applicable_areas
from app.db.models import AuditLogEntry, ComplianceArea
from app.db.base import AsyncSessionLocal
from app.graph.state import PRODUCT_CATEGORIES

# Same pattern tests/test_compliance.py's regression test enforces against
# app.compliance.rules output: a legal-reference pattern must never appear
# in an applicability_reason (CLAUDE.md: "Do not invent real legal
# citations or government records").
_LEGAL_REFERENCE_RE = re.compile(r"\b(section|sec\.|rule|regulation|reg\.|clause|schedule|article)\s*\d", re.IGNORECASE)


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# applicable_areas - pure unit tests, no I/O.
# ---------------------------------------------------------------------------


def test_applicable_areas_drug_category_adds_manufacturing_safety_licensing():
    areas = dict(applicable_areas("phytopharmaceutical"))
    assert ComplianceArea.manufacturing in areas
    assert ComplianceArea.safety_evidence in areas
    assert ComplianceArea.licensing in areas
    assert ComplianceArea.food_requirements not in areas
    assert ComplianceArea.cosmetic_requirements not in areas
    # always-applicable set
    for area in (
        ComplianceArea.classification,
        ComplianceArea.ingredients,
        ComplianceArea.labelling,
        ComplianceArea.claims,
        ComplianceArea.advertising,
    ):
        assert area in areas


def test_applicable_areas_food_adds_food_requirements_and_manufacturing():
    areas = dict(applicable_areas("ayurveda_aahara_or_nutraceutical"))
    assert ComplianceArea.food_requirements in areas
    assert ComplianceArea.manufacturing in areas
    assert ComplianceArea.safety_evidence not in areas
    assert ComplianceArea.licensing not in areas
    assert ComplianceArea.cosmetic_requirements not in areas


def test_applicable_areas_cosmetic_adds_cosmetic_requirements_and_manufacturing():
    areas = dict(applicable_areas("cosmetic"))
    assert ComplianceArea.cosmetic_requirements in areas
    assert ComplianceArea.manufacturing in areas
    assert ComplianceArea.food_requirements not in areas
    assert ComplianceArea.safety_evidence not in areas


def test_applicable_areas_unclear_is_only_always_applicable_set():
    areas = applicable_areas("unclear")
    area_names = {a for a, _ in areas}
    assert area_names == {
        ComplianceArea.classification,
        ComplianceArea.ingredients,
        ComplianceArea.labelling,
        ComplianceArea.claims,
        ComplianceArea.advertising,
    }
    reason_by_area = dict(areas)
    assert "classif" in reason_by_area[ComplianceArea.classification].lower()


def test_applicable_areas_none_matches_unclear_behaviour():
    assert {a for a, _ in applicable_areas(None)} == {a for a, _ in applicable_areas("unclear")}


def test_applicable_areas_out_of_scope_is_empty():
    assert applicable_areas("out_of_scope") == []


def test_no_applicability_reason_contains_a_legal_reference_pattern():
    """Regression test for the core no-fabrication constraint: every
    reason applicable_areas can produce, for every PRODUCT_CATEGORIES
    value (and None), must be phrased structurally - never as a quote or
    paraphrase of a specific statute/rule/regulation/section/clause/
    schedule/article number."""
    for classification in [*PRODUCT_CATEGORIES, None]:
        for area, reason in applicable_areas(classification):
            assert not _LEGAL_REFERENCE_RE.search(reason), (
                f"applicability_reason for area={area!r}, classification={classification!r} "
                f"looks like a legal citation: {reason!r}"
            )


# ---------------------------------------------------------------------------
# HTTP-level: generate / list / update / delete.
# ---------------------------------------------------------------------------


async def test_generate_checklist_matches_applicable_areas_all_unknown(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products", json={"name": "Ashwagandha Tablets", "product_classification": "phytopharmaceutical"}, headers=headers
    )
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    expected_areas = {a.value for a, _ in applicable_areas("phytopharmaceutical")}
    got_areas = {item["area"] for item in body["items"]}
    assert got_areas == expected_areas
    assert all(item["status"] == "unknown" for item in body["items"])
    assert body["summary"]["unknown"] == len(body["items"])
    assert body["summary"]["total"] == len(body["items"])


async def test_regenerate_is_idempotent_and_preserves_user_set_status(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products", json={"name": "Herbal Cream", "product_classification": "cosmetic"}, headers=headers
    )
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    items = resp.json()["items"]
    first_count = len(items)
    labelling_item = next(i for i in items if i["area"] == "labelling")

    resp = await client.patch(
        f"/products/{product_id}/compliance/{labelling_item['id']}",
        json={"status": "complete", "notes": "Verified by hand"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == first_count

    labelling_after = next(i for i in body["items"] if i["area"] == "labelling")
    assert labelling_after["status"] == "complete"
    assert labelling_after["notes"] == "Verified by hand"


async def test_reclassification_marks_item_not_applicable_not_deleted(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products", json={"name": "Herbal Balm", "product_classification": "cosmetic"}, headers=headers
    )
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    items = resp.json()["items"]
    cosmetic_item = next(i for i in items if i["area"] == "cosmetic_requirements")

    resp = await client.patch(
        f"/products/{product_id}", json={"product_classification": "phytopharmaceutical"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    cosmetic_after = next(i for i in body["items"] if i["id"] == cosmetic_item["id"])
    assert cosmetic_after["status"] == "not_applicable"
    # newly-applicable areas for the new classification are present too
    got_areas = {i["area"] for i in body["items"]}
    assert "safety_evidence" in got_areas
    assert "licensing" in got_areas


async def test_patch_updates_status_and_notes_and_writes_audit_row(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Neem Soap", "product_classification": "cosmetic"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    item = resp.json()["items"][0]

    resp = await client.patch(
        f"/products/{product_id}/compliance/{item['id']}",
        json={"status": "action_required", "notes": "Need to gather evidence"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "action_required"
    assert body["notes"] == "Need to gather evidence"
    assert body["updated_by_user_id"] is not None

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLogEntry).where(AuditLogEntry.action == "compliance.update").order_by(AuditLogEntry.created_at.desc())
        )
        audit = result.scalars().first()
        assert audit is not None
        assert audit.detail["item_id"] == item["id"]
        assert audit.detail["old_status"] == "unknown"
        assert audit.detail["new_status"] == "action_required"


async def test_other_users_product_is_403_on_get_post_patch(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Private Product"}, headers=headers_a)
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers_a)
    item_id = resp.json()["items"][0]["id"]

    assert (await client.get(f"/products/{product_id}/compliance", headers=headers_b)).status_code == 403
    assert (await client.post(f"/products/{product_id}/compliance", headers=headers_b)).status_code == 403
    assert (
        await client.patch(
            f"/products/{product_id}/compliance/{item_id}", json={"status": "complete"}, headers=headers_b
        )
    ).status_code == 403


async def test_item_from_a_different_product_returns_404(client, make_user):
    headers = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Product One", "product_classification": "cosmetic"}, headers=headers)
    product_one_id = resp.json()["id"]
    resp = await client.post("/products", json={"name": "Product Two", "product_classification": "cosmetic"}, headers=headers)
    product_two_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_one_id}/compliance", headers=headers)
    item_id = resp.json()["items"][0]["id"]

    resp = await client.patch(
        f"/products/{product_two_id}/compliance/{item_id}", json={"status": "complete"}, headers=headers
    )
    assert resp.status_code == 404


async def test_delete_product_with_compliance_items_returns_204(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "To Delete", "product_classification": "cosmetic"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    assert len(resp.json()["items"]) > 0

    resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    resp = await client.get(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 404


async def test_generate_with_evidence_only_cites_real_source_documents(client, make_user):
    """Slow - needs a live Ollama embed call + Chroma query. Optional per
    the task spec, included since Ollama/Chroma are up in this environment.
    Whatever evidence comes back (possibly none, if the corpus has nothing
    relevant), every doc_id in it must be a real source_documents row -
    never hand-filled."""
    from app.db.models import SourceDocument

    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={
            "name": "Triphala Churna",
            "product_classification": "ayurveda_aahara_or_nutraceutical",
            "jurisdiction": "india",
            "intended_use": "digestive health supplement",
        },
        headers=headers,
    )
    product_id = resp.json()["id"]

    resp = await client.post(f"/products/{product_id}/compliance?with_evidence=true", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    async with AsyncSessionLocal() as session:
        for item in body["items"]:
            for ev in item["evidence"] or []:
                result = await session.execute(
                    select(SourceDocument).where(
                        SourceDocument.doc_id == ev["doc_id"],
                        SourceDocument.section_or_article == ev["section_or_article"],
                    )
                )
                assert result.scalars().first() is not None, f"evidence cites unknown doc: {ev}"
