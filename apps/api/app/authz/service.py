"""Authorization service - the single place permission decisions get made.

Replaces `app.auth.dependencies.require_role` (deleted in this change,
not kept alongside this as a second parallel mechanism - see
docs/product/rbac-full-implementation-spec.md Section 5). Every check
resolves from `user_roles`/`role_permissions` (fresh per request), never
from a JWT claim - a role revoked mid-session takes effect on the next
request, not just the next login.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_db
from app.db.models import Permission, Role, RolePermission, User, UserRoleAssignment


@dataclass(frozen=True)
class AuthzContext:
    """One user's resolved roles/permissions/org memberships for the
    lifetime of one request. Built once per request (`load_authz_context`
    dependency), not re-queried per `has_permission` call."""

    user: User
    # permission key -> set of organization_id the grant applies to, with
    # None meaning "platform-wide" (spec Section 2's NULL-organization_id
    # convention, mirrored here).
    permissions: dict[str, set[uuid.UUID | None]] = field(default_factory=dict)
    organization_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)


async def load_authz_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthzContext:
    """FastAPI dependency: resolve the caller's full permission set in one
    query pass. Depend on this (or, more commonly, `require_permission`)
    rather than querying `user_roles` ad hoc in route handlers."""
    rows = await db.execute(
        select(Permission.key, UserRoleAssignment.organization_id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(UserRoleAssignment.user_id == current_user.id)
    )
    permissions: dict[str, set[uuid.UUID | None]] = {}
    for key, organization_id in rows.all():
        permissions.setdefault(key, set()).add(organization_id)

    org_rows = await db.execute(
        select(UserRoleAssignment.organization_id).where(
            UserRoleAssignment.user_id == current_user.id,
            UserRoleAssignment.organization_id.is_not(None),
        )
    )
    organization_ids = frozenset(row[0] for row in org_rows.all())

    return AuthzContext(user=current_user, permissions=permissions, organization_ids=organization_ids)


def has_permission(ctx: AuthzContext, key: str, *, organization_id: uuid.UUID | None = None) -> bool:
    """Does the caller's grant for `key` cover this *exact* target scope.

    `organization_id=None` means the target scope IS the platform-wide
    scope itself (e.g. "assign a role with no organization_id") - only
    satisfied by a platform-wide grant (`None in granted_orgs`), never by
    an org-scoped grant. Pass a specific `organization_id` to ask "does
    this cover *that* organization" - satisfied by either a platform-wide
    grant (applies everywhere) or a grant scoped to exactly that org.

    This is a precise scope check, not "does the user have this
    permission at all" - use `has_any_grant` for that (the route-entry
    gate use case, where the exact scope isn't known yet). An earlier
    version of this function conflated the two by unconditionally
    returning True whenever `organization_id is None`, which let an
    org-scoped grant (e.g. institutional_admin's `users.manage` for one
    org) satisfy a request targeting the platform-wide scope - a real
    privilege-escalation bug, caught by
    tests/test_admin_rbac_endpoints.py::
    test_institutional_admin_cannot_grant_platform_wide_role.
    """
    granted_orgs = ctx.permissions.get(key)
    if not granted_orgs:
        return False
    if organization_id is None:
        return None in granted_orgs
    return None in granted_orgs or organization_id in granted_orgs


def has_any_grant(ctx: AuthzContext, key: str) -> bool:
    """Does the caller hold `key` in ANY scope - platform-wide or any one
    organization. The route-entry gate use case (`require_permission`):
    "can this user do this at all," before the route body has resolved
    which specific organization_id (if any) is actually in play."""
    return bool(ctx.permissions.get(key))


def can_access_resource(ctx: AuthzContext, resource: object) -> bool:
    """Ownership OR organization membership OR explicit assignment OR
    public visibility - the checks a permission key alone can't express.

    Takes a plain `object` and reads it via getattr (not an isinstance
    check against a fixed set of ORM classes) because Phase 2+ resource
    types (Case, Product, ResearchProject, KnowledgeRecord, Document,
    Evidence) aren't all modeled yet - this function's contract is "any
    object exposing `owner_user_id`/`assigned_to_user_id`/
    `organization_id`/`visibility`," so later entities plug in without
    editing this function, matching the shape already specified in
    docs/product/rbac-full-implementation-spec.md Section 5.
    """
    owner_user_id = getattr(resource, "owner_user_id", None)
    if owner_user_id is not None and owner_user_id == ctx.user.id:
        return True

    assigned_user_id = getattr(resource, "assigned_to_user_id", None)
    if assigned_user_id is not None and assigned_user_id == ctx.user.id:
        return True

    organization_id = getattr(resource, "organization_id", None)
    if organization_id is not None and organization_id in ctx.organization_ids:
        return True

    visibility = getattr(resource, "visibility", None)
    if visibility is not None and getattr(visibility, "value", visibility) == "public":
        return True

    # A grantee list (e.g. KnowledgeRecordAccess rows for a TK record,
    # Phase 4) is resolved by the caller before invoking this function -
    # can_access_resource intentionally does not query the DB itself, to
    # stay a pure/testable function over data already loaded.
    explicit_grantee_ids = getattr(resource, "_explicit_grantee_user_ids", None)
    if explicit_grantee_ids and ctx.user.id in explicit_grantee_ids:
        return True

    return False


def can_perform_action(ctx: AuthzContext, resource: object, permission_key: str) -> bool:
    """The full check: permission grant AND resource access. Resource-state
    rules (e.g. "case.close only from a status that allows closing") are
    intentionally NOT here - those are workflow rules that belong in the
    entity's own service module (Phase 2's case-service), not smeared
    into the generic authorization layer."""
    organization_id = getattr(resource, "organization_id", None)
    return has_permission(ctx, permission_key, organization_id=organization_id) and can_access_resource(
        ctx, resource
    )


def require_permission(key: str) -> Callable[[AuthzContext], AuthzContext]:
    """FastAPI dependency factory - the direct replacement for
    `require_role(*roles)`. Checks the permission platform-wide-or-any-org
    (route handlers that need org-specific enforcement call
    `has_permission(ctx, key, organization_id=...)` themselves after this
    dependency resolves `ctx`, since the route is what knows which
    organization_id is in play)."""

    async def _check(ctx: AuthzContext = Depends(load_authz_context)) -> AuthzContext:
        if not has_any_grant(ctx, key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {key}",
            )
        return ctx

    return _check
