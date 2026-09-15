"""_run_nodes records per-node wall time on state["node_timings"] -
pure unit test against dummy sync/async nodes, no network/LLM/DB."""

import asyncio

from app.graph.graph import _run_nodes


def _sync_node(state: dict) -> dict:
    return {"sync_ran": True}


async def _async_node(state: dict) -> dict:
    return {"async_ran": True}


def test_run_nodes_records_timing_per_node():
    state = asyncio.run(_run_nodes([_sync_node, _async_node], {}))

    assert state["sync_ran"] is True
    assert state["async_ran"] is True
    assert set(state["node_timings"]) == {"_sync_node", "_async_node"}
    assert all(ms >= 0 for ms in state["node_timings"].values())


def test_run_nodes_accumulates_timings_across_calls_on_same_state():
    state: dict = {}
    asyncio.run(_run_nodes([_sync_node], state))
    asyncio.run(_run_nodes([_async_node], state))

    assert set(state["node_timings"]) == {"_sync_node", "_async_node"}
