"""The /query endpoint: runs the retrieval/citation graph for one question."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.graph.graph import run_graph
from app.query.schemas import CitationOut, QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query(payload: QueryRequest, _current_user: User = Depends(get_current_user)) -> QueryResponse:
    state = await run_graph(payload.question, payload.jurisdiction, payload.doc_type)

    return QueryResponse(
        answer=state.get("answer", ""),
        citations=[
            CitationOut(doc_id=c["doc_id"], section_or_article=c["section_or_article"])
            for c in state.get("validated_citations", [])
        ],
        rejected_citation_count=len(state.get("rejected_citations", [])),
    )
