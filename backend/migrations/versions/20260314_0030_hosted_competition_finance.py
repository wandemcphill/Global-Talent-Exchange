"""hosted competition finance and standings

Revision ID: 20260314_0030
Revises: 20260314_0029
Create Date: 2026-03-14 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0030'
down_revision = '20260314_0029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hosted_competition_standings',
        sa.Column('competition_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('final_rank', sa.Integer(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('draws', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('goals_for', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('goals_against', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payout_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['user_hosted_competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competition_id', 'user_id', name='uq_hosted_competition_standing_user'),
    )
    op.create_index(op.f('ix_hosted_competition_standings_competition_id'), 'hosted_competition_standings', ['competition_id'], unique=False)
    op.create_index(op.f('ix_hosted_competition_standings_user_id'), 'hosted_competition_standings', ['user_id'], unique=False)

    op.create_table(
        'hosted_competition_settlements',
        sa.Column('competition_id', sa.String(length=36), nullable=False),
        sa.Column('recipient_user_id', sa.String(length=36), nullable=True),
        sa.Column('settlement_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SETTLED', 'VOIDED', name='hostedcompetitionsettlementstatus', native_enum=False), nullable=False),
        sa.Column('gross_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('platform_fee_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('net_amount', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('ledger_transaction_id', sa.String(length=36), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('settled_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['user_hosted_competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['settled_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_hosted_competition_settlements_competition_id'), 'hosted_competition_settlements', ['competition_id'], unique=False)
    op.create_index(op.f('ix_hosted_competition_settlements_recipient_user_id'), 'hosted_competition_settlements', ['recipient_user_id'], unique=False)
    op.create_index(op.f('ix_hosted_competition_settlements_ledger_transaction_id'), 'hosted_competition_settlements', ['ledger_transaction_id'], unique=False)
    op.create_index(op.f('ix_hosted_competition_settlements_settled_by_user_id'), 'hosted_competition_settlements', ['settled_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_hosted_competition_settlements_settled_by_user_id'), table_name='hosted_competition_settlements')
    op.drop_index(op.f('ix_hosted_competition_settlements_ledger_transaction_id'), table_name='hosted_competition_settlements')
    op.drop_index(op.f('ix_hosted_competition_settlements_recipient_user_id'), table_name='hosted_competition_settlements')
    op.drop_index(op.f('ix_hosted_competition_settlements_competition_id'), table_name='hosted_competition_settlements')
    op.drop_table('hosted_competition_settlements')

    op.drop_index(op.f('ix_hosted_competition_standings_user_id'), table_name='hosted_competition_standings')
    op.drop_index(op.f('ix_hosted_competition_standings_competition_id'), table_name='hosted_competition_standings')
    op.drop_table('hosted_competition_standings')
