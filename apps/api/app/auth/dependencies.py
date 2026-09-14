"""FastAPI dependencies for DB sessions, current-user resolution, and RBAC."""

import uuid
from collections.abc import AsyncGenerator, Callable

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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token, or raise 401."""
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


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory: 403s unless the current user's role is in `roles`."""

    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return _check_role
