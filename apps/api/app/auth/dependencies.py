"""FastAPI dependencies for DB sessions, current-user resolution, and RBAC."""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.db.base import AsyncSessionLocal
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for the lifetime of one request."""
    async with AsyncSessionLocal() as session:
        yield session


async def resolve_user_from_token(token: str, db: AsyncSession) -> User:
    """Decode a bearer token and load the user it names, or raise 401.

    Shared by get_current_user (Authorization header, REST) and the /chat/ws
    WebSocket endpoint (token as a query param - browsers can't set a
    WebSocket's Authorization header, so the handshake URL carries it
    instead).
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise unauthorized from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthorized

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise unauthorized from exc

    user = await db.get(User, user_uuid)
    if user is None:
        raise unauthorized
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token, or raise 401."""
    return await resolve_user_from_token(token, db)
