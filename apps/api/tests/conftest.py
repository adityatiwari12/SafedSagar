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
import uuid

import httpx
import pytest

from app.auth.security import create_access_token, hash_password
from app.db.base import AsyncSessionLocal
from app.db.models import User, UserRole
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """An httpx AsyncClient talking to the app in-process (no network)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def make_user():
    """Factory fixture: insert a user with a given role directly (bypasses
    /auth/register, which always forces role=user) and return (user, token).

    Facilitator/Admin accounts have no self-registration path per the RBAC
    spec, so tests that need one create it directly against the DB, the
    same way a real Admin would seed one.
    """
    async def _make(role: UserRole = UserRole.user, password: str = "test-password-123"):
        email = f"{uuid.uuid4()}@example.test"
        async with AsyncSessionLocal() as session:
            user = User(email=email, hashed_password=hash_password(password), role=role)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id, user_role = user.id, user.role
        token = create_access_token(str(user_id), user_role.value)
        return email, password, token

    yield _make
