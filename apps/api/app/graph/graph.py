"""The full IP-SAKTI Sahayak state graph, hand-rolled as a plain sequence
of async node functions sharing one state dict. See pyproject.toml for
why this isn't built on the `langgraph` package. Node sequence matches
CLAUDE.md's architecture section, plus a condense_query step ahead of it
(the query-planner gap CLAUDE.md's "Known gaps" section flags as FR-10):

    condense_query -> classify_product -> route_jurisdiction ->
    route_ip_type -> retrieve -> rerank -> reason_and_cite ->
    validate_citations -> score_confidence -> escalate_if_needed

Split into CLASSIFY_NODES / REMAINING_NODES so a caller (chat/router.py's
clarifying-question precheck) can run just enough to decide whether to
ask a clarifying question, without paying for retrieval + the slow
reason_and_cite LLM call on a turn whose answer will be thrown away.
"""

from __future__ import annotations

import inspect
import time
from typing import Awaitable, Callable

from app.graph.nodes.classify_product import classify_product
from app.graph.nodes.condense_query import condense_query
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

CLASSIFY_NODES: list[Node] = [
    condense_query,
    classify_product,
]

REMAINING_NODES: list[Node] = [
    route_jurisdiction,
    route_ip_type,
    retrieve,
    rerank,
    reason_and_cite,
    validate_citations,
    score_confidence,
    escalate_if_needed,
]

NODES: list[Node] = CLASSIFY_NODES + REMAINING_NODES


NodeDoneCallback = Callable[[str, GraphState], Awaitable[None] | None]


async def _run_nodes(
    nodes: list[Node],
    state: GraphState,
    on_node_done: NodeDoneCallback | None = None,
) -> GraphState:
    # Per-node wall time, surfaced to the API response (ChatTurnResponse.
    # timing_ms) so latency regressions - e.g. reason_and_cite's LLM call
    # dominating end-to-end time - are visible per-request instead of only
    # discoverable by ad-hoc `time.perf_counter()` calls during debugging.
    # Kept on the same state dict across run_classification + run_remaining
    # so a single chat turn accumulates one complete timing breakdown.
    timings: dict[str, float] = state.setdefault("node_timings", {})
    for node in nodes:
        start = time.perf_counter()
        result = node(state)
        if inspect.isawaitable(result):
            result = await result
        state.update(result)
        timings[node.__name__] = round((time.perf_counter() - start) * 1000, 1)
        # Optional hook fired after each node completes - lets a caller
        # (chat/router.py's WebSocket endpoint) push live step-progress
        # frames to the browser as the graph runs, without REST callers
        # paying any cost (on_node_done is None for them).
        if on_node_done is not None:
            callback_result = on_node_done(node.__name__, state)
            if inspect.isawaitable(callback_result):
                await callback_result
    return state


def _initial_state(
    question: str,
    jurisdiction: str | None,
    doc_type: str | None,
    history_text: str | None,
) -> GraphState:
    return {
        "question": question,
        "jurisdiction": jurisdiction,
        "doc_type": doc_type,
        "history_text": history_text,
    }


async def run_classification(
    question: str,
    jurisdiction: str | None = None,
    doc_type: str | None = None,
    *,
    history_text: str | None = None,
    on_node_done: NodeDoneCallback | None = None,
) -> GraphState:
    """Run only condense_query + classify_product - enough to decide
    whether to ask a clarifying question, without running retrieval or
    the LLM reasoning call. Pass the result to run_remaining to continue
    the same turn without recomputing these nodes."""
    state = _initial_state(question, jurisdiction, doc_type, history_text)
    return await _run_nodes(CLASSIFY_NODES, state, on_node_done)


async def run_remaining(state: GraphState, *, on_node_done: NodeDoneCallback | None = None) -> GraphState:
    """Continue a state already produced by run_classification through
    the rest of the graph."""
    return await _run_nodes(REMAINING_NODES, state, on_node_done)


async def run_graph(
    question: str,
    jurisdiction: str | None = None,
    doc_type: str | None = None,
    *,
    history_text: str | None = None,
    on_node_done: NodeDoneCallback | None = None,
) -> GraphState:
    """Run the full node sequence and return the final state."""
    state = await run_classification(
        question, jurisdiction, doc_type, history_text=history_text, on_node_done=on_node_done
    )
    return await run_remaining(state, on_node_done=on_node_done)
