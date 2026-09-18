"""HTTP-level tests wiring Case to Product (RBAC Phase 2 gap closed now
that `products` exists - see docs/superpowers/plans, commit 8d008d0).

Follows tests/test_products.py's style (client/make_user fixtures) for the
ownership-gated endpoints, and tests/test_cases_and_admin.py's `_seed_case`
style for direct-DB seeding where a live LLM call would be needlessly slow.
"""

import uuid

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.base import AsyncSessionLocal
from app.db.models import (
    Case, CaseQueue, CaseRiskLevel, CaseStatus, Conversation, Message, MessageRole, Product, User, UserRole,
)


async def _auth_headers(make_user, role: str = "user", organization_id=None):
    _email, _password, token = await make_user(role=role, organization_id=organization_id)
    return {"Authorization": f"Bearer {token}"}


async def _seed_case_with_product(suffix: str, queue: CaseQueue = CaseQueue.ip) -> tuple[str, str, str]:
    """Insert a user + Product + conversation + messages + Case linked to
    that product. Returns (case_id, product_id, product_name)."""
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-product-user-{suffix}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        product = Product(owner_user_id=user.id, name=f"Seeded Product {suffix}")
        session.add(product)
        await session.flush()

        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()

        session.add(Message(conversation_id=conversation.id, role=MessageRole.user, content="Q?"))
        session.add(Message(conversation_id=conversation.id, role=MessageRole.assistant, content="A."))

        case = Case(
            user_id=user.id,
            conversation_id=conversation.id,
            product_id=product.id,
            question="Q?",
            product_classification="unclear",
            jurisdiction="india",
            confidence_score=0.1,
            confidence_level="low",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=queue,
        )
        session.add(case)
        await session.commit()
        return str(case.id), str(product.id), product.name


# --- POST /chat with productId --------------------------------------------


async def test_chat_with_own_product_id_links_case(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "My Chat Product"}, headers=headers)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    # Out-of-scope question short-circuits before retrieval/reasoning LLM
    # calls but still creates a Case (see tests/test_chat_creates_case.py).
    resp = await client.post(
        "/chat",
        json={
            "conversationId": None,
            "text": "What is the weather today?",
            "jurisdiction": "india",
            "productId": product_id,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    conversation_id = resp.json()["conversationId"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Case).where(Case.conversation_id == uuid.UUID(conversation_id))
        )
        case = result.scalar_one()
        assert case.product_id is not None
        assert str(case.product_id) == product_id


async def test_chat_with_other_users_product_id_returns_404(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "User A's Product"}, headers=headers_a)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    resp = await client.post(
        "/chat",
        json={
            "conversationId": None,
            "text": "What is the weather today?",
            "jurisdiction": "india",
            "productId": product_id,
        },
        headers=headers_b,
    )
    assert resp.status_code == 404

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Case).where(Case.product_id == uuid.UUID(product_id)))
        assert result.scalar_one_or_none() is None


# --- GET /products/{id}/cases ----------------------------------------------


async def test_get_product_cases_returns_linked_case_for_owner(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.post("/products", json={"name": "Dossier Product"}, headers=headers)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    resp = await client.post(
        "/chat",
        json={
            "conversationId": None,
            "text": "What is the weather today?",
            "jurisdiction": "india",
            "productId": product_id,
        },
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.get(f"/products/{product_id}/cases", headers=headers)
    assert resp.status_code == 200, resp.text
    cases = resp.json()
    assert len(cases) == 1
    assert cases[0]["product_id"] == product_id


async def test_get_product_cases_for_other_users_product_returns_403(client, make_user):
    headers_a = await _auth_headers(make_user)
    headers_b = await _auth_headers(make_user)

    resp = await client.post("/products", json={"name": "Private Dossier Product"}, headers=headers_a)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    resp = await client.get(f"/products/{product_id}/cases", headers=headers_b)
    assert resp.status_code == 403


# --- CaseOut.product_name ---------------------------------------------------


async def test_case_out_includes_product_name(client, make_user):
    case_id, product_id, product_name = await _seed_case_with_product(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    cases = resp.json()
    match = next((c for c in cases if c["id"] == case_id), None)
    assert match is not None
    assert match["product_id"] == product_id
    assert match["product_name"] == product_name
