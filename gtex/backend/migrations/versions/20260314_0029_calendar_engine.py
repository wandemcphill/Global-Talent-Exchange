"""calendar engine tables

Revision ID: 20260314_0029
Revises: 20260314_0028
Create Date: 2026-03-14 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0029'
down_revision = '20260314_0028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'calendar_seasons',
        sa.Column('season_key', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_key', name='uq_calendar_seasons_season_key'),
    )
    op.create_index(op.f('ix_calendar_seasons_season_key'), 'calendar_seasons', ['season_key'], unique=False)
    op.create_index(op.f('ix_calendar_seasons_starts_on'), 'calendar_seasons', ['starts_on'], unique=False)
    op.create_index(op.f('ix_calendar_seasons_ends_on'), 'calendar_seasons', ['ends_on'], unique=False)
    op.create_index(op.f('ix_calendar_seasons_status'), 'calendar_seasons', ['status'], unique=False)
    op.create_index(op.f('ix_calendar_seasons_active'), 'calendar_seasons', ['active'], unique=False)

    op.create_table(
        'calendar_events',
        sa.Column('season_id', sa.String(length=36), nullable=True),
        sa.Column('event_key', sa.String(length=120), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(length=48), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=True),
        sa.Column('family', sa.String(length=48), nullable=False),
        sa.Column('age_band', sa.String(length=16), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('exclusive_windows', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('pause_other_gtx_competitions', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('visibility', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['season_id'], ['calendar_seasons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_key', name='uq_calendar_events_event_key'),
    )
    op.create_index(op.f('ix_calendar_events_season_id'), 'calendar_events', ['season_id'], unique=False)
    op.create_index(op.f('ix_calendar_events_event_key'), 'calendar_events', ['event_key'], unique=False)
    op.create_index(op.f('ix_calendar_events_source_type'), 'calendar_events', ['source_type'], unique=False)
    op.create_index(op.f('ix_calendar_events_source_id'), 'calendar_events', ['source_id'], unique=False)
    op.create_index(op.f('ix_calendar_events_family'), 'calendar_events', ['family'], unique=False)
    op.create_index(op.f('ix_calendar_events_age_band'), 'calendar_events', ['age_band'], unique=False)
    op.create_index(op.f('ix_calendar_events_starts_on'), 'calendar_events', ['starts_on'], unique=False)
    op.create_index(op.f('ix_calendar_events_ends_on'), 'calendar_events', ['ends_on'], unique=False)
    op.create_index(op.f('ix_calendar_events_status'), 'calendar_events', ['status'], unique=False)

    op.create_table(
        'competition_lifecycle_runs',
        sa.Column('event_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=48), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('source_title', sa.String(length=200), nullable=False),
        sa.Column('competition_format', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('generated_rounds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('generated_matches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scheduled_dates_json', sa.JSON(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('launched_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['calendar_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['launched_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_competition_lifecycle_runs_event_id'), 'competition_lifecycle_runs', ['event_id'], unique=False)
    op.create_index(op.f('ix_competition_lifecycle_runs_source_type'), 'competition_lifecycle_runs', ['source_type'], unique=False)
    op.create_index(op.f('ix_competition_lifecycle_runs_source_id'), 'competition_lifecycle_runs', ['source_id'], unique=False)
    op.create_index(op.f('ix_competition_lifecycle_runs_status'), 'competition_lifecycle_runs', ['status'], unique=False)
    op.create_index(op.f('ix_competition_lifecycle_runs_stage'), 'competition_lifecycle_runs', ['stage'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_competition_lifecycle_runs_stage'), table_name='competition_lifecycle_runs')
    op.drop_index(op.f('ix_competition_lifecycle_runs_status'), table_name='competition_lifecycle_runs')
    op.drop_index(op.f('ix_competition_lifecycle_runs_source_id'), table_name='competition_lifecycle_runs')
    op.drop_index(op.f('ix_competition_lifecycle_runs_source_type'), table_name='competition_lifecycle_runs')
    op.drop_index(op.f('ix_competition_lifecycle_runs_event_id'), table_name='competition_lifecycle_runs')
    op.drop_table('competition_lifecycle_runs')

    op.drop_index(op.f('ix_calendar_events_status'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_ends_on'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_starts_on'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_age_band'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_family'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_source_id'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_source_type'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_event_key'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_season_id'), table_name='calendar_events')
    op.drop_table('calendar_events')

    op.drop_index(op.f('ix_calendar_seasons_active'), table_name='calendar_seasons')
    op.drop_index(op.f('ix_calendar_seasons_status'), table_name='calendar_seasons')
    op.drop_index(op.f('ix_calendar_seasons_ends_on'), table_name='calendar_seasons')
    op.drop_index(op.f('ix_calendar_seasons_starts_on'), table_name='calendar_seasons')
    op.drop_index(op.f('ix_calendar_seasons_season_key'), table_name='calendar_seasons')
    op.drop_table('calendar_seasons')
