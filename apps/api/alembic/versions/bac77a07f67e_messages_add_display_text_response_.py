"""messages: add display_text, response_json for chat history view

Revision ID: bac77a07f67e
Revises: a9ef26176043
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'bac77a07f67e'
down_revision: Union[str, None] = 'a9ef26176043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('display_text', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('response_json', JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'response_json')
    op.drop_column('messages', 'display_text')
