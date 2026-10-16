"""community engine threads, watchlists, and private messages

Revision ID: 20260314_0031
Revises: 20260314_0030
Create Date: 2026-03-14 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0031'
down_revision = '20260314_0030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'competition_watchlists',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('competition_key', sa.String(length=120), nullable=False),
        sa.Column('competition_title', sa.String(length=180), nullable=False),
        sa.Column('competition_type', sa.String(length=80), nullable=False),
        sa.Column('notify_on_story', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notify_on_launch', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'competition_key', name='uq_competition_watchlists_user_competition'),
    )
    op.create_index(op.f('ix_competition_watchlists_user_id'), 'competition_watchlists', ['user_id'], unique=False)
    op.create_index(op.f('ix_competition_watchlists_competition_key'), 'competition_watchlists', ['competition_key'], unique=False)

    op.create_table(
        'live_threads',
        sa.Column('thread_key', sa.String(length=140), nullable=False),
        sa.Column('competition_key', sa.String(length=120), nullable=True),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'LOCKED', 'ARCHIVED', name='livethreadstatus', native_enum=False), nullable=False),
        sa.Column('pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_key'),
    )
    op.create_index(op.f('ix_live_threads_thread_key'), 'live_threads', ['thread_key'], unique=True)
    op.create_index(op.f('ix_live_threads_competition_key'), 'live_threads', ['competition_key'], unique=False)
    op.create_index(op.f('ix_live_threads_created_by_user_id'), 'live_threads', ['created_by_user_id'], unique=False)

    op.create_table(
        'live_thread_messages',
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('author_user_id', sa.String(length=36), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('visibility', sa.Enum('PUBLIC', 'MOD_REVIEW', 'HIDDEN', name='communitymessagevisibility', native_enum=False), nullable=False),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reply_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['live_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_live_thread_messages_thread_id'), 'live_thread_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_live_thread_messages_author_user_id'), 'live_thread_messages', ['author_user_id'], unique=False)

    op.create_table(
        'private_message_threads',
        sa.Column('thread_key', sa.String(length=140), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'ARCHIVED', 'BLOCKED', name='privatemessagethreadstatus', native_enum=False), nullable=False),
        sa.Column('subject', sa.String(length=180), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_key'),
    )
    op.create_index(op.f('ix_private_message_threads_thread_key'), 'private_message_threads', ['thread_key'], unique=True)
    op.create_index(op.f('ix_private_message_threads_created_by_user_id'), 'private_message_threads', ['created_by_user_id'], unique=False)

    op.create_table(
        'private_message_participants',
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['private_message_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id', 'user_id', name='uq_private_message_participant_thread_user'),
    )
    op.create_index(op.f('ix_private_message_participants_thread_id'), 'private_message_participants', ['thread_id'], unique=False)
    op.create_index(op.f('ix_private_message_participants_user_id'), 'private_message_participants', ['user_id'], unique=False)

    op.create_table(
        'private_messages',
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('sender_user_id', sa.String(length=36), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['private_message_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_private_messages_thread_id'), 'private_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_private_messages_sender_user_id'), 'private_messages', ['sender_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_private_messages_sender_user_id'), table_name='private_messages')
    op.drop_index(op.f('ix_private_messages_thread_id'), table_name='private_messages')
    op.drop_table('private_messages')

    op.drop_index(op.f('ix_private_message_participants_user_id'), table_name='private_message_participants')
    op.drop_index(op.f('ix_private_message_participants_thread_id'), table_name='private_message_participants')
    op.drop_table('private_message_participants')

    op.drop_index(op.f('ix_private_message_threads_created_by_user_id'), table_name='private_message_threads')
    op.drop_index(op.f('ix_private_message_threads_thread_key'), table_name='private_message_threads')
    op.drop_table('private_message_threads')

    op.drop_index(op.f('ix_live_thread_messages_author_user_id'), table_name='live_thread_messages')
    op.drop_index(op.f('ix_live_thread_messages_thread_id'), table_name='live_thread_messages')
    op.drop_table('live_thread_messages')

    op.drop_index(op.f('ix_live_threads_created_by_user_id'), table_name='live_threads')
    op.drop_index(op.f('ix_live_threads_competition_key'), table_name='live_threads')
    op.drop_index(op.f('ix_live_threads_thread_key'), table_name='live_threads')
    op.drop_table('live_threads')

    op.drop_index(op.f('ix_competition_watchlists_competition_key'), table_name='competition_watchlists')
    op.drop_index(op.f('ix_competition_watchlists_user_id'), table_name='competition_watchlists')
    op.drop_table('competition_watchlists')
