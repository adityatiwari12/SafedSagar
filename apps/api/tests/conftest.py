"""Shared pytest fixtures.

The async engine and session factory in app.db.base are created once at
import time and hold an asyncpg connection pool bound to a single event
loop. pytest-asyncio's default (function-scoped) event loop fixture tears
down and recreates the loop between tests, which breaks that pool with
"another operation is in progress" / "attached to a different loop"
errors on the second and later tests. Use a single session-scoped event
loop so all tests share the loop the engine's pool was created on.
"""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
