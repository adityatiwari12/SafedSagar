"""The retrieval/citation state graph, hand-rolled as a plain sequence of
async node functions sharing one state dict. See pyproject.toml for why
this isn't built on the `langgraph` package. Node sequence matches
CLAUDE.md's architecture section (the citation-core subset of it - the
classify/route/confidence/escalate nodes are Phase 4):

    retrieve -> rerank -> reason_and_cite -> validate_citations
"""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable

from app.graph.nodes.rerank import rerank
from app.graph.nodes.reason_and_cite import reason_and_cite
from app.graph.nodes.retrieve import retrieve
from app.graph.nodes.validate_citations import validate_citations
from app.graph.state import GraphState

Node = Callable[[GraphState], dict] | Callable[[GraphState], Awaitable[dict]]

NODES: list[Node] = [retrieve, rerank, reason_and_cite, validate_citations]


async def run_graph(question: str, jurisdiction: str | None = None, doc_type: str | None = None) -> GraphState:
    """Run the full node sequence and return the final state."""
    state: GraphState = {"question": question, "jurisdiction": jurisdiction, "doc_type": doc_type}

    for node in NODES:
        result = node(state)
        if inspect.isawaitable(result):
            result = await result
        state.update(result)

    return state
