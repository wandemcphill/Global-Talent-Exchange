"""daily challenges and hosted competitions

Revision ID: 20260314_0026
Revises: 20260314_0025
Create Date: 2026-03-14 15:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260314_0026'
down_revision = '20260314_0025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    challenge_status = sa.Enum('ACTIVE', 'INACTIVE', name='dailychallengestatus')
    hosted_status = sa.Enum('DRAFT', 'OPEN', 'LOCKED', 'LIVE', 'COMPLETED', 'CANCELLED', name='hostedcompetitionstatus')
    bind = op.get_bind()
    challenge_status.create(bind, checkfirst=True)
    hosted_status.create(bind, checkfirst=True)

    op.create_table(
        'daily_challenges',
        sa.Column('challenge_key', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reward_amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('reward_unit', sa.String(length=16), nullable=False),
        sa.Column('claim_limit_per_day', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('status', challenge_status, nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_challenges')),
        sa.UniqueConstraint('challenge_key', name='uq_daily_challenges_challenge_key'),
    )

    op.create_table(
        'daily_challenge_claims',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('challenge_id', sa.String(length=36), nullable=False),
        sa.Column('claim_date', sa.Date(), nullable=False),
        sa.Column('reward_amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('reward_unit', sa.String(length=16), nullable=False),
        sa.Column('reward_settlement_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['challenge_id'], ['daily_challenges.id'], name=op.f('fk_daily_challenge_claims_challenge_id_daily_challenges'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reward_settlement_id'], ['reward_settlements.id'], name=op.f('fk_daily_challenge_claims_reward_settlement_id_reward_settlements'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_daily_challenge_claims_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_challenge_claims')),
        sa.UniqueConstraint('user_id', 'challenge_id', 'claim_date', name='uq_daily_challenge_claims_user_challenge_date'),
    )
    op.create_index(op.f('ix_daily_challenge_claims_user_id'), 'daily_challenge_claims', ['user_id'], unique=False)
    op.create_index(op.f('ix_daily_challenge_claims_challenge_id'), 'daily_challenge_claims', ['challenge_id'], unique=False)
    op.create_index(op.f('ix_daily_challenge_claims_claim_date'), 'daily_challenge_claims', ['claim_date'], unique=False)

    op.create_table(
        'competition_templates',
        sa.Column('template_key', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('competition_type', sa.String(length=80), nullable=False),
        sa.Column('team_type', sa.String(length=80), nullable=False),
        sa.Column('age_grade', sa.String(length=40), nullable=False),
        sa.Column('cup_or_league', sa.String(length=24), nullable=False),
        sa.Column('participants', sa.Integer(), nullable=False),
        sa.Column('viewing_mode', sa.String(length=40), nullable=False),
        sa.Column('gift_rules', sa.JSON(), nullable=False),
        sa.Column('seeding_method', sa.String(length=40), nullable=False),
        sa.Column('is_user_hostable', sa.Boolean(), nullable=False),
        sa.Column('entry_fee_fancoin', sa.Numeric(18, 4), nullable=False),
        sa.Column('reward_pool_fancoin', sa.Numeric(18, 4), nullable=False),
        sa.Column('platform_fee_bps', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_competition_templates')),
        sa.UniqueConstraint('template_key', name='uq_competition_templates_template_key'),
    )

    op.create_table(
        'user_hosted_competitions',
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('host_user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('slug', sa.String(length=180), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', hosted_status, nullable=False),
        sa.Column('visibility', sa.String(length=24), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lock_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_participants', sa.Integer(), nullable=False),
        sa.Column('entry_fee_fancoin', sa.Numeric(18, 4), nullable=False),
        sa.Column('reward_pool_fancoin', sa.Numeric(18, 4), nullable=False),
        sa.Column('platform_fee_amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], name=op.f('fk_user_hosted_competitions_host_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['competition_templates.id'], name=op.f('fk_user_hosted_competitions_template_id_competition_templates'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_hosted_competitions')),
    )
    op.create_index(op.f('ix_user_hosted_competitions_host_user_id'), 'user_hosted_competitions', ['host_user_id'], unique=False)
    op.create_index(op.f('ix_user_hosted_competitions_slug'), 'user_hosted_competitions', ['slug'], unique=True)
    op.create_index(op.f('ix_user_hosted_competitions_template_id'), 'user_hosted_competitions', ['template_id'], unique=False)

    op.create_table(
        'user_hosted_competition_participants',
        sa.Column('competition_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_fee_fancoin', sa.Numeric(18, 4), nullable=False),
        sa.Column('payout_eligible', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['user_hosted_competitions.id'], name=op.f('fk_user_hosted_competition_participants_competition_id_user_hosted_competitions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_hosted_competition_participants_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_hosted_competition_participants')),
        sa.UniqueConstraint('competition_id', 'user_id', name='uq_hosted_competition_participant_user'),
    )
    op.create_index(op.f('ix_user_hosted_competition_participants_competition_id'), 'user_hosted_competition_participants', ['competition_id'], unique=False)
    op.create_index(op.f('ix_user_hosted_competition_participants_user_id'), 'user_hosted_competition_participants', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_hosted_competition_participants_user_id'), table_name='user_hosted_competition_participants')
    op.drop_index(op.f('ix_user_hosted_competition_participants_competition_id'), table_name='user_hosted_competition_participants')
    op.drop_table('user_hosted_competition_participants')
    op.drop_index(op.f('ix_user_hosted_competitions_template_id'), table_name='user_hosted_competitions')
    op.drop_index(op.f('ix_user_hosted_competitions_slug'), table_name='user_hosted_competitions')
    op.drop_index(op.f('ix_user_hosted_competitions_host_user_id'), table_name='user_hosted_competitions')
    op.drop_table('user_hosted_competitions')
    op.drop_table('competition_templates')
    op.drop_index(op.f('ix_daily_challenge_claims_claim_date'), table_name='daily_challenge_claims')
    op.drop_index(op.f('ix_daily_challenge_claims_challenge_id'), table_name='daily_challenge_claims')
    op.drop_index(op.f('ix_daily_challenge_claims_user_id'), table_name='daily_challenge_claims')
    op.drop_table('daily_challenge_claims')
    op.drop_table('daily_challenges')
    sa.Enum(name='hostedcompetitionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='dailychallengestatus').drop(op.get_bind(), checkfirst=True)
