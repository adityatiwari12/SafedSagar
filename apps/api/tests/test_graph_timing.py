"""_run_nodes records per-node wall time on state["node_timings"] -
pure unit test against dummy sync/async nodes, no network/LLM/DB.

These are `async def` rather than sync tests calling `asyncio.run()`:
`asyncio.run` closes the loop it creates and leaves the thread with no
current event loop, which detaches the session-scoped `event_loop`
fixture conftest.py sets up to keep asyncpg's pool on one loop. Every
async test ordered after this module then failed with "There is no
current event loop in thread 'MainThread'" - an order-dependent failure
that looked like an unfixable Windows/pytest-asyncio quirk because each
affected file still passed in isolation.
"""

from app.graph.graph import _run_nodes


def _sync_node(state: dict) -> dict:
    return {"sync_ran": True}


async def _async_node(state: dict) -> dict:
    return {"async_ran": True}


async def test_run_nodes_records_timing_per_node():
    state = await _run_nodes([_sync_node, _async_node], {})

    assert state["sync_ran"] is True
    assert state["async_ran"] is True
    assert set(state["node_timings"]) == {"_sync_node", "_async_node"}
    assert all(ms >= 0 for ms in state["node_timings"].values())


async def test_run_nodes_accumulates_timings_across_calls_on_same_state():
    state: dict = {}
    await _run_nodes([_sync_node], state)
    await _run_nodes([_async_node], state)

    assert set(state["node_timings"]) == {"_sync_node", "_async_node"}
