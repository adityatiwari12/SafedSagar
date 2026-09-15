"""The /chat and /escalations endpoints - the contract apps/web's
realChatApi.ts already expects. Wraps the same graph app/query/router.py
uses, adding: conversation continuity (a conversationId thread), a single
round of clarifying questions when classify_product can't tell what the
product is, and citation enrichment (title/source_url) from the chunks
the graph actually retrieved.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_db
from app.chat.schemas import (
    AbsTkFlagsOut,
    ChatTurnRequest,
    ChatTurnResponse,
    ClassificationOut,
    CitationOut,
    EscalateRequest,
    EscalateResponse,
)
from app.db.models import (
    Conversation,
    EscalationItem,
    EscalationStatus,
    Message,
    MessageRole,
    User,
)
from app.graph.graph import run_classification, run_graph, run_remaining
from app.graph.state import GraphState

router = APIRouter(tags=["chat"])

_VALID_JURISDICTIONS = {"india", "international"}

# Asked once, only on a fresh (non-clarification-answer) turn, when
# classify_product can't determine the product category from the text
# alone. Static wording (the fixed set a user answers once) rather than
# LLM-generated questions - classify_product's job is deciding WHETHER
# to ask, not composing bespoke question text.
CLARIFYING_QUESTIONS = [
    "Is this a classical Ayurvedic formulation, a proprietary Ayurvedic medicine, or a new composition?",
    "Is the intended use primarily as a drug/medicine, food (Ayurveda Aahara), or cosmetic?",
    "What do you mainly need help with - patent, trademark, GI, ABS/biodiversity, or regulatory compliance?",
]


async def _get_or_create_conversation(
    db: AsyncSession, user: User, conversation_id: str | None
) -> Conversation:
    if conversation_id:
        try:
            existing = await db.get(Conversation, uuid.UUID(conversation_id))
        except ValueError:
            existing = None
        if existing is not None:
            if existing.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation")
            return existing

    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.flush()
    return conversation


# How many prior turns to fold into the graph's question text. Bounded so
# a long conversation doesn't blow up the prompt - a follow-up almost
# always only needs the last exchange or two to resolve "it"/"this".
_HISTORY_TURN_LIMIT = 3


async def _build_history_text(
    db: AsyncSession, conversation: Conversation
) -> str | None:
    """Prior turns as plain "Speaker: text" lines, or None for a fresh
    conversation.

    Without conversation history reaching the graph at all, every /chat
    call was a fully independent run_graph() invocation seeing only the
    latest message - a follow-up like "Can I patent it?" had no idea what
    "it" was. Verified live (2026-09-15): asking about a specific
    Ashwagandha+Brahmi formulation in turn 1, then "Can I patent it?" in
    turn 2, produced a generic non-answer about industrial application
    with no connection to the actual product.

    Kept as a plain transcript (no instructions baked in) rather than the
    single wrapped-question string this used to build: classify_product/
    route_jurisdiction/route_ip_type/retrieve now get condense_query's
    standalone rewrite instead of this raw transcript, and reason_and_cite
    builds its own history section from this field directly - each node
    gets what it actually needs instead of everything getting the same
    instruction-laden blob.
    """
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(_HISTORY_TURN_LIMIT * 2)
    )
    prior_messages = list(reversed(result.scalars().all()))
    if not prior_messages:
        return None

    lines = []
    for m in prior_messages:
        speaker = "User" if m.role == MessageRole.user else "Assistant"
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)


def _enrich_citations(state: GraphState) -> list[CitationOut]:
    chunks_by_key = {
        (c["doc_id"], c["section_or_article"]): c for c in state.get("reranked_chunks", [])
    }
    out = []
    for citation in state.get("validated_citations", []):
        key = (citation["doc_id"], citation["section_or_article"])
        chunk = chunks_by_key.get(key)
        out.append(
            CitationOut(
                doc_id=citation["doc_id"],
                title=chunk["title"] if chunk else citation["doc_id"],
                section_or_article=citation["section_or_article"],
                source_url=chunk["source_url"] if chunk else None,
            )
        )
    return out


def _abs_tk_flags(state: GraphState) -> AbsTkFlagsOut | None:
    ip_types = state.get("ip_types", [])
    biological_resource_likely = "access_and_benefit_sharing" in ip_types
    traditional_knowledge_likely = any(
        "traditional knowledge" in c["source_text"].lower() for c in state.get("reranked_chunks", [])
    )
    if not biological_resource_likely and not traditional_knowledge_likely:
        return None

    if biological_resource_likely and traditional_knowledge_likely:
        note = (
            "Biological resource + traditional knowledge indicators present. Consider NBA "
            "ABS approval and TKDL prior-art awareness."
        )
    elif biological_resource_likely:
        note = "ABS pathway may be applicable - confirm biological-resource sourcing."
    else:
        note = "Possible traditional-knowledge overlap - TKDL prior-art awareness recommended."

    return AbsTkFlagsOut(
        biological_resource_likely=biological_resource_likely,
        traditional_knowledge_likely=traditional_knowledge_likely,
        note=note,
    )


@router.post("/chat", response_model=ChatTurnResponse)
async def chat(
    payload: ChatTurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatTurnResponse:
    jurisdiction = payload.jurisdiction if payload.jurisdiction in _VALID_JURISDICTIONS else None
    conversation = await _get_or_create_conversation(db, current_user, payload.conversationId)

    # Must run BEFORE adding this turn's Message below - autoflush would
    # otherwise flush that pending insert first and the "prior messages"
    # query would see (and duplicate) the current turn.
    history_text = await _build_history_text(db, conversation)

    db.add(Message(conversation_id=conversation.id, role=MessageRole.user, content=payload.text))

    # Only offer clarification on a fresh attempt - once the user has
    # answered (frontend sends `answers` on that round), never ask again,
    # even if still unclear: one round max (CLAUDE.md - no unnecessary
    # questions).
    is_clarification_answer = bool(payload.answers)

    if not is_clarification_answer:
        # Classify first, cheaply - condense_query + classify_product only,
        # no retrieval or reasoning yet. Previously this ran the FULL graph
        # (including the slow reason_and_cite LLM call) just to check
        # product_classification, discarding a real answer whenever it came
        # back "unclear".
        classify_state = await run_classification(payload.text, jurisdiction, None, history_text=history_text)
        if classify_state.get("product_classification") == "unclear":
            await db.commit()
            return ChatTurnResponse(
                conversationId=str(conversation.id),
                clarifying_questions=CLARIFYING_QUESTIONS,
                classification=ClassificationOut(product_type="unknown", ip_type="unknown"),
                jurisdiction=classify_state.get("jurisdiction") or payload.jurisdiction,
                answer="",
                citations=[],
                confidence=classify_state.get("confidence_score", 0.0),
                confidence_band="low",
                escalate_recommended=False,
            )
        state = await run_remaining(classify_state)
    else:
        state = await run_graph(payload.text, jurisdiction, None, history_text=history_text)

    db.add(Message(conversation_id=conversation.id, role=MessageRole.assistant, content=state.get("answer", "")))

    if state.get("escalate"):
        db.add(
            EscalationItem(
                conversation_id=conversation.id,
                status=EscalationStatus.open,
                reason=state.get("escalation_reason"),
                product_classification=state.get("product_classification"),
                jurisdiction=state.get("jurisdiction"),
                confidence_score=state.get("confidence_score"),
                confidence_level=state.get("confidence_level"),
            )
        )

    await db.commit()

    ip_types = state.get("ip_types", [])
    return ChatTurnResponse(
        conversationId=str(conversation.id),
        classification=ClassificationOut(
            product_type=state.get("product_classification", "unclear"),
            ip_type=", ".join(ip_types) if ip_types else "unknown",
        ),
        jurisdiction=state.get("jurisdiction") or payload.jurisdiction,
        answer=state.get("answer", ""),
        citations=_enrich_citations(state),
        confidence=state.get("confidence_score", 0.0),
        confidence_band=state.get("confidence_level", "low"),
        escalate_recommended=state.get("escalate", False),
        next_steps=state.get("next_steps") or None,
        abs_tk_flags=_abs_tk_flags(state),
    )


@router.post("/escalations", response_model=EscalateResponse)
async def create_escalation(
    payload: EscalateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EscalateResponse:
    """User-initiated escalation (the Escalate button), independent of
    escalate_if_needed's automatic decision - always creates a fresh open
    case for the conversation's latest turn."""
    try:
        conversation_uuid = uuid.UUID(payload.conversationId)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversationId") from exc

    conversation = await db.get(Conversation, conversation_uuid)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    item = EscalationItem(
        conversation_id=conversation.id,
        status=EscalationStatus.open,
        reason="User requested escalation to a human facilitator.",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return EscalateResponse(escalation_id=str(item.id))
