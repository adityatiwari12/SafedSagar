"""HTTP-level tests for the documents router (Phase 28) - secure upload/
list/get/download/delete. Follows tests/test_products.py's style: httpx
`client` + `make_user` fixtures, real Postgres, no mocking of the storage
backend (LocalFilesystemStorage writes under app.config.settings.
document_storage_root, cleaned up implicitly since it's gitignored)."""

import uuid as _uuid

import pytest
from sqlalchemy import select

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models import Case, CaseRiskLevel, CaseStatus, Document, User
from app.documents.storage import LocalFilesystemStorage

_MINIMAL_PDF = b"%PDF-1.4\n%mock pdf content for tests\n%%EOF"


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


async def _get_document_row(document_id: str) -> Document:
    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, _uuid.UUID(document_id))
        assert doc is not None
        return doc


async def test_upload_valid_pdf_returns_201_with_metadata(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("label.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "label"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == "label.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(_MINIMAL_PDF)
    assert body["doc_kind"] == "label"
    assert body["status"] == "active"
    assert body["id"]
    assert body["owner_user_id"]
    # Never returns raw bytes or the internal storage key.
    assert "storage_key" not in body
    assert "source_text" not in body

    doc = await _get_document_row(body["id"])
    storage = LocalFilesystemStorage(settings.document_storage_root)
    assert storage.exists(doc.storage_key)
    assert storage.read(doc.storage_key) == _MINIMAL_PDF


async def test_upload_oversized_file_returns_400(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "document_max_upload_bytes", 10)
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("label.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "label"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "size" in resp.json()["detail"].lower() or "MB" in resp.json()["detail"]


async def test_upload_content_type_magic_byte_mismatch_returns_400(client, make_user):
    """A .txt file renamed to claim application/pdf - the Content-Type
    header and filename both lie, only the actual bytes are checked."""
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("not_really.pdf", b"just plain text, not a pdf", "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "magic" in resp.json()["detail"].lower()


async def test_upload_unsupported_content_type_returns_400(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("archive.zip", b"PK\x03\x04 fake zip", "application/zip")},
        data={"doc_kind": "other"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_download_returns_correct_bytes_and_content_type(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("cert.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "certificate"},
        headers=headers,
    )
    document_id = resp.json()["id"]

    resp = await client.get(f"/documents/{document_id}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.content == _MINIMAL_PDF
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert "cert.pdf" in resp.headers["content-disposition"]


async def test_other_user_cannot_get_download_or_delete(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post(
        "/documents",
        files={"file": ("private.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers_a,
    )
    document_id = resp.json()["id"]

    assert (await client.get(f"/documents/{document_id}", headers=headers_b)).status_code == 403
    assert (await client.get(f"/documents/{document_id}/download", headers=headers_b)).status_code == 403
    assert (await client.delete(f"/documents/{document_id}", headers=headers_b)).status_code == 403


async def test_owner_delete_then_get_returns_404_and_file_removed(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("to_delete.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers,
    )
    document_id = resp.json()["id"]
    doc = await _get_document_row(document_id)
    storage = LocalFilesystemStorage(settings.document_storage_root)
    assert storage.exists(doc.storage_key)

    resp = await client.delete(f"/documents/{document_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/documents/{document_id}", headers=headers)
    assert resp.status_code == 404

    resp = await client.get(f"/documents/{document_id}/download", headers=headers)
    assert resp.status_code == 404

    assert not storage.exists(doc.storage_key)


async def test_org_member_can_read_org_scoped_document(client, make_user):
    ministry_headers = await _auth_headers(make_user, role="ministry_admin")
    resp = await client.post(
        "/admin/organizations",
        json={"name": f"Org-{_uuid.uuid4().hex[:8]}", "org_type": "startup"},
        headers=ministry_headers,
    )
    org_id = resp.json()["id"]

    owner_headers = await _auth_headers(make_user, organization_id=_uuid.UUID(org_id))
    teammate_headers = await _auth_headers(make_user, organization_id=_uuid.UUID(org_id))

    resp = await client.post(
        "/documents",
        files={"file": ("shared.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "certificate", "organization_id": org_id},
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    document_id = resp.json()["id"]

    resp = await client.get(f"/documents/{document_id}", headers=teammate_headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/documents/{document_id}/download", headers=teammate_headers)
    assert resp.status_code == 200

    # Deletion is still owner-only.
    resp = await client.delete(f"/documents/{document_id}", headers=teammate_headers)
    assert resp.status_code == 403


async def test_upload_with_foreign_org_returns_403(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/documents",
        files={"file": ("sneaky.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other", "organization_id": "00000000-0000-0000-0000-000000000001"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_product_deletion_detaches_document_instead_of_orphaning(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Documented Product"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.post(
        "/documents",
        files={"file": ("spec_sheet.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "formulation_sheet", "product_id": product_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    document_id = resp.json()["id"]

    resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    # The document itself must survive, detached rather than orphaned/500d.
    resp = await client.get(f"/documents/{document_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["product_id"] is None


async def test_upload_with_foreign_product_returns_403(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Owner A Product"}, headers=headers_a)
    product_id = resp.json()["id"]

    resp = await client.post(
        "/documents",
        files={"file": ("hijack.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other", "product_id": product_id},
        headers=headers_b,
    )
    assert resp.status_code == 403


async def test_list_documents_only_returns_accessible(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post(
        "/documents",
        files={"file": ("a.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers_a,
    )
    document_a_id = resp.json()["id"]

    resp = await client.post(
        "/documents",
        files={"file": ("b.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers_b,
    )

    resp = await client.get("/documents", headers=headers_b)
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()]
    assert document_a_id not in ids


async def test_case_owner_can_access_document_attached_to_own_case(client, make_user):
    """A Case's own asker isn't covered by can_access_resource directly
    (Case has no owner_user_id column) - _can_access_case/_can_access_document
    check case.user_id explicitly, mirroring app.cases.router.
    _case_message_side's same distinction."""
    email, _password, token = await make_user()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        case = Case(
            user_id=user.id,
            question="Can I sell this abroad?",
            risk_level=CaseRiskLevel.low,
            status=CaseStatus.resolved,
        )
        session.add(case)
        await session.commit()
        case_id = case.id

    resp = await client.post(
        "/documents",
        files={"file": ("case_doc.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "correspondence", "case_id": str(case_id)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    document_id = resp.json()["id"]

    resp = await client.get(f"/documents/{document_id}", headers=headers)
    assert resp.status_code == 200


async def test_facilitator_has_no_document_create_permission(client, make_user):
    headers = await _auth_headers(make_user, role="facilitator")
    resp = await client.post(
        "/documents",
        files={"file": ("nope.pdf", _MINIMAL_PDF, "application/pdf")},
        data={"doc_kind": "other"},
        headers=headers,
    )
    assert resp.status_code == 403
