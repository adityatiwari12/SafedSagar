"""The /query endpoint: runs the retrieval/citation graph for one question.

Every call persists a Conversation + the question/answer Messages, and a
Case (via the same app.cases.service.derive_case_outcome the /chat endpoint
uses) - this is what apps/cases' facilitator/regulatory-expert/legal-expert
queue reads from.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_db
from app.cases.service import derive_case_outcome
from app.chat.router import _abs_tk_flags
from app.db.models import Case, Conversation, Message, MessageRole, User
from app.graph.graph import run_graph
from app.graph.state import GraphState
from app.query.schemas import CitationOut, QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


async def _persist(db: AsyncSession, user: User, question: str, state: GraphState) -> None:
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.flush()  # need conversation.id before the Messages/Case reference it

    db.add(Message(conversation_id=conversation.id, role=MessageRole.user, content=question))
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=state.get("answer", ""),
        )
    )

    abs_flags = _abs_tk_flags(state)
    outcome = derive_case_outcome(
        escalate=state.get("escalate", False),
        confidence_level=state.get("confidence_level", "low"),
        product_classification=state.get("product_classification"),
        ip_types=state.get("ip_types", []),
        abs_tk_flags=abs_flags.model_dump() if abs_flags else None,
    )
    db.add(
        Case(
            user_id=user.id,
            conversation_id=conversation.id,
            question=question,
            product_classification=state.get("product_classification"),
            ip_types=state.get("ip_types", []),
            jurisdiction=state.get("jurisdiction"),
            abs_tk_flags=abs_flags.model_dump() if abs_flags else None,
            confidence_score=state.get("confidence_score"),
            confidence_level=state.get("confidence_level"),
            risk_level=outcome.risk_level,
            status=outcome.status,
            queue=outcome.queue,
        )
    )

    await db.commit()


@router.post("", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    state = await run_graph(payload.question, payload.jurisdiction, payload.doc_type)

    await _persist(db, current_user, payload.question, state)

    return QueryResponse(
        answer=state.get("answer", ""),
        citations=[
            CitationOut(doc_id=c["doc_id"], section_or_article=c["section_or_article"])
            for c in state.get("validated_citations", [])
        ],
        rejected_citation_count=len(state.get("rejected_citations", [])),
        product_classification=state.get("product_classification", "unclear"),
        jurisdiction=state.get("jurisdiction"),
        jurisdiction_source=state.get("jurisdiction_source", "explicit"),
        ip_types=state.get("ip_types", []),
        confidence_score=state.get("confidence_score", 0.0),
        confidence_level=state.get("confidence_level", "low"),
        escalate=state.get("escalate", True),
        escalation_reason=state.get("escalation_reason"),
    )
