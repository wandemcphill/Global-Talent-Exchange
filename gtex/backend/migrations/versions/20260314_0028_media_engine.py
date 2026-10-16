"""media engine tables

Revision ID: 20260314_0028
Revises: 20260314_0027
Create Date: 2026-03-14 15:50:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0028'
down_revision = '20260314_0027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'match_views',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('match_key', sa.String(length=120), nullable=False),
        sa.Column('competition_key', sa.String(length=120), nullable=True),
        sa.Column('view_date_key', sa.String(length=16), nullable=False),
        sa.Column('watch_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('premium_unlocked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'match_key', 'view_date_key', name='uq_match_views_user_match_day'),
    )
    op.create_index(op.f('ix_match_views_user_id'), 'match_views', ['user_id'], unique=False)
    op.create_index(op.f('ix_match_views_match_key'), 'match_views', ['match_key'], unique=False)
    op.create_index(op.f('ix_match_views_competition_key'), 'match_views', ['competition_key'], unique=False)
    op.create_index(op.f('ix_match_views_view_date_key'), 'match_views', ['view_date_key'], unique=False)

    op.create_table(
        'premium_video_purchases',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('match_key', sa.String(length=120), nullable=False),
        sa.Column('competition_key', sa.String(length=120), nullable=True),
        sa.Column('price_coin', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('price_fancoin_equivalent', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'match_key', name='uq_premium_video_purchases_user_match'),
    )
    op.create_index(op.f('ix_premium_video_purchases_user_id'), 'premium_video_purchases', ['user_id'], unique=False)
    op.create_index(op.f('ix_premium_video_purchases_match_key'), 'premium_video_purchases', ['match_key'], unique=False)
    op.create_index(op.f('ix_premium_video_purchases_competition_key'), 'premium_video_purchases', ['competition_key'], unique=False)

    op.create_table(
        'match_revenue_snapshots',
        sa.Column('match_key', sa.String(length=120), nullable=False),
        sa.Column('competition_key', sa.String(length=120), nullable=True),
        sa.Column('home_club_id', sa.String(length=36), nullable=True),
        sa.Column('away_club_id', sa.String(length=36), nullable=True),
        sa.Column('total_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('premium_purchases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_revenue_coin', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('home_club_share_coin', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('away_club_share_coin', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['away_club_id'], ['club_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['home_club_id'], ['club_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_key', name='uq_match_revenue_snapshots_match_key'),
    )
    op.create_index(op.f('ix_match_revenue_snapshots_match_key'), 'match_revenue_snapshots', ['match_key'], unique=False)
    op.create_index(op.f('ix_match_revenue_snapshots_competition_key'), 'match_revenue_snapshots', ['competition_key'], unique=False)
    op.create_index(op.f('ix_match_revenue_snapshots_home_club_id'), 'match_revenue_snapshots', ['home_club_id'], unique=False)
    op.create_index(op.f('ix_match_revenue_snapshots_away_club_id'), 'match_revenue_snapshots', ['away_club_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_match_revenue_snapshots_away_club_id'), table_name='match_revenue_snapshots')
    op.drop_index(op.f('ix_match_revenue_snapshots_home_club_id'), table_name='match_revenue_snapshots')
    op.drop_index(op.f('ix_match_revenue_snapshots_competition_key'), table_name='match_revenue_snapshots')
    op.drop_index(op.f('ix_match_revenue_snapshots_match_key'), table_name='match_revenue_snapshots')
    op.drop_table('match_revenue_snapshots')
    op.drop_index(op.f('ix_premium_video_purchases_competition_key'), table_name='premium_video_purchases')
    op.drop_index(op.f('ix_premium_video_purchases_match_key'), table_name='premium_video_purchases')
    op.drop_index(op.f('ix_premium_video_purchases_user_id'), table_name='premium_video_purchases')
    op.drop_table('premium_video_purchases')
    op.drop_index(op.f('ix_match_views_view_date_key'), table_name='match_views')
    op.drop_index(op.f('ix_match_views_competition_key'), table_name='match_views')
    op.drop_index(op.f('ix_match_views_match_key'), table_name='match_views')
    op.drop_index(op.f('ix_match_views_user_id'), table_name='match_views')
    op.drop_table('match_views')
