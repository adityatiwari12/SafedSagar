"""Tests for the require_role RBAC dependency, via a throwaway test-only route."""

from fastapi import Depends

from app.auth.dependencies import require_role
from app.db.models import UserRole
from app.main import app


@app.get("/test/admin-only")
def _admin_only_route(_user=Depends(require_role("admin"))) -> dict[str, bool]:
    """Test-only route, mounted here rather than in app/main.py, to exercise
    require_role() without adding a real admin endpoint before one exists."""
    return {"ok": True}


async def test_require_role_admin_allows_admin(client, make_user):
    _email, _password, token = await make_user(role=UserRole.admin)

    resp = await client.get(
        "/test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


async def test_require_role_admin_rejects_user(client, make_user):
    _email, _password, token = await make_user(role=UserRole.user)

    resp = await client.get(
        "/test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
