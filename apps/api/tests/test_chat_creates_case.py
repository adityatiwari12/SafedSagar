"""Verifies _process_chat_turn persists a Case row - doesn't need a live
LLM call for the routing/persistence assertion itself, so this drives
app.cases.service directly against a hand-built GraphState-shaped dict
rather than exercising the full /chat endpoint (that's covered by the
existing live-LLM smoke test elsewhere)."""

import uuid

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.base import AsyncSessionLocal
from app.db.models import Case, CaseStatus, Conversation, User, UserRole


async def test_out_of_scope_turn_creates_a_case():
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-chat-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()

    from app.auth.security import create_access_token
    token = create_access_token(str(user_id), "user")

    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversationId": None, "text": "What is the weather today?", "jurisdiction": "india"},
        )
    assert resp.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Case).where(Case.user_id == user_id))
        case = result.scalar_one()
        assert case.status == CaseStatus.resolved
        assert case.product_classification == "out_of_scope"


async def test_delete_conversation_detaches_case_instead_of_500():
    """Regression test: DELETE /conversations/{id} used to 500 with
    IntegrityError (cases_conversation_id_fkey) because every answered
    turn now creates a Case row FK'd to the conversation, but the delete
    endpoint only ever cleaned up Message/EscalationItem child rows. The
    fix detaches Case rows (sets conversation_id=NULL) rather than
    deleting them - they're the audit/review record."""
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-delete-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()

    from app.auth.security import create_access_token
    token = create_access_token(str(user_id), "user")

    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversationId": None, "text": "What is the weather today?", "jurisdiction": "india"},
        )
        assert resp.status_code == 200
        conversation_id = resp.json()["conversationId"]

        delete_resp = await client.delete(
            f"/conversations/{conversation_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_resp.status_code == 204

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Case).where(Case.user_id == user_id))
        case = result.scalar_one()
        assert case.conversation_id is None

        remaining_conversation = await session.get(Conversation, uuid.UUID(conversation_id))
        assert remaining_conversation is None
