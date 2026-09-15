"""Tests for the escalation case queue and admin user list - inserts
EscalationItem/Conversation/Message rows directly (no live LLM call
needed to exercise these routes)."""

import uuid

from app.db.base import AsyncSessionLocal
from app.db.models import Conversation, EscalationItem, EscalationStatus, Message, MessageRole, UserRole


async def _seed_open_case(user_email_suffix: str) -> tuple[str, str]:
    """Insert a user + conversation + messages + open EscalationItem.
    Returns (case_id, user_email)."""
    from app.auth.security import hash_password
    from app.db.models import User

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-user-{user_email_suffix}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()

        session.add(Message(conversation_id=conversation.id, role=MessageRole.user, content="Q?"))
        session.add(Message(conversation_id=conversation.id, role=MessageRole.assistant, content="A."))

        item = EscalationItem(
            conversation_id=conversation.id,
            status=EscalationStatus.open,
            reason="test reason",
            product_classification="unclear",
            jurisdiction="india",
            confidence_score=0.1,
            confidence_level="low",
        )
        session.add(item)
        await session.commit()
        return str(item.id), user.email


async def test_case_queue_requires_facilitator_role(client, make_user):
    _email, _password, user_token = await make_user(role=UserRole.user)
    resp = await client.get("/cases", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


async def test_case_queue_lists_open_case(client, make_user):
    case_id, user_email = await _seed_open_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role=UserRole.facilitator)

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    cases = resp.json()
    match = next((c for c in cases if c["id"] == case_id), None)
    assert match is not None
    assert match["question"] == "Q?"
    assert match["answer"] == "A."
    assert match["user_email"] == user_email
    assert match["status"] == "open"


async def test_regulatory_expert_can_also_see_and_claim_case(client, make_user):
    case_id, _user_email = await _seed_open_case(uuid.uuid4().hex[:8])
    _email, _password, expert_token = await make_user(role=UserRole.regulatory_expert)

    claim_resp = await client.post(
        f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {expert_token}"}
    )
    assert claim_resp.status_code == 200
    assert claim_resp.json()["status"] == "in_progress"
    assert claim_resp.json()["assigned_facilitator_email"] is not None


async def test_close_case_sets_resolution(client, make_user):
    case_id, _user_email = await _seed_open_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role=UserRole.facilitator)

    resp = await client.post(
        f"/cases/{case_id}/close",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"resolution_summary": "resolved in test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "closed"
    assert body["resolution_summary"] == "resolved in test"
    assert body["closed_at"] is not None


async def test_claim_nonexistent_case_404(client, make_user):
    _email, _password, fac_token = await make_user(role=UserRole.facilitator)
    resp = await client.post(
        f"/cases/{uuid.uuid4()}/claim", headers={"Authorization": f"Bearer {fac_token}"}
    )
    assert resp.status_code == 404


async def test_admin_users_requires_admin_role(client, make_user):
    _email, _password, fac_token = await make_user(role=UserRole.facilitator)
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 403


async def test_admin_users_lists_users(client, make_user):
    email, _password, admin_token = await make_user(role=UserRole.admin)
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert email in emails


async def test_admin_stats_shape(client, make_user):
    _email, _password, admin_token = await make_user(role=UserRole.admin)
    resp = await client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "users_by_role" in body
    assert "open_cases" in body
    assert "closed_cases" in body
