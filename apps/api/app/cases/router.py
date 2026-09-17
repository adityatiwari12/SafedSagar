"""Case queue - Facilitator/Legal Expert/Regulatory Expert, queue-scoped.

Reads Case rows (every answered chat turn - app/chat/router.py's
_create_case), not a live re-query - a reviewer sees exactly what the AI
produced, not a fresh retrieval that could differ.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.authz.constants import Permission, RoleName
from app.authz.service import AuthzContext, can_access_resource, require_permission
from app.cases.schemas import CaseOut, CloseCaseRequest, ReviewActionOut, ReviewActionRequest
from app.db.models import AuditLogEntry, Case, CaseQueue, CaseStatus, ExpertReview, ExpertReviewAction, User

router = APIRouter(prefix="/cases", tags=["cases"])

# Which queue each reviewer role's case.view_queue grant actually covers.
# A permission key alone (case.view_queue) doesn't say WHICH queue - this
# is the same kind of scope narrowing can_access_resource does for
# ownership, just keyed by role name instead of a resource column (spec
# Section 8's routing rule assigns the queue at Case-creation time; this
# is where a caller's role is matched back to the queue they may see).
_ROLE_QUEUE: dict[str, CaseQueue] = {
    RoleName.FACILITATOR: CaseQueue.ip,
    RoleName.LEGAL_EXPERT: CaseQueue.legal,
    RoleName.REGULATORY_EXPERT: CaseQueue.regulatory,
}


async def _caller_role_names(ctx: AuthzContext, db: AsyncSession) -> set[str]:
    from app.db.models import Role, UserRoleAssignment

    rows = await db.execute(
        select(Role.name).join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id).where(
            UserRoleAssignment.user_id == ctx.user.id
        )
    )
    return {r[0] for r in rows.all()}


async def _to_case_out(db: AsyncSession, case: Case) -> CaseOut:
    assigned = await db.get(User, case.assigned_to_user_id) if case.assigned_to_user_id else None
    requester = await db.get(User, case.user_id)
    answer = ""
    if case.conversation_id:
        from app.db.models import Message, MessageRole

        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == case.conversation_id, Message.role == MessageRole.assistant)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_assistant = msg_result.scalar_one_or_none()
        answer = last_assistant.content if last_assistant else ""

    return CaseOut(
        id=case.id,
        status=case.status.value,
        queue=case.queue.value if case.queue else None,
        risk_level=case.risk_level.value,
        question=case.question,
        answer=answer,
        reason=None,
        product_classification=case.product_classification,
        jurisdiction=case.jurisdiction,
        confidence_score=case.confidence_score,
        confidence_level=case.confidence_level,
        assigned_facilitator_email=assigned.email if assigned else None,
        user_email=requester.email if requester else "",
        created_at=case.created_at,
        closed_at=case.closed_at,
        resolution_summary=case.resolution_summary,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    status_filter: str | None = None,
    ctx: AuthzContext = Depends(require_permission(Permission.CASE_VIEW_QUEUE)),
    db: AsyncSession = Depends(get_db),
) -> list[CaseOut]:
    role_names = await _caller_role_names(ctx, db)
    allowed_queues = {_ROLE_QUEUE[r] for r in role_names if r in _ROLE_QUEUE}
    if not allowed_queues:
        # Holds case.view_queue but none of the known reviewer roles (e.g.
        # a future role added to the grant without a queue mapping here) -
        # fail closed, not open, to an empty-but-200 queue rather than
        # every case.
        return []

    stmt = select(Case).where(Case.queue.in_(allowed_queues)).order_by(Case.created_at.desc())
    if status_filter:
        stmt = stmt.where(Case.status == CaseStatus(status_filter))

    result = await db.execute(stmt)
    cases = list(result.scalars().all())
    return [await _to_case_out(db, c) for c in cases]


@router.post("/{case_id}/claim", response_model=CaseOut)
async def claim_case(
    case_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.CASE_ASSIGN)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.assigned_to_user_id = ctx.user.id
    case.status = CaseStatus.in_progress
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="case.claim",
            detail={"case_id": str(case.id)},
        )
    )
    await db.commit()
    await db.refresh(case)
    return await _to_case_out(db, case)


@router.post("/{case_id}/close", response_model=CaseOut)
async def close_case(
    case_id: uuid.UUID,
    payload: CloseCaseRequest,
    ctx: AuthzContext = Depends(require_permission(Permission.CASE_CLOSE)),
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.status = CaseStatus.closed
    case.closed_at = datetime.now(timezone.utc)
    case.resolution_summary = payload.resolution_summary
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="case.close",
            detail={"case_id": str(case.id), "resolution_summary": payload.resolution_summary},
        )
    )
    await db.commit()
    await db.refresh(case)
    return await _to_case_out(db, case)


@router.post("/{case_id}/review", response_model=ReviewActionOut)
async def review_case(
    case_id: uuid.UUID,
    payload: ReviewActionRequest,
    ctx: AuthzContext = Depends(require_permission(Permission.REVIEW_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> ReviewActionOut:
    """Record a reviewer action. Only the case's assigned reviewer may act
    on it (can_access_resource's ownership check via assigned_to_user_id) -
    holding review.approve at all is necessary but not sufficient (spec
    Section 5's can_perform_action distinction)."""
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not can_access_resource(ctx, case):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your assigned case")

    try:
        action = ExpertReviewAction(payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action") from exc

    role_names = await _caller_role_names(ctx, db)
    reviewer_role = next((r for r in role_names if r in _ROLE_QUEUE), "facilitator")

    review = ExpertReview(
        case_id=case.id,
        reviewer_user_id=ctx.user.id,
        reviewer_role=reviewer_role,
        action=action,
        notes=payload.notes,
        previous_state={"status": case.status.value},
    )
    db.add(review)
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="case.review",
            detail={"case_id": str(case.id), "review_action": action.value, "reviewer_role": reviewer_role},
        )
    )

    if action == ExpertReviewAction.escalate:
        case.status = CaseStatus.escalated
    elif action in (ExpertReviewAction.approve, ExpertReviewAction.reject, ExpertReviewAction.modify):
        case.status = CaseStatus.closed
        case.closed_at = datetime.now(timezone.utc)
    elif action == ExpertReviewAction.request_info:
        case.status = CaseStatus.awaiting_user_input

    review.new_state = {"status": case.status.value}
    await db.commit()
    await db.refresh(review)
    return ReviewActionOut(id=review.id, case_id=case.id, action=review.action.value, notes=review.notes, created_at=review.created_at)
