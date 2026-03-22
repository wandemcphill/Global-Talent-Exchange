"""sponsorship and creator campaign engines

Revision ID: 20260314_0034
Revises: 20260314_0033
Create Date: 2026-03-14 19:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0034'
down_revision = '20260314_0033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sponsorship_leads',
        sa.Column('contract_id', sa.String(length=36), nullable=True),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('requester_user_id', sa.String(length=36), nullable=False),
        sa.Column('sponsor_name', sa.String(length=120), nullable=False),
        sa.Column('sponsor_email', sa.String(length=255), nullable=True),
        sa.Column('sponsor_company', sa.String(length=120), nullable=True),
        sa.Column('asset_type', sa.String(length=48), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='submitted'),
        sa.Column('proposal_note', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['club_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_id'], ['club_sponsorship_contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requester_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_id', name='uq_sponsorship_leads_contract_id'),
    )
    op.create_index(op.f('ix_sponsorship_leads_contract_id'), 'sponsorship_leads', ['contract_id'], unique=False)
    op.create_index(op.f('ix_sponsorship_leads_club_id'), 'sponsorship_leads', ['club_id'], unique=False)
    op.create_index(op.f('ix_sponsorship_leads_requester_user_id'), 'sponsorship_leads', ['requester_user_id'], unique=False)
    op.create_index(op.f('ix_sponsorship_leads_asset_type'), 'sponsorship_leads', ['asset_type'], unique=False)
    op.create_index(op.f('ix_sponsorship_leads_reviewed_by_user_id'), 'sponsorship_leads', ['reviewed_by_user_id'], unique=False)

    op.create_table(
        'creator_campaign_metric_snapshots',
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('attributed_signups', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified_signups', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qualified_joins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gifts_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gift_volume_minor', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rewards_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reward_volume_minor', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('competition_entries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['creator_campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'snapshot_date', name='uq_campaign_metric_snapshots_campaign_date'),
    )
    op.create_index(op.f('ix_creator_campaign_metric_snapshots_campaign_id'), 'creator_campaign_metric_snapshots', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_creator_campaign_metric_snapshots_snapshot_date'), 'creator_campaign_metric_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_creator_campaign_metric_snapshots_snapshot_date'), table_name='creator_campaign_metric_snapshots')
    op.drop_index(op.f('ix_creator_campaign_metric_snapshots_campaign_id'), table_name='creator_campaign_metric_snapshots')
    op.drop_table('creator_campaign_metric_snapshots')

    op.drop_index(op.f('ix_sponsorship_leads_reviewed_by_user_id'), table_name='sponsorship_leads')
    op.drop_index(op.f('ix_sponsorship_leads_asset_type'), table_name='sponsorship_leads')
    op.drop_index(op.f('ix_sponsorship_leads_requester_user_id'), table_name='sponsorship_leads')
    op.drop_index(op.f('ix_sponsorship_leads_club_id'), table_name='sponsorship_leads')
    op.drop_index(op.f('ix_sponsorship_leads_contract_id'), table_name='sponsorship_leads')
    op.drop_table('sponsorship_leads')
