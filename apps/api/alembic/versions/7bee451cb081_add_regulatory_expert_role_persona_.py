"""add regulatory_expert role, persona, verification_status

Revision ID: 7bee451cb081
Revises: 3cc1ab7c7f05
Create Date: 2026-09-15 12:52:10.431604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bee451cb081'
down_revision: Union[str, None] = '3cc1ab7c7f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Autogenerate does not detect added enum members - added by hand.
    # Must run outside the migration's transaction block: Postgres allows
    # ALTER TYPE ... ADD VALUE inside a transaction (PG12+), but the new
    # value cannot be used by any statement in that same transaction -
    # irrelevant here since nothing in this migration inserts a row using
    # it, but AUTOCOMMIT sidesteps the restriction entirely and is safer.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'regulatory_expert'")

    op.add_column('users', sa.Column('persona', sa.String(), nullable=True))

    # ADD COLUMN with an inline Enum does not auto-create the Postgres
    # type the way create_table does - create it explicitly first.
    verification_status_enum = sa.Enum('approved', 'pending', 'rejected', name='verification_status')
    verification_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('verification_status', verification_status_enum, server_default='approved', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'verification_status')
    op.drop_column('users', 'persona')
    sa.Enum(name='verification_status').drop(op.get_bind(), checkfirst=True)
    # Postgres has no DROP VALUE for enums - removing 'regulatory_expert'
    # would require recreating the type. Not done here: downgrading a
    # dev/hackathon migration that added an enum member is not a real
    # need, and forcing a type-recreate for it would risk data loss on a
    # table that isn't empty.
