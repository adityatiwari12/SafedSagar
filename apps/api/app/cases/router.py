"""Escalation case queue - Facilitator/Regulatory Expert/Admin only.

Reads what app/query/router.py persisted (a snapshot of the graph's
output at escalation time) plus the conversation's question/answer
Messages. No live re-query - a facilitator reviews exactly what the AI
saw, not a fresh retrieval that could differ.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db, require_role
from app.cases.schemas import CaseOut, CloseCaseRequest
from app.db.models import Conversation, EscalationItem, EscalationStatus, Message, MessageRole, User

router = APIRouter(prefix="/cases", tags=["cases"])

CASE_ROLES = ("facilitator", "regulatory_expert", "admin")


async def _to_case_out(db: AsyncSession, item: EscalationItem) -> CaseOut:
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == item.conversation_id)
        .order_by(Message.created_at)
    )
    messages = list(messages_result.scalars().all())
    question = next((m.content for m in messages if m.role == MessageRole.user), "")
    answer = next((m.content for m in messages if m.role == MessageRole.assistant), "")

    conversation = await db.get(Conversation, item.conversation_id)
    conversation_user = await db.get(User, conversation.user_id) if conversation else None
    facilitator = (
        await db.get(User, item.assigned_facilitator_id) if item.assigned_facilitator_id else None
    )

    return CaseOut(
        id=item.id,
        status=item.status.value,
        question=question,
        answer=answer,
        reason=item.reason,
        product_classification=item.product_classification,
        jurisdiction=item.jurisdiction,
        confidence_score=item.confidence_score,
        confidence_level=item.confidence_level,
        assigned_facilitator_email=facilitator.email if facilitator else None,
        user_email=conversation_user.email if conversation_user else "",
        created_at=item.created_at,
        closed_at=item.closed_at,
        resolution_summary=item.resolution_summary,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    status_filter: str | None = None,
    _current_user: User = Depends(require_role(*CASE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[CaseOut]:
    stmt = select(EscalationItem).order_by(EscalationItem.created_at.desc())
    if status_filter:
        stmt = stmt.where(EscalationItem.status == EscalationStatus(status_filter))

    result = await db.execute(stmt)
    items = list(result.scalars().all())
    # item.conversation is lazy-loaded per access above; fine at this
    # queue's expected scale (a handful of open cases at a time for MVP).
    return [await _to_case_out(db, item) for item in items]


@router.post("/{case_id}/claim", response_model=CaseOut)
async def claim_case(
    case_id: uuid.UUID,
    current_user: User = Depends(require_role(*CASE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    item = await db.get(EscalationItem, case_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    item.assigned_facilitator_id = current_user.id
    item.status = EscalationStatus.in_progress
    await db.commit()
    await db.refresh(item)
    return await _to_case_out(db, item)


@router.post("/{case_id}/close", response_model=CaseOut)
async def close_case(
    case_id: uuid.UUID,
    payload: CloseCaseRequest,
    _current_user: User = Depends(require_role(*CASE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    item = await db.get(EscalationItem, case_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    item.status = EscalationStatus.closed
    item.closed_at = datetime.now(timezone.utc)
    item.resolution_summary = payload.resolution_summary
    await db.commit()
    await db.refresh(item)
    return await _to_case_out(db, item)
