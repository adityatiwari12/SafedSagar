"""The full IP-SAKTI Sahayak state graph, hand-rolled as a plain sequence
of async node functions sharing one state dict. See pyproject.toml for
why this isn't built on the `langgraph` package. Node sequence matches
CLAUDE.md's architecture section:

    classify_product -> route_jurisdiction -> route_ip_type ->
    retrieve -> rerank -> reason_and_cite -> validate_citations ->
    score_confidence -> escalate_if_needed
"""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable

from app.graph.nodes.classify_product import classify_product
from app.graph.nodes.escalate_if_needed import escalate_if_needed
from app.graph.nodes.reason_and_cite import reason_and_cite
from app.graph.nodes.rerank import rerank
from app.graph.nodes.retrieve import retrieve
from app.graph.nodes.route_ip_type import route_ip_type
from app.graph.nodes.route_jurisdiction import route_jurisdiction
from app.graph.nodes.score_confidence import score_confidence
from app.graph.nodes.validate_citations import validate_citations
from app.graph.state import GraphState

Node = Callable[[GraphState], dict] | Callable[[GraphState], Awaitable[dict]]

NODES: list[Node] = [
    classify_product,
    route_jurisdiction,
    route_ip_type,
    retrieve,
    rerank,
    reason_and_cite,
    validate_citations,
    score_confidence,
    escalate_if_needed,
]


async def run_graph(question: str, jurisdiction: str | None = None, doc_type: str | None = None) -> GraphState:
    """Run the full node sequence and return the final state."""
    state: GraphState = {"question": question, "jurisdiction": jurisdiction, "doc_type": doc_type}

    for node in NODES:
        result = node(state)
        if inspect.isawaitable(result):
            result = await result
        state.update(result)

    return state
