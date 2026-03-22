"""discovery engine and notification center preferences

Revision ID: 20260314_0032
Revises: 20260314_0031
Create Date: 2026-03-14 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0032'
down_revision = '20260314_0031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'saved_searches',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('query', sa.String(length=180), nullable=False),
        sa.Column('entity_scope', sa.String(length=48), nullable=False),
        sa.Column('alerts_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'query', name='uq_saved_search_user_query'),
    )
    op.create_index(op.f('ix_saved_searches_user_id'), 'saved_searches', ['user_id'], unique=False)
    op.create_index(op.f('ix_saved_searches_query'), 'saved_searches', ['query'], unique=False)

    op.create_table(
        'featured_rails',
        sa.Column('rail_key', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('rail_type', sa.String(length=48), nullable=False),
        sa.Column('audience', sa.String(length=32), nullable=False),
        sa.Column('query_hint', sa.String(length=180), nullable=True),
        sa.Column('subtitle', sa.Text(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rail_key', name='uq_featured_rails_key'),
    )
    op.create_index(op.f('ix_featured_rails_rail_key'), 'featured_rails', ['rail_key'], unique=False)
    op.create_index(op.f('ix_featured_rails_created_by_user_id'), 'featured_rails', ['created_by_user_id'], unique=False)

    op.create_table(
        'notification_preferences',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('allow_wallet', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_market', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_story', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_competition', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_social', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_broadcasts', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_notification_preferences_user'),
    )
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

    op.create_table(
        'notification_subscriptions',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('subscription_key', sa.String(length=140), nullable=False),
        sa.Column('subscription_type', sa.String(length=48), nullable=False),
        sa.Column('label', sa.String(length=180), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subscription_key', name='uq_notification_subscriptions_user_key'),
    )
    op.create_index(op.f('ix_notification_subscriptions_user_id'), 'notification_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_notification_subscriptions_subscription_key'), 'notification_subscriptions', ['subscription_key'], unique=False)

    op.create_table(
        'platform_announcements',
        sa.Column('announcement_key', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('audience', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.String(length=24), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('deliver_as_notification', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('published_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['published_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('announcement_key'),
    )
    op.create_index(op.f('ix_platform_announcements_announcement_key'), 'platform_announcements', ['announcement_key'], unique=True)
    op.create_index(op.f('ix_platform_announcements_published_by_user_id'), 'platform_announcements', ['published_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_platform_announcements_published_by_user_id'), table_name='platform_announcements')
    op.drop_index(op.f('ix_platform_announcements_announcement_key'), table_name='platform_announcements')
    op.drop_table('platform_announcements')

    op.drop_index(op.f('ix_notification_subscriptions_subscription_key'), table_name='notification_subscriptions')
    op.drop_index(op.f('ix_notification_subscriptions_user_id'), table_name='notification_subscriptions')
    op.drop_table('notification_subscriptions')

    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')

    op.drop_index(op.f('ix_featured_rails_created_by_user_id'), table_name='featured_rails')
    op.drop_index(op.f('ix_featured_rails_rail_key'), table_name='featured_rails')
    op.drop_table('featured_rails')

    op.drop_index(op.f('ix_saved_searches_query'), table_name='saved_searches')
    op.drop_index(op.f('ix_saved_searches_user_id'), table_name='saved_searches')
    op.drop_table('saved_searches')
