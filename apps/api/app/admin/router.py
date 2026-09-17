"""Admin-only platform views, plus role/organization management
(docs/product/rbac-full-implementation-spec.md Phase 1)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    OrganizationCreate,
    OrganizationOut,
    RoleAssignmentCreate,
    RoleAssignmentOut,
    RoleOut,
    UserSummary,
)
from app.auth.dependencies import get_db
from app.authz.constants import Permission
from app.authz.service import AuthzContext, has_permission, require_permission
from app.db.models import (
    AuditLogEntry,
    EscalationItem,
    EscalationStatus,
    Organization,
    OrganizationType,
    Role,
    User,
    UserRoleAssignment,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    _ctx: AuthzContext = Depends(require_permission(Permission.USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> list[UserSummary]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.get("/stats")
async def platform_stats(
    # Aggregate counts only (role counts, open/closed case counts) - the
    # analytics.national grant, not users.manage, is the correct gate:
    # this endpoint never returns an individual case or user record (spec
    # Section 12's "aggregated, privacy-preserving" requirement).
    _ctx: AuthzContext = Depends(require_permission(Permission.ANALYTICS_NATIONAL)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role_counts = await db.execute(select(User.role, func.count()).group_by(User.role))
    users_by_role = {role.value: count for role, count in role_counts.all()}

    open_cases = await db.scalar(
        select(func.count()).select_from(EscalationItem).where(EscalationItem.status == EscalationStatus.open)
    )
    closed_cases = await db.scalar(
        select(func.count()).select_from(EscalationItem).where(EscalationItem.status == EscalationStatus.closed)
    )

    return {
        "users_by_role": users_by_role,
        "open_cases": open_cases or 0,
        "closed_cases": closed_cases or 0,
    }


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    _ctx: AuthzContext = Depends(require_permission(Permission.USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> list[Role]:
    """Reference data for the role-assignment UI - readable by anyone who
    can manage users (institutional_admin included), not gated behind the
    stricter roles.manage (ministry_admin-only, for editing the role/
    permission catalog itself, not just assigning existing roles)."""
    result = await db.execute(select(Role).order_by(Role.name))
    return list(result.scalars().all())


@router.get("/organizations", response_model=list[OrganizationOut])
async def list_organizations(
    ctx: AuthzContext = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> list[Organization]:
    """A ministry_admin (platform-wide org.view grant) sees every
    organization; an institutional_admin (org-scoped org.view grant) sees
    only the organization(s) their own role grant names."""
    has_platform_wide_grant = None in ctx.permissions.get(Permission.ORG_VIEW, set())
    if has_platform_wide_grant:
        result = await db.execute(select(Organization).order_by(Organization.name))
    else:
        result = await db.execute(
            select(Organization).where(Organization.id.in_(ctx.organization_ids)).order_by(Organization.name)
        )
    return list(result.scalars().all())


@router.post("/organizations", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    ctx: AuthzContext = Depends(require_permission(Permission.ORGANIZATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    try:
        org_type = OrganizationType(payload.org_type)
    except ValueError as exc:
        allowed = ", ".join(t.value for t in OrganizationType)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"org_type must be one of: {allowed}",
        ) from exc

    org = Organization(name=payload.name, org_type=org_type, created_by_user_id=ctx.user.id)
    db.add(org)
    await db.flush()
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="organization.create",
            detail={"organization_id": str(org.id), "name": org.name, "org_type": org.org_type.value},
        )
    )
    await db.commit()
    await db.refresh(org)
    return org


@router.post(
    "/users/{user_id}/roles", response_model=RoleAssignmentOut, status_code=status.HTTP_201_CREATED
)
async def assign_role(
    user_id: uuid.UUID,
    payload: RoleAssignmentCreate,
    ctx: AuthzContext = Depends(require_permission(Permission.USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> UserRoleAssignment:
    """Grant a role to a user. `payload.organization_id` is never trusted
    at face value: a caller only granted users.manage for their own
    organization (institutional_admin) cannot use this to grant a
    platform-wide role or a role scoped to a *different* organization -
    both require a users.manage grant that actually covers the requested
    scope, checked here via `has_permission`, not by trusting whatever
    organization_id the client sent (spec Section 24: "no privilege
    escalation through client requests")."""
    if not has_permission(ctx, Permission.USERS_MANAGE, organization_id=payload.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted to manage users for this organization scope",
        )

    target_user = await db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = await db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown role name")

    if payload.organization_id is not None:
        org = await db.get(Organization, payload.organization_id)
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    assignment = UserRoleAssignment(
        user_id=target_user.id, role_id=role.id, organization_id=payload.organization_id
    )
    db.add(assignment)
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="user_role.assign",
            detail={
                "target_user_id": str(target_user.id),
                "role_name": role.name,
                "organization_id": str(payload.organization_id) if payload.organization_id else None,
            },
        )
    )
    await db.commit()
    await db.refresh(assignment)
    return RoleAssignmentOut(
        id=assignment.id,
        user_id=assignment.user_id,
        role_name=role.name,
        organization_id=assignment.organization_id,
    )


@router.delete("/users/{user_id}/roles/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role(
    user_id: uuid.UUID,
    assignment_id: uuid.UUID,
    ctx: AuthzContext = Depends(require_permission(Permission.USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> None:
    assignment = await db.get(UserRoleAssignment, assignment_id)
    if assignment is None or assignment.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")

    if not has_permission(ctx, Permission.USERS_MANAGE, organization_id=assignment.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted to manage users for this organization scope",
        )

    role = await db.get(Role, assignment.role_id)
    db.add(
        AuditLogEntry(
            actor_user_id=ctx.user.id,
            action="user_role.revoke",
            detail={
                "target_user_id": str(user_id),
                "role_name": role.name if role else str(assignment.role_id),
                "organization_id": str(assignment.organization_id) if assignment.organization_id else None,
            },
        )
    )
    await db.delete(assignment)
    await db.commit()
