"""Idempotent seed for roles/permissions/role_permissions from
app.authz.constants. Called from the Alembic migration that introduces
these tables (data migration, same revision as the schema change - a
permission engine with no seeded rows authorizes nothing) and re-runnable
standalone (`python -m app.authz.seed`) after any change to
constants.ROLE_PERMISSIONS, since it upserts rather than only-inserts.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authz.constants import PERMISSION_CATALOG, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from app.db.models import Permission, Role, RolePermission


async def seed_authz(db: AsyncSession) -> None:
    role_by_name: dict[str, Role] = {}
    existing_roles = await db.execute(select(Role))
    for role in existing_roles.scalars().all():
        role_by_name[role.name] = role

    for name, description in ROLE_DESCRIPTIONS.items():
        if name not in role_by_name:
            role = Role(name=name, description=description)
            db.add(role)
            role_by_name[name] = role
        else:
            role_by_name[name].description = description

    permission_by_key: dict[str, Permission] = {}
    existing_permissions = await db.execute(select(Permission))
    for permission in existing_permissions.scalars().all():
        permission_by_key[permission.key] = permission

    for key, resource, action, description in PERMISSION_CATALOG:
        if key not in permission_by_key:
            permission = Permission(key=key, resource=resource, action=action, description=description)
            db.add(permission)
            permission_by_key[key] = permission
        else:
            perm = permission_by_key[key]
            perm.resource = resource
            perm.action = action
            perm.description = description

    # Flush so the new Role/Permission rows have ids before RolePermission
    # rows reference them.
    await db.flush()

    existing_grants = await db.execute(select(RolePermission.role_id, RolePermission.permission_id))
    existing_pairs = {(role_id, permission_id) for role_id, permission_id in existing_grants.all()}

    wanted_pairs: set[tuple] = set()
    for role_name, permission_keys in ROLE_PERMISSIONS.items():
        role = role_by_name[role_name]
        for key in permission_keys:
            permission = permission_by_key[key]
            wanted_pairs.add((role.id, permission.id))

    for role_id, permission_id in wanted_pairs - existing_pairs:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))

    stale_pairs = existing_pairs - wanted_pairs
    if stale_pairs:
        stale_rows = await db.execute(select(RolePermission))
        for row in stale_rows.scalars().all():
            if (row.role_id, row.permission_id) in stale_pairs:
                await db.delete(row)

    await db.commit()


async def _main() -> None:
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await seed_authz(db)
    print(f"Seeded {len(ROLE_DESCRIPTIONS)} roles, {len(PERMISSION_CATALOG)} permissions.")


if __name__ == "__main__":
    asyncio.run(_main())
