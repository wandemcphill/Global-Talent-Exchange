"""player import and club infrastructure

Revision ID: 20260314_0027
Revises: 20260314_0026
Create Date: 2026-03-14 15:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '20260314_0027'
down_revision = '20260314_0026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'club_stadiums',
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('theme_key', sa.String(length=64), nullable=False, server_default='default'),
        sa.Column('gift_retention_bonus_bps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revenue_multiplier_bps', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('prestige_bonus_bps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['club_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', name='uq_club_stadiums_club_id'),
    )
    op.create_index(op.f('ix_club_stadiums_club_id'), 'club_stadiums', ['club_id'], unique=False)

    op.create_table(
        'club_facilities',
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('training_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('academy_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('medical_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('branding_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('upkeep_cost_fancoin', sa.Numeric(18,4), nullable=False, server_default='0'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['club_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', name='uq_club_facilities_club_id'),
    )
    op.create_index(op.f('ix_club_facilities_club_id'), 'club_facilities', ['club_id'], unique=False)

    op.create_table(
        'club_supporter_tokens',
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('token_name', sa.String(length=120), nullable=False),
        sa.Column('token_symbol', sa.String(length=16), nullable=False),
        sa.Column('circulating_supply', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('holder_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('influence_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('ACTIVE', 'PAUSED', name='supportertokenstatus'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['club_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', name='uq_club_supporter_tokens_club_id'),
    )
    op.create_index(op.f('ix_club_supporter_tokens_club_id'), 'club_supporter_tokens', ['club_id'], unique=False)

    op.create_table(
        'club_supporter_holdings',
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('influence_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_founding_supporter', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['club_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'user_id', name='uq_club_supporter_holdings_club_user'),
    )
    op.create_index(op.f('ix_club_supporter_holdings_club_id'), 'club_supporter_holdings', ['club_id'], unique=False)
    op.create_index(op.f('ix_club_supporter_holdings_user_id'), 'club_supporter_holdings', ['user_id'], unique=False)

    op.create_table(
        'player_import_jobs',
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_label', sa.String(length=120), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PROCESSED', 'PARTIAL', 'FAILED', name='playerimportjobstatus'), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_player_import_jobs_created_by_user_id'), 'player_import_jobs', ['created_by_user_id'], unique=False)

    op.create_table(
        'player_import_items',
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('external_source_id', sa.String(length=128), nullable=True),
        sa.Column('player_name', sa.String(length=160), nullable=True),
        sa.Column('normalized_position', sa.String(length=32), nullable=True),
        sa.Column('nationality_code', sa.String(length=12), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('VALID', 'INVALID', 'IMPORTED', 'SKIPPED', name='playerimportitemstatus'), nullable=False),
        sa.Column('validation_errors_json', sa.JSON(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('linked_player_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['player_import_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_player_id'], ['ingestion_players.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'row_number', name='uq_player_import_items_job_row'),
    )
    op.create_index(op.f('ix_player_import_items_job_id'), 'player_import_items', ['job_id'], unique=False)
    op.create_index(op.f('ix_player_import_items_linked_player_id'), 'player_import_items', ['linked_player_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_player_import_items_linked_player_id'), table_name='player_import_items')
    op.drop_index(op.f('ix_player_import_items_job_id'), table_name='player_import_items')
    op.drop_table('player_import_items')
    op.drop_index(op.f('ix_player_import_jobs_created_by_user_id'), table_name='player_import_jobs')
    op.drop_table('player_import_jobs')
    op.drop_index(op.f('ix_club_supporter_holdings_user_id'), table_name='club_supporter_holdings')
    op.drop_index(op.f('ix_club_supporter_holdings_club_id'), table_name='club_supporter_holdings')
    op.drop_table('club_supporter_holdings')
    op.drop_index(op.f('ix_club_supporter_tokens_club_id'), table_name='club_supporter_tokens')
    op.drop_table('club_supporter_tokens')
    op.drop_index(op.f('ix_club_facilities_club_id'), table_name='club_facilities')
    op.drop_table('club_facilities')
    op.drop_index(op.f('ix_club_stadiums_club_id'), table_name='club_stadiums')
    op.drop_table('club_stadiums')
