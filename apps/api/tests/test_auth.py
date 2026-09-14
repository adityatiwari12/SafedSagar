"""Tests for /auth/register, /auth/login, /auth/me."""

import uuid


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


async def test_login_wrong_password_401(client, make_user):
    email, _password, _token = await make_user()

    resp = await client.post(
        "/auth/login", data={"username": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_register_duplicate_email_400(client):
    email = f"{uuid.uuid4()}@example.test"
    await client.post("/auth/register", json={"email": email, "password": "pw12345"})

    resp = await client.post(
        "/auth/register", json={"email": email, "password": "another-pw"}
    )
    assert resp.status_code == 400


async def test_me_without_token_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
