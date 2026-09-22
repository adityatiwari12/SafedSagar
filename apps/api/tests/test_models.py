"""Insert-and-read-back tests for each ORM model.

Rows are inserted in FK-respecting order: User first (referenced by
Conversation, EscalationItem, and AuditLogEntry), then Conversation
(referenced by Message and EscalationItem), then Message.
SourceDocument has no FKs and is inserted independently.
"""

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import (
    AuditLogEntry,
    Conversation,
    EscalationItem,
    EscalationStatus,
    Jurisdiction,
    Message,
    MessageRole,
    SourceDocument,
    User,
    UserRole,
)


@pytest.mark.asyncio
async def test_user_round_trip():
    unique_email = f"user-{uuid.uuid4()}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            email=unique_email,
            hashed_password="hashed-secret",
            role=UserRole.user,
            jurisdiction_preference="india",
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    async with AsyncSessionLocal() as session:
        fetched = await session.get(User, user_id)
        assert fetched is not None
        assert fetched.email == unique_email
        assert fetched.hashed_password == "hashed-secret"
        assert fetched.role == UserRole.user
        assert fetched.jurisdiction_preference == "india"
        assert isinstance(fetched.created_at, datetime)


@pytest.mark.asyncio
async def test_conversation_message_escalation_and_audit_log_round_trip():
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"facilitator-{uuid.uuid4()}@example.com",
            hashed_password="hashed-secret",
            role=UserRole.facilitator,
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    async with AsyncSessionLocal() as session:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        await session.commit()
        conversation_id = conversation.id

    async with AsyncSessionLocal() as session:
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.user,
            content="What is the term for a design registration in India?",
        )
        session.add(message)
        await session.commit()
        message_id = message.id

    async with AsyncSessionLocal() as session:
        escalation = EscalationItem(
            conversation_id=conversation_id,
            status=EscalationStatus.open,
            assigned_facilitator_id=user_id,
        )
        session.add(escalation)
        await session.commit()
        escalation_id = escalation.id

    async with AsyncSessionLocal() as session:
        audit_entry = AuditLogEntry(
            actor_user_id=user_id,
            action="escalation.created",
            detail={"escalation_id": str(escalation_id)},
        )
        session.add(audit_entry)
        await session.commit()
        audit_id = audit_entry.id

    async with AsyncSessionLocal() as session:
        fetched_conversation = await session.get(Conversation, conversation_id)
        assert fetched_conversation is not None
        assert fetched_conversation.user_id == user_id
        assert isinstance(fetched_conversation.created_at, datetime)

        fetched_message = await session.get(Message, message_id)
        assert fetched_message is not None
        assert fetched_message.conversation_id == conversation_id
        assert fetched_message.role == MessageRole.user
        assert (
            fetched_message.content
            == "What is the term for a design registration in India?"
        )

        fetched_escalation = await session.get(EscalationItem, escalation_id)
        assert fetched_escalation is not None
        assert fetched_escalation.conversation_id == conversation_id
        assert fetched_escalation.status == EscalationStatus.open
        assert fetched_escalation.assigned_facilitator_id == user_id
        assert fetched_escalation.closed_at is None

        fetched_audit = await session.get(AuditLogEntry, audit_id)
        assert fetched_audit is not None
        assert fetched_audit.actor_user_id == user_id
        assert fetched_audit.action == "escalation.created"
        assert fetched_audit.detail == {"escalation_id": str(escalation_id)}


@pytest.mark.asyncio
async def test_case_and_expert_review_round_trip():
    from app.db.models import (
        Case, CaseQueue, CaseRiskLevel, CaseStatus, ExpertReview, ExpertReviewAction,
        User, UserRole,
    )
    from app.auth.security import hash_password

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"case-model-{uuid.uuid4()}@example.test",
            hashed_password=hash_password("testpass123"),
            role=UserRole.user,
        )
        session.add(user)
        await session.flush()

        case = Case(
            user_id=user.id,
            question="Can I patent this?",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=CaseQueue.ip,
        )
        session.add(case)
        await session.flush()

        review = ExpertReview(
            case_id=case.id,
            reviewer_user_id=user.id,
            reviewer_role="facilitator",
            action=ExpertReviewAction.approve,
            notes="Looks right.",
        )
        session.add(review)
        await session.commit()
        await session.refresh(case)
        await session.refresh(review)

        assert case.status == CaseStatus.escalated
        assert case.queue == CaseQueue.ip
        assert review.case_id == case.id
        assert review.action == ExpertReviewAction.approve


@pytest.mark.asyncio
async def test_source_document_round_trip():
    # doc_id is namespaced "test-fixture-*", not a real-corpus-shaped id
    # (e.g. "ipindia-patents-act-1970-<hex>") - the row is also deleted at
    # the end of the test. A prior version used a real-looking doc_id and
    # never cleaned it up: it accumulated one stray row in the shared dev
    # Postgres on every test run (51 and counting by the time this was
    # caught), which the knowledge graph's fragment-canonicalization logic
    # then picked up as if it were real corpus data on every rebuild.
    doc_id = f"test-fixture-source-document-{uuid.uuid4().hex[:8]}"
    chunk_id = f"{doc_id}#s3p"
    async with AsyncSessionLocal() as session:
        doc = SourceDocument(
            id=chunk_id,
            doc_id=doc_id,
            title="The Patents Act, 1970 - Section 3(p)",
            authority="Office of the Controller General of Patents, Designs & Trade Marks",
            jurisdiction=Jurisdiction.india,
            doc_type="statute",
            effective_date=date(1972, 4, 20),
            version="2024-consolidated",
            section_or_article="Section 3(p)",
            source_url="https://ipindia.gov.in/patents-act.htm",
            last_verified_date=date(2026, 1, 1),
            source_text="An invention which, in effect, is traditional knowledge...",
        )
        session.add(doc)
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            fetched = await session.get(SourceDocument, chunk_id)
            assert fetched is not None
            assert fetched.doc_id == doc_id
            assert fetched.title == "The Patents Act, 1970 - Section 3(p)"
            assert fetched.jurisdiction == Jurisdiction.india
            assert fetched.doc_type == "statute"
    finally:
        async with AsyncSessionLocal() as session:
            row = await session.get(SourceDocument, chunk_id)
            if row is not None:
                await session.delete(row)
                await session.commit()
        assert fetched.effective_date == date(1972, 4, 20)
        assert fetched.version == "2024-consolidated"
        assert fetched.section_or_article == "Section 3(p)"
        assert fetched.source_url == "https://ipindia.gov.in/patents-act.htm"
        assert fetched.last_verified_date == date(2026, 1, 1)
        assert "traditional knowledge" in fetched.source_text
