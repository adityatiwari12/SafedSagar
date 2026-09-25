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
from app.authz.service import AuthzContext, can_access_resource, has_any_grant, load_authz_context, require_permission
from app.cases.schemas import (
    CaseMessageCreate, CaseMessageOut, CaseOut, CloseCaseRequest, ReviewActionOut, ReviewActionRequest,
)
from app.db.models import (
    AuditLogEntry, Case, CaseMessage, CaseMessageKind, CaseQueue, CaseStatus, ExpertReview, ExpertReviewAction,
    Product, User,
)

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

# Which specific permission gates each /review action. request_info has no
# dedicated permission key in app.authz.constants - treated as covered by
# REVIEW_APPROVE (every reviewer role that can approve can also ask for
# more info).
_ACTION_PERMISSION: dict[ExpertReviewAction, str] = {
    ExpertReviewAction.approve: Permission.REVIEW_APPROVE,
    ExpertReviewAction.modify: Permission.REVIEW_MODIFY,
    ExpertReviewAction.reject: Permission.REVIEW_REJECT,
    ExpertReviewAction.escalate: Permission.REVIEW_ESCALATE,
    ExpertReviewAction.request_info: Permission.REVIEW_APPROVE,
}

# Which CaseMessageKind values each side of a case's message thread may
# post. Server-enforced (never trust the client to self-limit) - a plain
# user may ask a follow-up or answer a request for info, but only the
# assigned reviewer may ask for more info or send the substantive
# "expert_response" (spec Phase 23's expert-escalation loop).
_USER_ALLOWED_MESSAGE_KINDS = {CaseMessageKind.note, CaseMessageKind.info_response}
_REVIEWER_ALLOWED_MESSAGE_KINDS = {
    CaseMessageKind.note, CaseMessageKind.info_request, CaseMessageKind.expert_response,
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

    product_name = None
    if case.product_id is not None:
        product = await db.get(Product, case.product_id)
        product_name = product.name if product else None

    return CaseOut(
        id=case.id,
        status=case.status.value,
        queue=case.queue.value if case.queue else None,
        risk_level=case.risk_level.value,
        question=case.question,
        answer=answer,
        reason=None,
        product_classification=case.product_classification,
        ip_types=case.ip_types,
        jurisdiction=case.jurisdiction,
        confidence_score=case.confidence_score,
        confidence_level=case.confidence_level,
        assigned_facilitator_email=assigned.email if assigned else None,
        user_email=requester.email if requester else "",
        created_at=case.created_at,
        closed_at=case.closed_at,
        resolution_summary=case.resolution_summary,
        product_id=case.product_id,
        product_name=product_name,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    status_filter: str | None = None,
    ctx: AuthzContext = Depends(load_authz_context),
    db: AsyncSession = Depends(get_db),
) -> list[CaseOut]:
    """Two different views behind one endpoint, picked by which grant the
    caller actually has - a reviewer (case.view_queue) sees their queue;
    a plain user (case.view_own, already granted to RoleName.USER but
    never read by any endpoint until now) sees their own submitted
    cases. Neither grant -> 403, not an empty queue."""
    is_reviewer = has_any_grant(ctx, Permission.CASE_VIEW_QUEUE)
    is_own_viewer = has_any_grant(ctx, Permission.CASE_VIEW_OWN)
    if not is_reviewer and not is_own_viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {Permission.CASE_VIEW_QUEUE} or {Permission.CASE_VIEW_OWN}",
        )

    if is_reviewer:
        role_names = await _caller_role_names(ctx, db)
        allowed_queues = {_ROLE_QUEUE[r] for r in role_names if r in _ROLE_QUEUE}
        if not allowed_queues:
            # Holds case.view_queue but none of the known reviewer roles
            # (e.g. a future role added to the grant without a queue
            # mapping here) - fail closed, not open, to an empty-but-200
            # queue rather than every case.
            return []
        stmt = select(Case).where(Case.queue.in_(allowed_queues)).order_by(Case.created_at.desc())
    else:
        stmt = select(Case).where(Case.user_id == ctx.user.id).order_by(Case.created_at.desc())

    if status_filter:
        try:
            stmt = stmt.where(Case.status == CaseStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status_filter")

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

    role_names = await _caller_role_names(ctx, db)
    allowed_queues = {_ROLE_QUEUE[r] for r in role_names if r in _ROLE_QUEUE}
    if case.queue not in allowed_queues:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Case not in your queue")
    if case.assigned_to_user_id is not None and case.assigned_to_user_id != ctx.user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case already claimed by another reviewer")

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
    if not can_access_resource(ctx, case):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your assigned case")

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
    ctx: AuthzContext = Depends(require_permission(Permission.REVIEW_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> ReviewActionOut:
    """Record a reviewer action. Only the case's assigned reviewer may act
    on it (can_access_resource's ownership check via assigned_to_user_id) -
    holding review.approve at all is necessary but not sufficient (spec
    Section 5's can_perform_action distinction). The route-entry dependency
    only guards review.view (the broadest grant every reviewer role holds);
    the specific permission for the requested action is checked below, since
    a single action (e.g. escalate) may not be granted to every role that
    can otherwise review (e.g. legal_expert has no higher tier to escalate
    to)."""
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not can_access_resource(ctx, case):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your assigned case")

    try:
        action = ExpertReviewAction(payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action") from exc

    required = _ACTION_PERMISSION[action]
    if not has_any_grant(ctx, required):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {required}")

    role_names = await _caller_role_names(ctx, db)
    reviewer_role = next((r for r in sorted(role_names) if r in _ROLE_QUEUE), "facilitator")

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


def _case_message_side(ctx: AuthzContext, case: Case) -> str | None:
    """Which side of a case's message thread the caller is on: its own
    user, or its assigned reviewer (the same ownership check claim/close/
    review already use - can_access_resource's assigned_to_user_id match,
    NOT every reviewer who could see the case in a queue listing). Neither
    -> None, the caller gets a 403.

    Reviewer is checked first: the unlikely case where the same account
    is both the case's owner and its assigned reviewer should get the
    reviewer's (strictly broader) kind set, not silently fall back to the
    user's narrower one.
    """
    if has_any_grant(ctx, Permission.CASE_VIEW_QUEUE) and can_access_resource(ctx, case):
        return "reviewer"
    if case.user_id == ctx.user.id and has_any_grant(ctx, Permission.CASE_VIEW_OWN):
        return "user"
    return None


async def _to_case_message_out(db: AsyncSession, message: CaseMessage) -> CaseMessageOut:
    author = await db.get(User, message.author_user_id)
    return CaseMessageOut(
        id=message.id,
        case_id=message.case_id,
        author_user_id=message.author_user_id,
        author_email=author.email if author else "",
        author_role=message.author_role,
        body=message.body,
        kind=message.kind.value,
        created_at=message.created_at,
    )


@router.get("/{case_id}/messages", response_model=list[CaseMessageOut])
async def list_case_messages(
    case_id: uuid.UUID,
    ctx: AuthzContext = Depends(load_authz_context),
    db: AsyncSession = Depends(get_db),
) -> list[CaseMessageOut]:
    """Full message thread for a case, oldest first. `require_permission`
    only expresses a single permission key; a user (case.view_own) and a
    reviewer (case.view_queue) both hit this same endpoint, so the OR is
    checked inline via `_case_message_side`, the same way list_cases/
    review_case already do custom checks past the route-entry dependency."""
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if _case_message_side(ctx, case) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this case")

    result = await db.execute(
        select(CaseMessage).where(CaseMessage.case_id == case_id).order_by(CaseMessage.created_at.asc())
    )
    messages = list(result.scalars().all())
    return [await _to_case_message_out(db, m) for m in messages]


@router.post("/{case_id}/messages", response_model=CaseMessageOut, status_code=status.HTTP_201_CREATED)
async def create_case_message(
    case_id: uuid.UUID,
    payload: CaseMessageCreate,
    ctx: AuthzContext = Depends(load_authz_context),
    db: AsyncSession = Depends(get_db),
) -> CaseMessageOut:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    side = _case_message_side(ctx, case)
    if side is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this case")

    try:
        kind = CaseMessageKind(payload.kind)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kind") from exc

    allowed_kinds = _REVIEWER_ALLOWED_MESSAGE_KINDS if side == "reviewer" else _USER_ALLOWED_MESSAGE_KINDS
    if kind not in allowed_kinds:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"A {side} may not post a '{kind.value}' message",
        )

    if side == "reviewer":
        role_names = await _caller_role_names(ctx, db)
        author_role = next((r for r in sorted(role_names) if r in _ROLE_QUEUE), "facilitator")
    else:
        author_role = "user"

    message = CaseMessage(
        case_id=case.id,
        author_user_id=ctx.user.id,
        author_role=author_role,
        body=payload.body,
        kind=kind,
    )
    db.add(message)

    # request_info/info_response are the one real state transition this
    # thread drives (spec's "additional information if required" step) -
    # everything else (including expert_response) leaves case.status
    # alone; closing stays close_case's separate, explicit action.
    if kind == CaseMessageKind.info_request:
        case.status = CaseStatus.awaiting_user_input
    elif kind == CaseMessageKind.info_response and case.status == CaseStatus.awaiting_user_input:
        if case.assigned_to_user_id is not None:
            case.status = CaseStatus.in_progress

    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="case.message",
            detail={"case_id": str(case.id), "kind": kind.value},
        )
    )

    await db.commit()
    await db.refresh(message)
    return await _to_case_message_out(db, message)
