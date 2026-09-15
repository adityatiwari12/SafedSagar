"""Tests for /auth/register, /auth/login, /auth/me."""

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings


async def test_register_login_me_round_trip(client):
    email = f"{uuid.uuid4()}@example.test"
    password = "correct-horse-battery"

    register_resp = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["email"] == email
    assert body["role"] == "user"

    login_resp = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email
    assert me_resp.json()["role"] == "user"
    assert "hashed_password" not in me_resp.json()
    assert "password" not in me_resp.json()


async def test_login_wrong_password_401(client, make_user):
    email, _password, _token = await make_user()

    resp = await client.post(
        "/auth/login", data={"username": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_register_default_role_is_user_approved(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "user"
    assert body["verification_status"] == "approved"


async def test_register_facilitator_request_lands_pending(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "role": "facilitator"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "facilitator"
    assert body["verification_status"] == "pending"


async def test_register_regulatory_expert_request_lands_pending(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "role": "regulatory_expert"},
    )
    assert resp.status_code == 201
    assert resp.json()["verification_status"] == "pending"


async def test_register_admin_role_rejected_422(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "role": "admin"},
    )
    assert resp.status_code == 422


async def test_register_persona_for_user_role(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "role": "user", "persona": "cultivator"},
    )
    assert resp.status_code == 201
    assert resp.json()["persona"] == "cultivator"


async def test_register_invalid_persona_rejected_422(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "persona": "not-a-real-persona"},
    )
    assert resp.status_code == 422


async def test_login_nonexistent_email_401(client):
    resp = await client.post(
        "/auth/login",
        data={"username": f"{uuid.uuid4()}@example.test", "password": "whatever123"},
    )
    assert resp.status_code == 401


async def test_register_password_too_long_422(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register", json={"email": email, "password": "a" * 73}
    )
    assert resp.status_code == 422


async def test_register_password_too_short_422(client):
    email = f"{uuid.uuid4()}@example.test"
    resp = await client.post(
        "/auth/register", json={"email": email, "password": "short"}
    )
    assert resp.status_code == 422


async def test_me_garbage_token_401(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.valid.token"}
    )
    assert resp.status_code == 401


async def test_me_expired_token_401(client, make_user):
    email, _password, _token = await make_user()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_token = jwt.encode(
        {"sub": email, "role": "user", "exp": int(past.timestamp())},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


async def test_register_duplicate_email_400(client):
    email = f"{uuid.uuid4()}@example.test"
    await client.post("/auth/register", json={"email": email, "password": "pw1234567"})

    resp = await client.post(
        "/auth/register", json={"email": email, "password": "another-pw"}
    )
    assert resp.status_code == 400


async def test_me_without_token_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
