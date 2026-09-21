"""Graph expansion node: after rerank, before reason_and_cite. Appends up
to app.kg.expand.MAX_GRAPH_CHUNKS real source_documents chunks that the
legal knowledge graph connects to this question (marked via_graph=True),
and records related_provisions for the UI. No LLM calls; a few indexed
queries. A missing/empty graph (not built yet, or migration not applied)
is a no-op, never an error - the answer just proceeds without it."""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.db.base import AsyncSessionLocal
from app.graph.state import GraphState
from app.kg.expand import expand

logger = logging.getLogger(__name__)


async def expand_with_graph(state: GraphState) -> dict:
    try:
        async with AsyncSessionLocal() as session:
            return await expand(session, state)
    except SQLAlchemyError as exc:
        logger.warning("expand_with_graph: graph unavailable, skipping (%s)", exc.__class__.__name__)
        return {"related_provisions": [], "graph_chunks": []}
