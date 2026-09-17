"""Tests for app.authz - the permission matrix itself, the seeded DB
state, and cross-organization isolation. See
docs/product/rbac-full-implementation-spec.md Section 9."""

import uuid

from sqlalchemy import select

from app.authz.constants import (
    ADMIN_TIER_ROLES,
    ALL_ROLES,
    PERMISSION_CATALOG,
    ROLE_PERMISSIONS,
    Permission,
)
from app.authz.service import can_access_resource, can_perform_action, has_permission
from app.db.base import AsyncSessionLocal
from app.db.models import Permission as PermissionModel
from app.db.models import Role, RolePermission


def test_admin_tiers_never_hold_review_approval_permissions():
    """Structural separation-of-duties invariant (spec Sections 0/8):
    system administration must never double as legal decision-making."""
    forbidden = {Permission.REVIEW_APPROVE, Permission.REVIEW_MODIFY, Permission.REVIEW_REJECT}
    for role in ADMIN_TIER_ROLES:
        granted = ROLE_PERMISSIONS[role]
        assert not (granted & forbidden), f"{role} must never hold {granted & forbidden}"


def test_admin_tiers_never_hold_case_view_queue():
    """spec Section 12: government/institutional admin oversight is
    aggregate-analytics-only, never individual case detail."""
    for role in ("institutional_admin", "ministry_admin"):
        assert Permission.CASE_VIEW_QUEUE not in ROLE_PERMISSIONS[role]


def test_every_role_can_ask_the_assistant():
    """spec Section 4's corrected ai.* row: universal, not withheld from
    any authenticated role."""
    for role in ALL_ROLES:
        assert Permission.AI_ASK in ROLE_PERMISSIONS[role]


def test_permission_catalog_has_no_duplicate_keys():
    keys = [key for key, *_ in PERMISSION_CATALOG]
    assert len(keys) == len(set(keys))


def test_role_permissions_only_reference_cataloged_permissions():
    catalog_keys = {key for key, *_ in PERMISSION_CATALOG}
    for role, keys in ROLE_PERMISSIONS.items():
        unknown = keys - catalog_keys
        assert not unknown, f"{role} grants unknown permission(s): {unknown}"


async def test_seeded_db_matches_constants_exactly():
    """The migration's seed data (alembic revision a18b27770761) and
    app.authz.seed must resolve to the exact same role->permission
    matrix as the constants module - a seed drifting from constants.py
    would make code and DB silently disagree about who can do what."""
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Role.name, PermissionModel.key)
            .select_from(RolePermission)
            .join(Role, Role.id == RolePermission.role_id)
            .join(PermissionModel, PermissionModel.id == RolePermission.permission_id)
        )
        db_matrix: dict[str, set[str]] = {}
        for role_name, permission_key in rows.all():
            db_matrix.setdefault(role_name, set()).add(permission_key)

    assert db_matrix == ROLE_PERMISSIONS


class _FakeUser:
    def __init__(self, user_id: uuid.UUID):
        self.id = user_id


def test_has_permission_platform_wide_grant_covers_any_org():
    from app.authz.service import AuthzContext

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    ctx = AuthzContext(user=_FakeUser(user_id), permissions={"users.manage": {None}}, organization_ids=frozenset())
    assert has_permission(ctx, "users.manage")
    assert has_permission(ctx, "users.manage", organization_id=org_id)


def test_has_permission_org_scoped_grant_does_not_cover_platform_wide_target():
    """Regression test for the privilege-escalation bug caught by
    tests/test_admin_rbac_endpoints.py::
    test_institutional_admin_cannot_grant_platform_wide_role - an
    org-scoped grant must NOT satisfy a request targeting the
    platform-wide (organization_id=None) scope."""
    from app.authz.service import AuthzContext

    own_org = uuid.uuid4()
    ctx = AuthzContext(
        user=_FakeUser(uuid.uuid4()),
        permissions={"users.manage": {own_org}},
        organization_ids=frozenset({own_org}),
    )
    assert not has_permission(ctx, "users.manage", organization_id=None)


def test_has_permission_org_scoped_grant_does_not_cover_other_orgs():
    from app.authz.service import AuthzContext

    user_id = uuid.uuid4()
    own_org = uuid.uuid4()
    other_org = uuid.uuid4()
    ctx = AuthzContext(
        user=_FakeUser(user_id),
        permissions={"users.manage": {own_org}},
        organization_ids=frozenset({own_org}),
    )
    assert has_permission(ctx, "users.manage", organization_id=own_org)
    assert not has_permission(ctx, "users.manage", organization_id=other_org)


def test_can_access_resource_ownership():
    from app.authz.service import AuthzContext

    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    ctx = AuthzContext(user=_FakeUser(owner_id))

    class _Resource:
        owner_user_id = owner_id
        organization_id = None

    class _OtherResource:
        owner_user_id = other_id
        organization_id = None

    assert can_access_resource(ctx, _Resource())
    assert not can_access_resource(ctx, _OtherResource())


def test_can_access_resource_organization_isolation():
    """A user in Organization A cannot access a resource scoped to
    Organization B, even though the permission check alone would pass."""
    from app.authz.service import AuthzContext

    user_id = uuid.uuid4()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    ctx = AuthzContext(user=_FakeUser(user_id), organization_ids=frozenset({org_a}))

    class _ResourceInOrgB:
        owner_user_id = uuid.uuid4()  # not this user
        organization_id = org_b

    assert not can_access_resource(ctx, _ResourceInOrgB())


def test_can_access_resource_public_visibility():
    from app.authz.service import AuthzContext

    ctx = AuthzContext(user=_FakeUser(uuid.uuid4()))

    class _PublicTkRecord:
        owner_user_id = uuid.uuid4()
        organization_id = None
        visibility = "public"

    class _PrivateTkRecord:
        owner_user_id = uuid.uuid4()
        organization_id = None
        visibility = "private"

    assert can_access_resource(ctx, _PublicTkRecord())
    assert not can_access_resource(ctx, _PrivateTkRecord())


def test_can_perform_action_requires_both_permission_and_access():
    from app.authz.service import AuthzContext

    owner_id = uuid.uuid4()
    ctx_with_permission_no_access = AuthzContext(
        user=_FakeUser(uuid.uuid4()), permissions={"product.edit": {None}}
    )
    ctx_with_access_no_permission = AuthzContext(user=_FakeUser(owner_id), permissions={})

    class _Product:
        owner_user_id = owner_id
        organization_id = None

    assert not can_perform_action(ctx_with_permission_no_access, _Product(), "product.edit")
    assert not can_perform_action(ctx_with_access_no_permission, _Product(), "product.edit")
