"""Password hashing and JWT token management."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings

_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The hashed password string.
    """
    encoded = password.encode()
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {_BCRYPT_MAX_BYTES} bytes")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(encoded, salt)
    return hashed.decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its hash.

    Args:
        plain_password: The plain-text password to verify.
        hashed_password: The hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    encoded = plain_password.encode()
    if len(encoded) > _BCRYPT_MAX_BYTES:
        # A password this long can never match a hash created under
        # hash_password's 72-byte limit - reject without hitting bcrypt's
        # own hard ValueError, so an over-length login attempt gets a
        # normal 401 (via the caller) instead of a 500.
        return False
    return bcrypt.checkpw(encoded, hashed_password.encode())


def create_access_token(user_id: str, role: str) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: The user ID to encode in the 'sub' claim.
        role: The user role to encode in the 'role' claim.

    Returns:
        The encoded JWT token as a string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token.

    Args:
        token: The JWT token string to decode.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        jose.JWTError: If the token is invalid, expired, or cannot be verified.
    """
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    return payload
