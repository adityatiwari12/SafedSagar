"""HTTP-level tests for the products router - ownership+org-scoped CRUD
(docs/product/rbac-full-implementation-spec.md Phase 3, Products only).
Follows tests/test_cases_and_admin.py's style: httpx `client` + `make_user`
fixtures, no direct DB seeding except through the API itself."""


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


async def test_create_product_returns_201_and_echoes_fields(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={
            "name": "Ashwagandha Capsules",
            "description": "Standardized extract capsule",
            "product_classification": "phytopharmaceutical",
            "jurisdiction": "india",
            "ingredients": [{"name": "Withania somnifera", "quantity": "300mg"}],
            "biological_resources": ["Withania somnifera"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Ashwagandha Capsules"
    assert body["description"] == "Standardized extract capsule"
    assert body["product_classification"] == "phytopharmaceutical"
    assert body["jurisdiction"] == "india"
    assert body["ingredients"] == [{"name": "Withania somnifera", "quantity": "300mg"}]
    assert body["biological_resources"] == ["Withania somnifera"]
    assert body["id"]
    assert body["owner_user_id"]
    assert body["created_at"]
    assert body["updated_at"]


async def test_create_product_invalid_classification_returns_400(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={"name": "Bad Product", "product_classification": "not_a_real_category"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_create_product_invalid_jurisdiction_returns_400(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={"name": "Bad Jurisdiction", "jurisdiction": "mars"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_create_product_with_foreign_org_returns_403(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={"name": "Sneaky Org Product", "organization_id": "00000000-0000-0000-0000-000000000001"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_list_products_only_returns_own_products(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "User A Product"}, headers=headers_a)
    assert resp.status_code == 201
    product_a_id = resp.json()["id"]

    resp = await client.post("/products", json={"name": "User B Product"}, headers=headers_b)
    assert resp.status_code == 201

    resp = await client.get("/products", headers=headers_b)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert product_a_id not in ids


async def test_get_other_users_product_returns_403(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Private Product"}, headers=headers_a)
    product_id = resp.json()["id"]

    resp = await client.get(f"/products/{product_id}", headers=headers_b)
    assert resp.status_code == 403


async def test_patch_updates_only_supplied_fields(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post(
        "/products",
        json={"name": "Original Name", "description": "Original description", "jurisdiction": "india"},
        headers=headers,
    )
    product_id = resp.json()["id"]

    resp = await client.patch(f"/products/{product_id}", json={"description": "Updated description"}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["description"] == "Updated description"
    assert body["name"] == "Original Name"
    assert body["jurisdiction"] == "india"


async def test_patch_other_users_product_returns_403(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Owner A Product"}, headers=headers_a)
    product_id = resp.json()["id"]

    resp = await client.patch(f"/products/{product_id}", json={"name": "Hijacked"}, headers=headers_b)
    assert resp.status_code == 403


async def test_delete_own_product_then_get_returns_404(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "To Delete"}, headers=headers)
    product_id = resp.json()["id"]

    resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 404


async def test_delete_other_users_product_returns_403(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Owner A Product 2"}, headers=headers_a)
    product_id = resp.json()["id"]

    resp = await client.delete(f"/products/{product_id}", headers=headers_b)
    assert resp.status_code == 403


async def test_facilitator_has_no_product_permissions(client, make_user):
    headers = await _auth_headers(make_user, role="facilitator")

    resp = await client.post("/products", json={"name": "Facilitator Product"}, headers=headers)
    assert resp.status_code == 403

    resp = await client.get("/products", headers=headers)
    assert resp.status_code == 403


async def test_delete_product_with_linked_case_detaches_instead_of_500(client, make_user):
    """A Case is the assessment record of a question actually asked and
    answered; it outlives the product it was about. cases.product_id is a
    plain nullable FK with no ON DELETE, so deleting an assessed product
    raised a ForeignKeyViolationError (500) until delete_product detached
    them first."""
    import uuid as _uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models import Case, CaseRiskLevel, CaseStatus, User

    email, _password, token = await make_user()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/products", json={"name": "Assessed Product"}, headers=headers)
    product_id = resp.json()["id"]

    # Seed the Case directly rather than driving /chat: this test is about
    # the FK, not the graph, and a live LLM turn would make it slow.
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        case = Case(
            user_id=user.id,
            product_id=_uuid.UUID(product_id),
            question="Can I patent this?",
            risk_level=CaseRiskLevel.low,
            status=CaseStatus.resolved,
        )
        session.add(case)
        await session.commit()
        case_id = case.id

    resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    async with AsyncSessionLocal() as session:
        surviving = await session.get(Case, case_id)
        assert surviving is not None, "deleting a product must not destroy its assessment history"
        assert surviving.product_id is None


async def test_org_member_can_read_and_edit_but_not_delete(client, make_user):
    """Deletion is owner-only, deliberately stricter than read/update: a
    teammate collaborating on a shared dossier can edit it, but destroying
    it is the owner's call alone."""
    import uuid as _uuid

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
        "/products",
        json={"name": "Shared Org Dossier", "organization_id": org_id},
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    product_id = resp.json()["id"]

    assert (await client.get(f"/products/{product_id}", headers=teammate_headers)).status_code == 200

    resp = await client.patch(
        f"/products/{product_id}", json={"development_stage": "pilot"}, headers=teammate_headers
    )
    assert resp.status_code == 200, resp.text

    resp = await client.delete(f"/products/{product_id}", headers=teammate_headers)
    assert resp.status_code == 403

    assert (await client.delete(f"/products/{product_id}", headers=owner_headers)).status_code == 204
