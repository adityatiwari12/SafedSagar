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
from sqlalchemy import select

from app.auth.security import create_access_token, hash_password
from app.db.base import AsyncSessionLocal
from app.db.models import Role, User, UserRole, UserRoleAssignment
from app.main import app

# The legacy `users.role` column (still NOT NULL - see UserRole's
# docstring for the deprecation/migration-window context) has no slot for
# the 3 new-only role names. Since nothing in app.authz reads this column
# any more, any legacy value is fine for those three - `user` is the
# least-surprising placeholder.
_LEGACY_ROLE_FALLBACK: dict[str, UserRole] = {
    "user": UserRole.user,
    "facilitator": UserRole.facilitator,
    "regulatory_expert": UserRole.regulatory_expert,
    "legal_expert": UserRole.user,
    "institutional_admin": UserRole.admin,
    "ministry_admin": UserRole.admin,
    "kb_manager": UserRole.admin,
}


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
    /auth/register, which always forces role=user) and return
    (email, password, token).

    `role` is one of the new role-catalog names (app.authz.constants.
    RoleName) as a plain string, e.g. "facilitator", "ministry_admin" -
    this creates the real `UserRoleAssignment` row app.authz.service
    reads (the legacy `users.role` column is also set, best-effort, only
    because it's still NOT NULL - nothing in the new authz path reads it).
    Facilitator/Admin-tier accounts have no self-registration path per the
    RBAC spec, so tests that need one create it directly against the DB,
    the same way a real Admin would seed one.
    """
    async def _make(
        role: str = "user",
        organization_id: uuid.UUID | None = None,
        password: str = "test-password-123",
    ):
        email = f"{uuid.uuid4()}@example.test"
        legacy_role = _LEGACY_ROLE_FALLBACK[role]
        async with AsyncSessionLocal() as session:
            user = User(email=email, hashed_password=hash_password(password), role=legacy_role)
            session.add(user)
            await session.flush()

            role_row = await session.scalar(select(Role).where(Role.name == role))
            assert role_row is not None, f"role {role!r} not seeded - run app.authz.seed"
            session.add(
                UserRoleAssignment(user_id=user.id, role_id=role_row.id, organization_id=organization_id)
            )
            await session.commit()
            await session.refresh(user)
            user_id, user_role = user.id, user.role
        token = create_access_token(str(user_id), user_role.value)
        return email, password, token

    yield _make
