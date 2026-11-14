"""test definitions: plain-language info fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('test_definitions', sa.Column('info_what', sa.Text(), nullable=True))
    op.add_column('test_definitions', sa.Column('info_low', sa.Text(), nullable=True))
    op.add_column('test_definitions', sa.Column('info_high', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('test_definitions', 'info_high')
    op.drop_column('test_definitions', 'info_low')
    op.drop_column('test_definitions', 'info_what')
