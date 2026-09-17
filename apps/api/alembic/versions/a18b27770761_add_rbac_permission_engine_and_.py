"""add rbac permission engine and organizations

Adds the Role/Permission/RolePermission/UserRoleAssignment/Organization/
OrganizationMember schema (docs/product/rbac-full-implementation-spec.md
Sections 2-4), seeds it from app.authz.constants, and backfills every
existing `users.role` value into the new `user_roles` table so no
existing account loses access when routers switch from `require_role`
(reads `users.role`) to `require_permission` (reads `user_roles`).

`users.role` itself is left in place (expand->migrate->contract, spec
Section 2) - dropped in a later migration once nothing reads it.

Revision ID: a18b27770761
Revises: bac77a07f67e
Create Date: 2026-09-16 12:45:49.713595

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a18b27770761'
down_revision: Union[str, None] = 'bac77a07f67e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- organizations ------------------------------------------------
    # create_type=True (default) lets op.create_table create this enum
    # type as part of the table DDL - an explicit separate .create() call
    # here would double-create it (CREATE TYPE run twice) since
    # create_table doesn't know about a prior manual call.
    organization_type = sa.Enum("institution", "startup", "other", name="organization_type")

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("org_type", organization_type, nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "organization_members",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "organization_id", name="ux_org_member"),
    )

    # -- permission engine ---------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(), nullable=False, unique=True),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", sa.Uuid(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="ux_role_permission"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Nullable organization_id can't be part of a plain unique constraint
    # the way a NOT NULL composite key could - two partial unique indexes
    # instead (spec Section 2): one for org-scoped grants, one for
    # platform-wide (NULL-org) grants.
    op.create_index(
        "ux_user_role_scoped", "user_roles", ["user_id", "role_id", "organization_id"],
        unique=True, postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "ux_user_role_unscoped", "user_roles", ["user_id", "role_id"],
        unique=True, postgresql_where=sa.text("organization_id IS NULL"),
    )

    _seed_and_backfill()


def _seed_and_backfill() -> None:
    from app.authz.constants import PERMISSION_CATALOG, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS

    bind = op.get_bind()

    roles_t = sa.table(
        "roles", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String),
        sa.column("description", sa.String),
    )
    permissions_t = sa.table(
        "permissions", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("key", sa.String),
        sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("description", sa.String),
    )
    role_permissions_t = sa.table(
        "role_permissions", sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("role_id", sa.Uuid(as_uuid=True)), sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    user_roles_t = sa.table(
        "user_roles", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("user_id", sa.Uuid(as_uuid=True)),
        sa.column("role_id", sa.Uuid(as_uuid=True)), sa.column("organization_id", sa.Uuid(as_uuid=True)),
    )

    role_id_by_name: dict[str, uuid.UUID] = {}
    role_rows = []
    for name, description in ROLE_DESCRIPTIONS.items():
        role_id = uuid.uuid4()
        role_id_by_name[name] = role_id
        role_rows.append({"id": role_id, "name": name, "description": description})
    op.bulk_insert(roles_t, role_rows)

    permission_id_by_key: dict[str, uuid.UUID] = {}
    permission_rows = []
    for key, resource, action, description in PERMISSION_CATALOG:
        permission_id = uuid.uuid4()
        permission_id_by_key[key] = permission_id
        permission_rows.append(
            {"id": permission_id, "key": key, "resource": resource, "action": action, "description": description}
        )
    op.bulk_insert(permissions_t, permission_rows)

    grant_rows = []
    for role_name, permission_keys in ROLE_PERMISSIONS.items():
        role_id = role_id_by_name[role_name]
        for key in permission_keys:
            grant_rows.append({"id": uuid.uuid4(), "role_id": role_id, "permission_id": permission_id_by_key[key]})
    op.bulk_insert(role_permissions_t, grant_rows)

    # Backfill: every existing user gets one platform-wide user_roles row
    # matching their legacy `users.role` value. `admin` maps to
    # `ministry_admin` - the superset of today's unrestricted admin
    # behavior, flagged in the spec (Section 2) for manual post-migration
    # review since the flat `admin` role never distinguished
    # institutional/ministry/KB scope.
    legacy_role_map = {
        "user": "user",
        "facilitator": "facilitator",
        "regulatory_expert": "regulatory_expert",
        "admin": "ministry_admin",
    }
    existing_users = bind.execute(sa.text("SELECT id, role FROM users")).fetchall()
    backfill_rows = []
    for user_id, legacy_role in existing_users:
        mapped_role_name = legacy_role_map.get(legacy_role)
        if mapped_role_name is None:
            continue
        backfill_rows.append(
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role_id": role_id_by_name[mapped_role_name],
                "organization_id": None,
            }
        )
    if backfill_rows:
        op.bulk_insert(user_roles_t, backfill_rows)


def downgrade() -> None:
    op.drop_index("ux_user_role_unscoped", table_name="user_roles")
    op.drop_index("ux_user_role_scoped", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    sa.Enum(name="organization_type").drop(op.get_bind(), checkfirst=True)
