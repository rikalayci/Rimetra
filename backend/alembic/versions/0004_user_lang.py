"""users.lang: interface / Telegram language preference

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('lang', sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'lang')
