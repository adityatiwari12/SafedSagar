"""HTTP-level tests for the Phase 1 role/organization management
endpoints (app/admin/router.py) - in particular the guard against a
scoped admin using a client-supplied organization_id to escalate past
their own scope (spec Section 24: "no privilege escalation through
client requests")."""

import uuid


async def test_ministry_admin_can_create_organization(client, make_user):
    _email, _password, token = await make_user(role="ministry_admin")
    resp = await client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "AIIA Test Institute", "org_type": "institution"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "AIIA Test Institute"


async def test_user_cannot_create_organization(client, make_user):
    _email, _password, token = await make_user(role="user")
    resp = await client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Should Not Exist", "org_type": "startup"},
    )
    assert resp.status_code == 403


async def test_institutional_admin_sees_only_own_organization(client, make_user):
    ministry_email, _pw, ministry_token = await make_user(role="ministry_admin")

    create_resp = await client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {ministry_token}"},
        json={"name": f"Org-{uuid.uuid4().hex[:8]}", "org_type": "institution"},
    )
    org_id = create_resp.json()["id"]

    _email, _pw, inst_admin_token = await make_user(role="institutional_admin", organization_id=uuid.UUID(org_id))

    resp = await client.get("/admin/organizations", headers={"Authorization": f"Bearer {inst_admin_token}"})
    assert resp.status_code == 200
    org_ids = {o["id"] for o in resp.json()}
    assert org_ids == {org_id}


async def test_institutional_admin_cannot_grant_platform_wide_role(client, make_user):
    """The privilege-escalation guard: an institutional_admin's
    users.manage grant is scoped to their own organization_id. Passing
    organization_id=null (platform-wide) in the request body must not be
    honored just because the client sent it."""
    ministry_email, _pw, ministry_token = await make_user(role="ministry_admin")
    create_resp = await client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {ministry_token}"},
        json={"name": f"Org-{uuid.uuid4().hex[:8]}", "org_type": "institution"},
    )
    org_id = create_resp.json()["id"]

    _email, _pw, inst_admin_token = await make_user(role="institutional_admin", organization_id=uuid.UUID(org_id))
    target_email, _pw2, _target_token = await make_user(role="user")

    # Need the target's user id - list_users requires users.manage, which
    # institutional_admin has (org-scoped), so this call itself succeeds;
    # the escalation attempt below is the actual assertion.
    users_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {inst_admin_token}"})
    target = next(u for u in users_resp.json() if u["email"] == target_email)

    escalate_resp = await client.post(
        f"/admin/users/{target['id']}/roles",
        headers={"Authorization": f"Bearer {inst_admin_token}"},
        json={"role_name": "ministry_admin", "organization_id": None},
    )
    assert escalate_resp.status_code == 403


async def test_institutional_admin_can_assign_role_within_own_org(client, make_user):
    ministry_email, _pw, ministry_token = await make_user(role="ministry_admin")
    create_resp = await client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {ministry_token}"},
        json={"name": f"Org-{uuid.uuid4().hex[:8]}", "org_type": "startup"},
    )
    org_id = create_resp.json()["id"]

    _email, _pw, inst_admin_token = await make_user(role="institutional_admin", organization_id=uuid.UUID(org_id))
    target_email, _pw2, _target_token = await make_user(role="user")

    users_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {inst_admin_token}"})
    target = next(u for u in users_resp.json() if u["email"] == target_email)

    resp = await client.post(
        f"/admin/users/{target['id']}/roles",
        headers={"Authorization": f"Bearer {inst_admin_token}"},
        json={"role_name": "user", "organization_id": org_id},
    )
    assert resp.status_code == 201
    assert resp.json()["role_name"] == "user"
    assert resp.json()["organization_id"] == org_id
