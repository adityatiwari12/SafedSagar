"""Multi-round conversational intake (FR-01).

Covers the three pieces of the round-capped intake loop that replaced the
old one-shot fixed-question gate:
  - assess_intake's fail-open behaviour on a malformed LLM reply (pure
    unit test, generate_json patched - no network),
  - _count_recent_clarifying_rounds' "resets after a real answer"
    semantics (pure DB rows, no LLM),
  - the two live /chat behaviours: a vague opener gets exactly ONE
    natural follow-up question, and a conversation that has already spent
    its 5 rounds gets a real answer carrying the best-effort next_step
    instead of a sixth question.

The two /chat tests are LIVE tests - they run the real graph against the
configured LLM, same as the existing test_chat_creates_case.py suite.
The cap-forcing one is deliberately live rather than mocked: forcing
assess_intake to report "insufficient" while ALSO exercising the real
run_remaining path it falls through to would mean patching out most of
what the test is meant to prove.
"""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.auth.security import create_access_token, hash_password
from app.chat.router import _INTAKE_ROUND_CAP, _count_recent_clarifying_rounds
from app.db.base import AsyncSessionLocal
from app.db.models import Conversation, Message, MessageRole, User, UserRole
from app.graph.nodes import assess_intake as assess_intake_module
from app.graph.nodes.assess_intake import assess_intake
from app.main import app

_BEST_EFFORT_FRAGMENT = (
    "This answer uses the best available understanding of your question after several "
    "clarifying rounds"
)


async def _make_chat_user() -> tuple[uuid.UUID, str]:
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"intake-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()
    return user_id, create_access_token(str(user_id), "user")


# ---------------------------------------------------------------------------
# assess_intake - fail-open on a malformed LLM reply
# ---------------------------------------------------------------------------


def test_assess_intake_fails_open_when_llm_reply_is_malformed(monkeypatch):
    """A parse failure must NEVER report "insufficient" - that would trap
    the user in an intake loop they can't answer their way out of."""

    def _boom(*args, **kwargs):
        raise ValueError("not JSON")

    monkeypatch.setattr(assess_intake_module, "generate_json", _boom)

    result = assess_intake({"question": "I have an Ayurvedic product", "retrieval_query": "x"})

    assert result == {"intake_sufficient": True, "intake_question": None}


def test_assess_intake_returns_single_question_when_insufficient(monkeypatch):
    monkeypatch.setattr(
        assess_intake_module,
        "generate_json",
        lambda *a, **k: {"sufficient": False, "question": "Which herbs are in it?"},
    )

    result = assess_intake({"question": "I have an Ayurvedic product", "history_text": None})

    assert result == {"intake_sufficient": False, "intake_question": "Which herbs are in it?"}


def test_assess_intake_drops_a_blank_question(monkeypatch):
    """"sufficient": false with no usable question is still "not
    sufficient" - the router supplies its own generic fallback."""
    monkeypatch.setattr(
        assess_intake_module, "generate_json", lambda *a, **k: {"sufficient": False, "question": "  "}
    )

    result = assess_intake({"question": "q"})

    assert result == {"intake_sufficient": False, "intake_question": None}


# ---------------------------------------------------------------------------
# _count_recent_clarifying_rounds
# ---------------------------------------------------------------------------


async def _count_rounds_for(rows: list[dict]) -> int:
    """Seed a conversation with `rows` (oldest-first; each a kwargs dict
    for Message minus conversation_id/created_at - created_at is assigned
    increasing so ordering is deterministic regardless of insert speed)
    and return _count_recent_clarifying_rounds for it."""
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"intake-count-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()
        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()

        base = datetime.now(timezone.utc) - timedelta(hours=1)
        for i, row in enumerate(rows):
            session.add(
                Message(
                    conversation_id=conversation.id,
                    created_at=base + timedelta(minutes=i),
                    **row,
                )
            )
        await session.commit()
        conversation_id = conversation.id

    async with AsyncSessionLocal() as session:
        fresh = await session.get(Conversation, conversation_id)
        return await _count_recent_clarifying_rounds(session, fresh)


def _clarifying_row(text: str = "What's in it?") -> dict:
    return {
        "role": MessageRole.assistant,
        "content": text,
        "response_json": {"clarifying_questions": [text]},
    }


def _answer_row(text: str = "Here is the answer.") -> dict:
    return {
        "role": MessageRole.assistant,
        "content": text,
        "response_json": {"answer": text, "clarifying_questions": None},
    }


async def test_count_rounds_is_zero_for_a_conversation_with_no_assistant_turns():
    assert await _count_rounds_for([]) == 0


async def test_count_rounds_resets_after_a_real_answer():
    """3 clarifying rounds, then a real answer, then nothing -> 0. A fresh
    ambiguous follow-up later in a long conversation gets its own full
    budget rather than inheriting a spent one."""
    rounds = await _count_rounds_for(
        [_clarifying_row("q1"), _clarifying_row("q2"), _clarifying_row("q3"), _answer_row()]
    )
    assert rounds == 0


async def test_count_rounds_counts_consecutive_trailing_clarifying_rounds():
    assert await _count_rounds_for([_clarifying_row("q1"), _clarifying_row("q2")]) == 2


async def test_count_rounds_ignores_user_messages_between_rounds():
    """The real conversation shape interleaves user replies - only the
    assistant's own turns are rounds."""
    rounds = await _count_rounds_for(
        [
            {"role": MessageRole.user, "content": "I have a product"},
            _clarifying_row("q1"),
            {"role": MessageRole.user, "content": "It has ashwagandha"},
            _clarifying_row("q2"),
        ]
    )
    assert rounds == 2


# ---------------------------------------------------------------------------
# Live /chat behaviour
# ---------------------------------------------------------------------------


async def test_vague_opening_question_gets_exactly_one_clarifying_question():
    """LIVE (real LLM): the old behaviour returned a fixed 3-question
    list; intake now asks one targeted question at a time."""
    _user_id, token = await _make_chat_user()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as client:
        resp = await client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversationId": None, "text": "I have an Ayurvedic product", "jurisdiction": "india"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["clarifying_questions"], "a bare 'I have an Ayurvedic product' should not be answerable"
    assert len(body["clarifying_questions"]) == 1
    assert body["answer"] == ""


async def test_round_cap_forces_a_real_answer_with_the_best_effort_next_step():
    """LIVE (real LLM): with _INTAKE_ROUND_CAP rounds already spent, an
    equally vague message must NOT produce a further question - it gets a
    real answer, visibly labelled best-effort."""
    user_id, token = await _make_chat_user()

    async with AsyncSessionLocal() as session:
        conversation = Conversation(user_id=user_id, language="en")
        session.add(conversation)
        await session.flush()
        base = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(_INTAKE_ROUND_CAP):
            session.add(
                Message(
                    conversation_id=conversation.id,
                    created_at=base + timedelta(minutes=i),
                    role=MessageRole.assistant,
                    content=f"clarifying question {i}",
                    response_json={"clarifying_questions": [f"clarifying question {i}"]},
                )
            )
        await session.commit()
        conversation_id = str(conversation.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as client:
        resp = await client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "conversationId": conversation_id,
                "text": "I have an Ayurvedic product, can you help?",
                "jurisdiction": "india",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert not body["clarifying_questions"], "round cap spent - must not ask a sixth question"
    assert body["answer"], "capped intake must fall through to a real (best-effort) answer"
    assert body["next_steps"], "the best-effort notice is always prepended to next_steps"
    assert _BEST_EFFORT_FRAGMENT in body["next_steps"][0]

    async with AsyncSessionLocal() as session:
        stored = await session.execute(
            select(Message).where(
                Message.conversation_id == uuid.UUID(conversation_id),
                Message.role == MessageRole.assistant,
            )
        )
        assert len(stored.scalars().all()) == _INTAKE_ROUND_CAP + 1
