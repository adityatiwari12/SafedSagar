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
