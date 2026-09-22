"""HTTP-level tests for the product assessment PDF report
(GET /products/{id}/report). Follows tests/test_documents.py's style:
httpx `client` + `make_user` fixtures, real Postgres, no mocking - a Case
row is seeded directly (bypassing the chat/graph pipeline, which is a
parallel agent's active work area), compliance/ABS are created through
their real endpoints with with_evidence left off (no live Chroma/Ollama
retrieval needed for these tests)."""

import uuid as _uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import AuditLogEntry, Case, CaseRiskLevel, CaseStatus, User


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


async def _create_product(client, headers, name: str = "Test Product") -> str:
    resp = await client.post(
        "/products",
        json={
            "name": name,
            "description": "A herbal wellness formulation.",
            "product_classification": "ayurveda_aahara_or_nutraceutical",
            "jurisdiction": "india",
            "intended_use": "General wellness",
            "claims": "Supports stress relief",
            "development_stage": "prototype",
            "ingredients": [{"name": "Ashwagandha extract", "quantity": "500mg"}],
            "biological_resources": ["Withania somnifera"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _seed_case_for_product(product_id: str, user_id: _uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        case = Case(
            user_id=user_id,
            product_id=_uuid.UUID(product_id),
            question="Is this formulation patentable in India?",
            product_classification="ayurveda_aahara_or_nutraceutical",
            jurisdiction="india",
            confidence_score=0.62,
            confidence_level="medium",
            risk_level=CaseRiskLevel.medium,
            status=CaseStatus.resolved,
            citations=[
                {
                    "doc_id": "patents-act-1970",
                    "title": "The Patents Act, 1970",
                    "section_or_article": "Section 3",
                    "source_url": "https://example.test/patents-act",
                }
            ],
        )
        session.add(case)
        await session.commit()


async def test_generate_report_for_empty_product_returns_valid_pdf(client, make_user):
    headers = await _auth_headers(make_user)
    product_id = await _create_product(client, headers, name="Empty Dossier Product")

    resp = await client.get(f"/products/{product_id}/report", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 0


async def test_generate_report_with_case_compliance_and_abs_is_larger(client, make_user):
    email, _password, token = await make_user()
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, headers, name="Full Dossier Product")

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        user_id = user.id
    await _seed_case_for_product(product_id, user_id)

    resp = await client.post(f"/products/{product_id}/compliance", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.put(
        f"/products/{product_id}/abs",
        json={
            "is_biological_resource": True,
            "resource_description": "Ashwagandha root extract",
            "origin": "india",
            "sourcing": "cultivated",
            "involves_traditional_knowledge": False,
            "purpose": "commercial",
            "user_entity_category": "indian_company",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    # Baseline: an otherwise-identical empty product's report, to compare
    # sizes against - a real minimum-content check, not just "no exception".
    empty_product_id = await _create_product(client, headers, name="Comparison Empty Product")
    empty_resp = await client.get(f"/products/{empty_product_id}/report", headers=headers)
    assert empty_resp.status_code == 200

    resp = await client.get(f"/products/{product_id}/report", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > len(empty_resp.content)


async def test_other_user_cannot_generate_report(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)
    product_id = await _create_product(client, headers_a, name="Private Product")

    resp = await client.get(f"/products/{product_id}/report", headers=headers_b)
    assert resp.status_code == 403


async def test_nonexistent_product_returns_404(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.get(f"/products/{_uuid.uuid4()}/report", headers=headers)
    assert resp.status_code == 404


async def test_generate_report_writes_audit_log_entry(client, make_user):
    headers = await _auth_headers(make_user)
    product_id = await _create_product(client, headers, name="Audited Product")

    resp = await client.get(f"/products/{product_id}/report", headers=headers)
    assert resp.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLogEntry).where(AuditLogEntry.action == "report.generate")
        )
        entries = result.scalars().all()
        assert any(e.detail.get("product_id") == product_id for e in entries)
