"""The /chat and /escalations endpoints - the contract apps/web's
realChatApi.ts already expects. Wraps the same graph app/query/router.py
uses, adding: conversation continuity (a conversationId thread), a single
round of clarifying questions when classify_product can't tell what the
product is, and citation enrichment (title/source_url) from the chunks
the graph actually retrieved.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_db, resolve_user_from_token
from app.cases.service import derive_case_outcome
from app.chat.schemas import (
    AbsTkFlagsOut,
    ChatTurnRequest,
    ChatTurnResponse,
    ClassificationOut,
    CitationOut,
    ConversationMessageOut,
    ConversationSummaryOut,
    EscalateRequest,
    EscalateResponse,
)
from app.db.base import AsyncSessionLocal
from app.db.models import (
    AuditLogEntry,
    Case,
    CaseQueue,
    CaseRiskLevel,
    CaseStatus,
    Conversation,
    EscalationItem,
    Message,
    MessageRole,
    User,
)
from app.graph.graph import NodeDoneCallback, run_classification, run_graph, run_remaining
from app.graph.state import GraphState
from app.translation.languages import DEFAULT_LANGUAGE, is_supported
from app.translation.translation_service import get_translation_service

router = APIRouter(tags=["chat"])

# Maps a graph node's function name (or the "language" pseudo-step emitted
# before the graph even runs, once translation-detection resolves the
# target language) to the JourneyStepper step it represents in the web UI.
# Several nodes collapse onto the same UI step (e.g. retrieve+rerank are
# both "need") - the WebSocket handler dedupes so each step frame is sent
# once per turn regardless of how many nodes map onto it.
NODE_TO_STEP = {
    "language": "language",
    "condense_query": "understand",
    "classify_product": "classify",
    "route_jurisdiction": "jurisdiction",
    "route_ip_type": "need",
    "retrieve": "need",
    "rerank": "need",
    "reason_and_cite": "answer",
    "validate_citations": "answer",
    "score_confidence": "action",
    "escalate_if_needed": "action",
}

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

_OUT_OF_SCOPE_MESSAGE = (
    "This assistant only covers Ayurveda intellectual-property, biodiversity/ABS, and "
    "regulatory questions. Please ask something in that scope, or rephrase your question "
    "to connect it to an Ayurvedic product, formulation, or filing."
)


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        await value


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


def _localize_list(
    translation_service, texts: list[str], target_language: str
) -> tuple[list[str], str, bool]:
    """Translate each string independently, returning ("failed" overall
    status if any one did) - used for the static CLARIFYING_QUESTIONS list,
    which has no single canonical answer to fall back to as a whole."""
    if target_language == DEFAULT_LANGUAGE:
        return texts, "not_needed", False

    localized = []
    any_unverified = False
    for text in texts:
        outcome = translation_service.resolve_outgoing(text, target_language)
        localized.append(outcome.text)
        if outcome.translation_status not in ("verified", "not_needed"):
            any_unverified = True
    return localized, ("failed" if any_unverified else "verified"), any_unverified


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


async def _create_case(
    db: AsyncSession,
    *,
    current_user: User,
    conversation: Conversation,
    question: str,
    target_language: str,
    state: GraphState,
    response: "ChatTurnResponse",
) -> Case:
    """Persist a Case for this turn - every answered turn (including an
    out-of-scope refusal), never a clarifying-question round (spec
    Section 6, Build order item 2: "every question becomes a Case row" -
    scoped here to turns that actually reached an answer, since a
    clarifying round isn't yet an answer to assess)."""
    outcome = derive_case_outcome(
        escalate=state.get("escalate", False),
        confidence_level=response.confidence_band,
        product_classification=response.classification.product_type,
        ip_types=state.get("ip_types", []),
        abs_tk_flags=response.abs_tk_flags.model_dump() if response.abs_tk_flags else None,
    )
    case = Case(
        user_id=current_user.id,
        conversation_id=conversation.id,
        question=question,
        language=target_language,
        product_classification=response.classification.product_type,
        ip_types=state.get("ip_types", []),
        jurisdiction=response.jurisdiction,
        abs_tk_flags=response.abs_tk_flags.model_dump() if response.abs_tk_flags else None,
        ai_analysis={
            "classification": response.classification.model_dump(),
            "next_steps": response.next_steps,
            "timing_ms": response.timing_ms,
        },
        citations=[c.model_dump() for c in response.citations],
        confidence_score=response.confidence,
        confidence_level=response.confidence_band,
        risk_level=outcome.risk_level,
        status=outcome.status,
        queue=outcome.queue,
    )
    db.add(case)
    return case


async def _process_chat_turn(
    payload: ChatTurnRequest,
    current_user: User,
    db: AsyncSession,
    on_node_done: NodeDoneCallback | None = None,
) -> ChatTurnResponse:
    """Core /chat business logic, shared by the REST endpoint (below) and
    the /chat/ws WebSocket endpoint. on_node_done is None for REST callers
    (no behavior change); the WebSocket endpoint passes a callback that
    streams {"type": "step", "step": ...} frames to the browser as the
    graph actually progresses, via NODE_TO_STEP above.
    """
    jurisdiction = payload.jurisdiction if payload.jurisdiction in _VALID_JURISDICTIONS else None
    conversation = await _get_or_create_conversation(db, current_user, payload.conversationId)

    # Multilingual entry point (task Section 6/9): detect the query's
    # language for INTERPRETATION (translating the input to the canonical
    # English the rest of the pipeline expects) - falling back to the
    # conversation's established language, then the request's declared
    # `language`, on low-confidence detection.
    translation_service = get_translation_service()
    requested_language = payload.language if is_supported(payload.language) else None
    ui_language = conversation.language or requested_language
    incoming = translation_service.resolve_incoming(payload.text, ui_language)

    # Output language is the explicit UI selection, not auto-detection of
    # what the user happened to type it in - picking Hindi from the
    # dropdown must mean Hindi replies even if this particular message was
    # typed in English. Falls back to the conversation's established
    # language, then the detected input language, only when the request
    # didn't declare one at all.
    target_language = (
        requested_language
        or conversation.language
        or (incoming.detected_language if is_supported(incoming.detected_language) else DEFAULT_LANGUAGE)
    )
    conversation.language = target_language
    canonical_text = incoming.canonical_query

    if on_node_done is not None:
        await _maybe_await(on_node_done("language", {}))

    # Must run BEFORE adding this turn's Message below - autoflush would
    # otherwise flush that pending insert first and the "prior messages"
    # query would see (and duplicate) the current turn.
    history_text = await _build_history_text(db, conversation)

    # Stored content is always the canonical English text - history-folding
    # and the graph itself stay English-only regardless of the user's
    # language, per task Section 4 ("do NOT create separate knowledge
    # bases per language"). `language` on the row records what the turn
    # was actually conducted in.
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=canonical_text,
            display_text=payload.text,
            language=target_language,
        )
    )

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
        classify_state = await run_classification(
            canonical_text, jurisdiction, None, history_text=history_text, on_node_done=on_node_done
        )
        if classify_state.get("product_classification") == "out_of_scope":
            # Not "unclear" (ambiguous but on-topic) - the question isn't
            # about Ayurveda IP/biodiversity/regulatory matters at all.
            # Refuse immediately rather than asking clarifying questions or
            # running jurisdiction/retrieval/reasoning on it.
            localized_refusal, refusal_status, refusal_review = _localize_list(
                translation_service, [_OUT_OF_SCOPE_MESSAGE], target_language
            )
            response = ChatTurnResponse(
                conversationId=str(conversation.id),
                classification=ClassificationOut(product_type="out_of_scope", ip_type="out_of_scope"),
                jurisdiction=classify_state.get("jurisdiction") or payload.jurisdiction,
                answer=localized_refusal[0],
                citations=[],
                confidence=0.0,
                confidence_band="low",
                escalate_recommended=False,
                detected_language=incoming.detected_language,
                canonical_query=canonical_text,
                canonical_answer=_OUT_OF_SCOPE_MESSAGE,
                translation_status=refusal_status,
                needs_human_review=refusal_review,
                timing_ms=classify_state.get("node_timings"),
            )
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=_OUT_OF_SCOPE_MESSAGE,
                    display_text=localized_refusal[0],
                    response_json=response.model_dump(),
                    language=target_language,
                )
            )
            await _create_case(
                db,
                current_user=current_user,
                conversation=conversation,
                question=canonical_text,
                target_language=target_language,
                state=classify_state,
                response=response,
            )
            await db.commit()
            return response
        if classify_state.get("product_classification") == "unclear":
            localized_questions, cq_status, cq_review = _localize_list(
                translation_service, CLARIFYING_QUESTIONS, target_language
            )
            response = ChatTurnResponse(
                conversationId=str(conversation.id),
                clarifying_questions=localized_questions,
                classification=ClassificationOut(product_type="unknown", ip_type="unknown"),
                jurisdiction=classify_state.get("jurisdiction") or payload.jurisdiction,
                answer="",
                citations=[],
                confidence=classify_state.get("confidence_score", 0.0),
                confidence_band="low",
                escalate_recommended=False,
                detected_language=incoming.detected_language,
                canonical_query=canonical_text,
                canonical_answer=None,
                translation_status=cq_status,
                needs_human_review=cq_review,
                timing_ms=classify_state.get("node_timings"),
            )
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content="\n".join(CLARIFYING_QUESTIONS),
                    display_text="\n".join(localized_questions),
                    response_json=response.model_dump(),
                    language=target_language,
                )
            )
            await db.commit()
            return response
        state = await run_remaining(classify_state, on_node_done=on_node_done)
    else:
        state = await run_graph(
            canonical_text, jurisdiction, None, history_text=history_text, on_node_done=on_node_done
        )

    # Second (and last - one round max, same as the product-classification
    # gate above) chance to ask instead of guess: reason_and_cite flags this
    # when the question is real but too under-specified to answer precisely
    # (e.g. "Indian medicinal plants" naming no plant), rather than always
    # forcing out a generic best-effort answer.
    dynamic_clarifying_question = state.get("clarifying_question") if not is_clarification_answer else None
    if dynamic_clarifying_question:
        localized_questions, cq_status, cq_review = _localize_list(
            translation_service, [dynamic_clarifying_question], target_language
        )
        response = ChatTurnResponse(
            conversationId=str(conversation.id),
            clarifying_questions=localized_questions,
            classification=ClassificationOut(
                product_type=state.get("product_classification", "unclear"),
                ip_type=", ".join(state.get("ip_types", [])) or "unknown",
            ),
            jurisdiction=state.get("jurisdiction") or payload.jurisdiction,
            answer="",
            citations=[],
            confidence=state.get("confidence_score", 0.0),
            confidence_band="low",
            escalate_recommended=False,
            detected_language=incoming.detected_language,
            canonical_query=canonical_text,
            canonical_answer=None,
            translation_status=cq_status,
            needs_human_review=cq_review,
            timing_ms=state.get("node_timings"),
        )
        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.assistant,
                content=dynamic_clarifying_question,
                display_text=localized_questions[0],
                response_json=response.model_dump(),
                language=target_language,
            )
        )
        await db.commit()
        return response

    canonical_answer = state.get("answer", "")
    outgoing = translation_service.resolve_outgoing(canonical_answer, target_language)

    ip_types = state.get("ip_types", [])
    response = ChatTurnResponse(
        conversationId=str(conversation.id),
        classification=ClassificationOut(
            product_type=state.get("product_classification", "unclear"),
            ip_type=", ".join(ip_types) if ip_types else "unknown",
        ),
        jurisdiction=state.get("jurisdiction") or payload.jurisdiction,
        answer=outgoing.text,
        citations=_enrich_citations(state),
        confidence=state.get("confidence_score", 0.0),
        confidence_band=state.get("confidence_level", "low"),
        escalate_recommended=state.get("escalate", False),
        next_steps=state.get("next_steps") or None,
        abs_tk_flags=_abs_tk_flags(state),
        detected_language=incoming.detected_language,
        canonical_query=canonical_text,
        canonical_answer=canonical_answer,
        translation_status=outgoing.translation_status,
        needs_human_review=outgoing.needs_human_review,
        timing_ms=state.get("node_timings"),
    )

    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=canonical_answer,
            display_text=outgoing.text,
            response_json=response.model_dump(),
            language=target_language,
        )
    )

    await _create_case(
        db,
        current_user=current_user,
        conversation=conversation,
        question=canonical_text,
        target_language=target_language,
        state=state,
        response=response,
    )

    await db.commit()
    return response


@router.post("/chat", response_model=ChatTurnResponse)
async def chat(
    payload: ChatTurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatTurnResponse:
    return await _process_chat_turn(payload, current_user, db)


@router.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    """Same /chat contract as the REST endpoint, but streams a
    {"type": "step", "step": <JourneyStepId>} frame as each graph node
    actually completes, then one final {"type": "result", "data": <same
    ChatTurnResponse shape as POST /chat>} frame before closing. Lets the
    web UI's stepper reflect real progress instead of guessing from the
    finished response (see NODE_TO_STEP above for the node->step mapping).

    Auth is a query param, not the Authorization header the REST endpoint
    uses - browsers can't set custom headers on a WebSocket handshake.
    Uses its own DB session (FastAPI's Depends(get_db) doesn't apply to
    WebSocket routes) and closes it when the connection ends.
    """
    async with AsyncSessionLocal() as db:
        try:
            current_user = await resolve_user_from_token(token, db)
        except HTTPException:
            await websocket.close(code=4401, reason="Could not validate credentials")
            return

        await websocket.accept()
        sent_steps: set[str] = set()

        async def on_node_done(node_name: str, _state: GraphState) -> None:
            step = NODE_TO_STEP.get(node_name)
            if step and step not in sent_steps:
                sent_steps.add(step)
                await websocket.send_json({"type": "step", "step": step})
            # "abs" has no dedicated graph node - the ABS/TK check is a
            # derived flag (_abs_tk_flags), ready as soon as rerank has run
            # (ip_types from route_ip_type, reranked_chunks from rerank).
            if node_name == "rerank" and "abs" not in sent_steps:
                sent_steps.add("abs")
                await websocket.send_json({"type": "step", "step": "abs"})

        try:
            while True:
                raw = await websocket.receive_json()
                payload = ChatTurnRequest.model_validate(raw)
                sent_steps.clear()
                try:
                    response = await _process_chat_turn(payload, current_user, db, on_node_done=on_node_done)
                except Exception as exc:  # noqa: BLE001 - report to the client, don't crash the socket
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                await websocket.send_json({"type": "result", "data": response.model_dump()})
        except WebSocketDisconnect:
            pass


@router.post("/escalations", response_model=EscalateResponse)
async def create_escalation(
    payload: EscalateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EscalateResponse:
    """User-initiated escalation (the Escalate button) - marks the most
    recent Case for this conversation as escalated to the ip queue,
    independent of the automatic risk-based routing at answer time."""
    try:
        conversation_uuid = uuid.UUID(payload.conversationId)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversationId") from exc

    conversation = await db.get(Conversation, conversation_uuid)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    result = await db.execute(
        select(Case)
        .where(Case.conversation_id == conversation_uuid)
        .order_by(Case.created_at.desc())
        .limit(1)
    )
    case = result.scalar_one_or_none()
    if case is None:
        case = Case(
            user_id=current_user.id,
            conversation_id=conversation.id,
            question="User requested escalation to a human facilitator.",
            risk_level=CaseRiskLevel.high,
            status=CaseStatus.escalated,
            queue=CaseQueue.ip,
        )
        db.add(case)
    else:
        case.status = CaseStatus.escalated
        case.queue = case.queue or CaseQueue.ip

    await db.flush()
    db.add(
        AuditLogEntry(
            actor_user_id=current_user.id,
            action="case.user_escalate",
            detail={"case_id": str(case.id), "conversation_id": str(conversation.id)},
        )
    )
    await db.commit()
    await db.refresh(case)

    return EscalateResponse(escalation_id=str(case.id))


def _make_title(message: Message | None) -> str:
    # display_text is the raw typed text; content is the canonical-English
    # fallback for rows from before display_text was populated on write.
    text = (message.display_text or message.content) if message else None
    if not text:
        return "New conversation"
    single_line = " ".join(text.split())
    return single_line if len(single_line) <= 60 else single_line[:57] + "..."


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummaryOut]:
    """Chat history list - one row per conversation, titled from its first
    user message, ordered by most recent activity."""
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == current_user.id)
    )
    conversations = result.scalars().all()

    summaries = []
    for conv in conversations:
        first_user_message = await db.scalar(
            select(Message)
            .where(Message.conversation_id == conv.id, Message.role == MessageRole.user)
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        last_message = await db.scalar(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        updated_at = last_message.created_at if last_message else conv.created_at
        summaries.append(
            ConversationSummaryOut(
                conversationId=str(conv.id),
                title=_make_title(first_user_message),
                language=conv.language,
                created_at=conv.created_at.isoformat(),
                updated_at=updated_at.isoformat(),
            )
        )

    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a conversation and its messages/escalation items. No ORM
    cascade or DB-level ON DELETE is configured on these FKs, so the
    child rows are deleted explicitly, in FK-dependency order."""
    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversationId") from exc

    conversation = await db.get(Conversation, conversation_uuid)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await db.execute(update(Case).where(Case.conversation_id == conversation_uuid).values(conversation_id=None))
    await db.execute(delete(EscalationItem).where(EscalationItem.conversation_id == conversation_uuid))
    await db.execute(delete(Message).where(Message.conversation_id == conversation_uuid))
    await db.delete(conversation)
    await db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessageOut])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationMessageOut]:
    """Full turn-by-turn history for one conversation - re-renders
    identically to when each assistant turn was first shown, via the
    stored `response_json` snapshot rather than re-deriving it."""
    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversationId") from exc

    conversation = await db.get(Conversation, conversation_uuid)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_uuid)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        ConversationMessageOut(
            role=m.role.value,
            display_text=m.display_text or m.content,
            language=m.language,
            created_at=m.created_at.isoformat(),
            response=ChatTurnResponse(**m.response_json) if m.response_json else None,
        )
        for m in messages
    ]
