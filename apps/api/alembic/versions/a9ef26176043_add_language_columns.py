"""add language columns: users.preferred_language, conversations.language, messages.language

Revision ID: a9ef26176043
Revises: 6134f0419df7
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9ef26176043'
down_revision: Union[str, None] = '6134f0419df7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('preferred_language', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('language', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('language', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'language')
    op.drop_column('conversations', 'language')
    op.drop_column('users', 'preferred_language')
