"""Tests for security functions: password hashing and JWT encoding/decoding."""

from datetime import datetime, timedelta

import pytest
from jose import JWTError, jwt

from app.config import settings
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_produces_different_hash(self):
        """Hash function should produce a hash different from the original password."""
        password = "my-secure-password-123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password_correct(self):
        """Correct password should verify against its hash."""
        password = "my-secure-password-123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "my-secure-password-123"
        hashed = hash_password(password)
        wrong_password = "wrong-password"
        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_round_trip_multiple(self):
        """Multiple hashes of the same password should verify correctly."""
        password = "test-password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Hashes should be different (salt is different)
        assert hash1 != hash2
        # But both should verify the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Test JWT token creation and decoding."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a string."""
        token = create_access_token(user_id="user123", role="user")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_and_decode_token_round_trip(self):
        """Token should encode and decode correctly."""
        user_id = "user123"
        role = "facilitator"
        token = create_access_token(user_id=user_id, role=role)
        payload = decode_access_token(token)

        assert payload["sub"] == user_id
        assert payload["role"] == role

    def test_create_and_decode_token_has_expiry(self):
        """Token payload should contain an exp claim."""
        user_id = "user456"
        role = "admin"
        token = create_access_token(user_id=user_id, role=role)
        payload = decode_access_token(token)

        assert "exp" in payload
        # exp should be in the future (within reasonable bounds)
        now = datetime.utcnow()
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        # Should expire in approximately jwt_expire_minutes minutes
        min_expected = now + timedelta(minutes=settings.jwt_expire_minutes - 1)
        max_expected = now + timedelta(minutes=settings.jwt_expire_minutes + 1)
        assert min_expected < exp_time < max_expected

    def test_decode_invalid_token_raises(self):
        """Decoding an invalid token should raise an exception."""
        invalid_token = "not.a.valid.token"
        with pytest.raises(JWTError):
            decode_access_token(invalid_token)

    def test_decode_expired_token_raises(self):
        """Decoding an expired token should raise an exception."""
        # Create an already-expired token using jose.jwt.encode directly
        past_time = datetime.utcnow() - timedelta(minutes=5)
        expired_payload = {
            "sub": "user123",
            "role": "user",
            "exp": int(past_time.timestamp()),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        # Attempting to decode should raise JWTError
        with pytest.raises(JWTError):
            decode_access_token(expired_token)

    def test_decode_token_tampered_raises(self):
        """Decoding a tampered token should raise an exception."""
        token = create_access_token(user_id="user123", role="user")
        # Tamper with the token by changing a character
        tampered_token = token[:-5] + "xxxxx"

        with pytest.raises(JWTError):
            decode_access_token(tampered_token)
