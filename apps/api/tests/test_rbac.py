"""Tests for the require_permission RBAC dependency, via a throwaway
test-only route. Supersedes the old require_role-based version - see
docs/product/rbac-full-implementation-spec.md."""

from fastapi import Depends

from app.authz.constants import Permission
from app.authz.service import AuthzContext, require_permission
from app.main import app


@app.get("/test/system-configure-only")
def _system_configure_only_route(
    _ctx: AuthzContext = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
) -> dict[str, bool]:
    """Test-only route, mounted here rather than in app/main.py, to
    exercise require_permission() without adding a real endpoint before
    one exists. system.configure is granted only to ministry_admin
    (app.authz.constants.ROLE_PERMISSIONS) - a clean single-role probe."""
    return {"ok": True}


async def test_require_permission_allows_granted_role(client, make_user):
    _email, _password, token = await make_user(role="ministry_admin")

    resp = await client.get(
        "/test/system-configure-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


async def test_require_permission_rejects_ungranted_role(client, make_user):
    _email, _password, token = await make_user(role="user")

    resp = await client.get(
        "/test/system-configure-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_require_permission_rejects_other_admin_tiers(client, make_user):
    """institutional_admin and kb_manager must NOT get system.configure -
    it's a ministry_admin-only grant (least privilege across admin tiers,
    not a blanket "any admin" check)."""
    for role in ("institutional_admin", "kb_manager"):
        _email, _password, token = await make_user(role=role)
        resp = await client.get(
            "/test/system-configure-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, f"{role} must not have system.configure"
