"""telegram bot: user link fields + one-time link codes

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03 20:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('telegram_chat_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('telegram_username', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('telegram_linked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('telegram_notify', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('users', sa.Column('telegram_member_id', sa.String(length=32), nullable=True))
    op.create_unique_constraint('users_telegram_chat_id_key', 'users', ['telegram_chat_id'])
    op.create_table(
        'telegram_link_codes',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=32), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_telegram_link_codes_user_id', 'telegram_link_codes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_telegram_link_codes_user_id', table_name='telegram_link_codes')
    op.drop_table('telegram_link_codes')
    op.drop_constraint('users_telegram_chat_id_key', 'users', type_='unique')
    for c in ('telegram_member_id', 'telegram_notify', 'telegram_linked_at', 'telegram_username', 'telegram_chat_id'):
        op.drop_column('users', c)
