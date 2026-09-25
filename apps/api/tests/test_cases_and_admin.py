"""Tests for the case queue and admin user list - inserts Case/
Conversation/Message rows directly (no live LLM call needed to exercise
these routes)."""

import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import (
    AuditLogEntry, Case, CaseQueue, CaseRiskLevel, CaseStatus, Conversation, Message, MessageRole, UserRole,
)


async def _audit_actions_for_case(case_id: str) -> list[str]:
    """Every AuditLogEntry.action recorded with this case_id in `detail`
    (spec's audit-trail requirement, Global Constraints) - queried
    directly rather than via an endpoint, since audit rows aren't
    exposed through /cases."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuditLogEntry.action, AuditLogEntry.detail))
        return [action for action, detail in result.all() if detail and detail.get("case_id") == case_id]


async def _seed_case(user_email_suffix: str, queue: CaseQueue = CaseQueue.ip) -> tuple[str, str]:
    """Insert a user + conversation + messages + escalated Case in the
    given queue. Returns (case_id, user_email)."""
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

        case = Case(
            user_id=user.id,
            conversation_id=conversation.id,
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
        return str(case.id), user.email


async def test_plain_user_sees_only_their_own_cases_not_the_full_queue(client, make_user):
    # CASE_VIEW_OWN (granted to RoleName.USER) is a different, narrower
    # view than CASE_VIEW_QUEUE (facilitator/legal_expert/regulatory_expert) -
    # a plain user gets 200 + their own cases, never the full reviewer queue.
    # _seed_case's user has no real UserRoleAssignment (it's a throwaway
    # row, not a real login), so this needs a real make_user(role="user")
    # account to mint a token that actually carries CASE_VIEW_OWN.
    my_email, _pw, my_token = await make_user(role="user")

    async with AsyncSessionLocal() as session:
        from app.db.models import User

        my_user = (await session.execute(select(User).where(User.email == my_email))).scalar_one()

        conversation = Conversation(user_id=my_user.id)
        session.add(conversation)
        await session.flush()
        my_case = Case(
            user_id=my_user.id,
            conversation_id=conversation.id,
            question="My own question?",
            product_classification="unclear",
            jurisdiction="india",
            confidence_score=0.1,
            confidence_level="low",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=CaseQueue.ip,
        )
        session.add(my_case)
        await session.commit()
        my_case_id = str(my_case.id)

    other_case_id, _other_email = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {my_token}"})
    assert resp.status_code == 200
    cases = resp.json()
    case_ids = {c["id"] for c in cases}
    assert my_case_id in case_ids
    assert other_case_id not in case_ids


async def test_user_with_no_cases_gets_empty_list_not_403(client, make_user):
    _email, _password, user_token = await make_user(role="user")
    resp = await client.get("/cases", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_case_queue_lists_open_case(client, make_user):
    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    cases = resp.json()
    match = next((c for c in cases if c["id"] == case_id), None)
    assert match is not None
    assert match["question"] == "Q?"
    assert match["answer"] == "A."
    assert match["user_email"] == user_email
    assert match["status"] == "escalated"
    assert match["queue"] == "ip"


async def test_facilitator_does_not_see_legal_queue_cases(client, make_user):
    """Queue scoping (spec Section 8): a facilitator's ip-queue grant must
    not surface cases routed to the legal queue."""
    legal_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert legal_case_id not in case_ids


async def test_legal_expert_sees_only_legal_queue(client, make_user):
    legal_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    ip_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, legal_token = await make_user(role="legal_expert")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {legal_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert legal_case_id in case_ids
    assert ip_case_id not in case_ids


async def test_regulatory_expert_sees_only_regulatory_queue(client, make_user):
    reg_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.regulatory)
    ip_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.ip)
    _email, _password, reg_token = await make_user(role="regulatory_expert")

    resp = await client.get("/cases", headers={"Authorization": f"Bearer {reg_token}"})
    assert resp.status_code == 200
    case_ids = {c["id"] for c in resp.json()}
    assert reg_case_id in case_ids
    assert ip_case_id not in case_ids


async def test_close_case_sets_resolution(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert claim_resp.status_code == 200

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
    assert "case.close" in await _audit_actions_for_case(case_id)


async def test_claim_nonexistent_case_404(client, make_user):
    _email, _password, fac_token = await make_user(role="facilitator")
    resp = await client.post(
        f"/cases/{uuid.uuid4()}/claim", headers={"Authorization": f"Bearer {fac_token}"}
    )
    assert resp.status_code == 404


async def test_claim_case_outside_queue_forbidden(client, make_user):
    """A facilitator (ip queue) must not be able to claim a case routed to
    the legal queue - claim_case previously only checked CASE_ASSIGN, with
    no queue-scope check."""
    legal_case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    _email, _password, fac_token = await make_user(role="facilitator")

    resp = await client.post(
        f"/cases/{legal_case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"}
    )
    assert resp.status_code == 403


async def test_claim_already_claimed_case_conflict(client, make_user):
    """A second facilitator must not be able to steal a case already
    assigned to a different facilitator."""
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    first_claim = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert first_claim.status_code == 200

    _email2, _password2, other_fac_token = await make_user(role="facilitator")
    second_claim = await client.post(
        f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {other_fac_token}"}
    )
    assert second_claim.status_code == 409


async def test_close_case_requires_assigned_reviewer(client, make_user):
    """Mirrors test_review_action_requires_assigned_reviewer: only the
    facilitator who claimed the case may close it."""
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert claim_resp.status_code == 200

    _email2, _password2, other_fac_token = await make_user(role="facilitator")
    close_resp = await client.post(
        f"/cases/{case_id}/close",
        headers={"Authorization": f"Bearer {other_fac_token}"},
        json={"resolution_summary": "trying to close someone else's case"},
    )
    assert close_resp.status_code == 403


async def test_legal_expert_cannot_escalate_no_higher_tier(client, make_user):
    """legal_expert never holds Permission.REVIEW_ESCALATE (it's the top
    review tier - nothing to escalate to, per app.authz.constants'
    ROLE_PERMISSIONS[RoleName.LEGAL_EXPERT]) - review_case must reject an
    escalate action from this role even though it gates the route on the
    broader review.view permission."""
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8], queue=CaseQueue.legal)
    _email, _password, legal_token = await make_user(role="legal_expert")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {legal_token}"})
    assert claim_resp.status_code == 200

    review_resp = await client.post(
        f"/cases/{case_id}/review",
        headers={"Authorization": f"Bearer {legal_token}"},
        json={"action": "escalate", "notes": "no higher tier exists"},
    )
    assert review_resp.status_code == 403


async def test_review_action_requires_assigned_reviewer(client, make_user):
    """can_perform_action's ownership check (app.authz.service): only the
    facilitator who claimed the case may review it."""
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert claim_resp.status_code == 200

    _email2, _password2, other_fac_token = await make_user(role="facilitator")
    review_resp = await client.post(
        f"/cases/{case_id}/review",
        headers={"Authorization": f"Bearer {other_fac_token}"},
        json={"action": "approve", "notes": "looks fine"},
    )
    assert review_resp.status_code == 403


async def test_review_action_approve_by_assigned_reviewer(client, make_user):
    case_id, _ = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})

    resp = await client.post(
        f"/cases/{case_id}/review",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"action": "approve", "notes": "looks fine"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "approve"
    actions = await _audit_actions_for_case(case_id)
    assert "case.claim" in actions
    assert "case.review" in actions


async def test_admin_users_requires_users_manage_permission(client, make_user):
    _email, _password, fac_token = await make_user(role="facilitator")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 403


async def test_admin_users_lists_users(client, make_user):
    email, _password, admin_token = await make_user(role="ministry_admin")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert email in emails


async def test_admin_stats_shape(client, make_user):
    _email, _password, admin_token = await make_user(role="ministry_admin")
    resp = await client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "users_by_role" in body
    assert "open_cases" in body
    assert "closed_cases" in body
