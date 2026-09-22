"""Tests for the case-messages thread (Phase 23's expert-escalation loop:
user -> AI assessment -> escalation -> expert assigned -> review ->
additional information if required -> expert response -> user
notification -> closure). Reuses the _seed_case pattern from
test_cases_and_admin.py."""

import uuid

from app.db.base import AsyncSessionLocal
from app.db.models import AuditLogEntry, Case, CaseQueue, CaseRiskLevel, CaseStatus, Conversation, Message, MessageRole, UserRole


async def _audit_actions_for_case(case_id: str) -> list[str]:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(select(AuditLogEntry.action, AuditLogEntry.detail))
        return [action for action, detail in result.all() if detail and detail.get("case_id") == case_id]


async def _seed_case(user_email_suffix: str, queue: CaseQueue = CaseQueue.ip) -> tuple[str, str]:
    """Insert a user + conversation + messages + escalated Case in the
    given queue. Returns (case_id, user_email).

    Also grants the new-style `user` role via UserRoleAssignment (the
    same thing tests/conftest.py's `make_user` fixture does) - without
    it app.authz.service resolves zero permissions for this user, since
    the legacy `users.role` column is no longer read for authorization.
    """
    from sqlalchemy import select

    from app.auth.security import hash_password
    from app.authz.constants import RoleName
    from app.db.models import Role, User, UserRoleAssignment

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-msg-user-{user_email_suffix}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        role_row = (await session.execute(select(Role).where(Role.name == RoleName.USER))).scalar_one()
        session.add(UserRoleAssignment(user_id=user.id, role_id=role_row.id))

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


async def _user_token_for_case_owner(make_user, user_email: str) -> str:
    """The _seed_case user is inserted directly against the DB (not via
    make_user), so log in as that same user through /auth to get a real
    token bound to that exact user_id."""
    return user_email


async def test_user_posts_note_on_own_case(client, make_user):
    from app.auth.security import create_access_token
    from app.db.base import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import User

    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8])
    async with AsyncSessionLocal() as session:
        owner = (await session.execute(select(User).where(User.email == user_email))).scalar_one()
        owner_token = create_access_token(str(owner.id), owner.role.value)

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"body": "Any update?", "kind": "note"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["kind"] == "note"
    assert body["body"] == "Any update?"
    assert body["author_email"] == user_email
    assert body["author_role"] == "user"

    get_resp = await client.get(f"/cases/{case_id}/messages", headers={"Authorization": f"Bearer {owner_token}"})
    assert get_resp.status_code == 200
    thread = get_resp.json()
    assert any(m["id"] == body["id"] for m in thread)
    assert "case.message" in await _audit_actions_for_case(case_id)


async def test_user_cannot_post_info_request(client, make_user):
    from app.auth.security import create_access_token
    from app.db.base import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import User

    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8])
    async with AsyncSessionLocal() as session:
        owner = (await session.execute(select(User).where(User.email == user_email))).scalar_one()
        owner_token = create_access_token(str(owner.id), owner.role.value)

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"body": "please answer sooner", "kind": "info_request"},
    )
    assert resp.status_code == 403


async def test_user_cannot_post_expert_response(client, make_user):
    from app.auth.security import create_access_token
    from app.db.base import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import User

    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8])
    async with AsyncSessionLocal() as session:
        owner = (await session.execute(select(User).where(User.email == user_email))).scalar_one()
        owner_token = create_access_token(str(owner.id), owner.role.value)

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"body": "final answer", "kind": "expert_response"},
    )
    assert resp.status_code == 403


async def test_reviewer_info_request_sets_awaiting_user_input(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    claim_resp = await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    assert claim_resp.status_code == 200

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"body": "Can you share more ingredient detail?", "kind": "info_request"},
    )
    assert resp.status_code == 201
    assert resp.json()["kind"] == "info_request"
    assert resp.json()["author_role"] == "facilitator"

    async with AsyncSessionLocal() as session:
        case = await session.get(Case, uuid.UUID(case_id))
        assert case.status == CaseStatus.awaiting_user_input


async def test_user_info_response_flips_status_back(client, make_user):
    from app.auth.security import create_access_token
    from app.db.base import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import User

    case_id, user_email = await _seed_case(uuid.uuid4().hex[:8])
    async with AsyncSessionLocal() as session:
        owner = (await session.execute(select(User).where(User.email == user_email))).scalar_one()
        owner_token = create_access_token(str(owner.id), owner.role.value)

    _email, _password, fac_token = await make_user(role="facilitator")
    await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})
    await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"body": "need more info", "kind": "info_request"},
    )
    async with AsyncSessionLocal() as session:
        case = await session.get(Case, uuid.UUID(case_id))
        assert case.status == CaseStatus.awaiting_user_input

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"body": "here is more info", "kind": "info_response"},
    )
    assert resp.status_code == 201
    assert resp.json()["kind"] == "info_response"

    async with AsyncSessionLocal() as session:
        case = await session.get(Case, uuid.UUID(case_id))
        assert case.status != CaseStatus.awaiting_user_input
        assert case.status == CaseStatus.in_progress


async def test_reviewer_expert_response_does_not_close_case(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})

    async with AsyncSessionLocal() as session:
        case = await session.get(Case, uuid.UUID(case_id))
        status_before = case.status

    resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"body": "Here is the final expert guidance.", "kind": "expert_response"},
    )
    assert resp.status_code == 201
    assert resp.json()["kind"] == "expert_response"

    async with AsyncSessionLocal() as session:
        case = await session.get(Case, uuid.UUID(case_id))
        assert case.status == status_before
        assert case.status != CaseStatus.closed

    # Closing is still the reviewer's separate, explicit action.
    close_resp = await client.post(
        f"/cases/{case_id}/close",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"resolution_summary": "done"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"


async def test_unrelated_user_forbidden_on_get_and_post(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, other_token = await make_user(role="user")

    get_resp = await client.get(f"/cases/{case_id}/messages", headers={"Authorization": f"Bearer {other_token}"})
    assert get_resp.status_code == 403

    post_resp = await client.post(
        f"/cases/{case_id}/messages",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"body": "hello", "kind": "note"},
    )
    assert post_resp.status_code == 403


async def test_messages_ordered_oldest_first(client, make_user):
    case_id, _user_email = await _seed_case(uuid.uuid4().hex[:8])
    _email, _password, fac_token = await make_user(role="facilitator")
    await client.post(f"/cases/{case_id}/claim", headers={"Authorization": f"Bearer {fac_token}"})

    for i in range(3):
        r = await client.post(
            f"/cases/{case_id}/messages",
            headers={"Authorization": f"Bearer {fac_token}"},
            json={"body": f"note {i}", "kind": "note"},
        )
        assert r.status_code == 201

    resp = await client.get(f"/cases/{case_id}/messages", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 200
    bodies = [m["body"] for m in resp.json()]
    assert bodies == ["note 0", "note 1", "note 2"]
    created_ats = [m["created_at"] for m in resp.json()]
    assert created_ats == sorted(created_ats)


async def test_nonexistent_case_404(client, make_user):
    _email, _password, fac_token = await make_user(role="facilitator")
    resp = await client.get(f"/cases/{uuid.uuid4()}/messages", headers={"Authorization": f"Bearer {fac_token}"})
    assert resp.status_code == 404

    resp2 = await client.post(
        f"/cases/{uuid.uuid4()}/messages",
        headers={"Authorization": f"Bearer {fac_token}"},
        json={"body": "hi", "kind": "note"},
    )
    assert resp2.status_code == 404
