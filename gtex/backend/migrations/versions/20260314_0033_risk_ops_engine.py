"""risk ops engine

Revision ID: 20260314_0033
Revises: 20260314_0032
Create Date: 2026-03-14 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '20260314_0033'
down_revision = '20260314_0032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'aml_cases',
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('case_key', sa.String(length=96), nullable=False),
        sa.Column('trigger_source', sa.String(length=48), nullable=False, server_default='manual'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='risk_severity', native_enum=False), nullable=False, server_default='medium'),
        sa.Column('status', sa.Enum('open', 'in_review', 'resolved', 'dismissed', name='risk_case_status', native_enum=False), nullable=False, server_default='open'),
        sa.Column('amount_signal', sa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sa.Column('country_code', sa.String(length=8), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('assigned_admin_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aml_cases_case_key'), 'aml_cases', ['case_key'], unique=True)
    op.create_index(op.f('ix_aml_cases_country_code'), 'aml_cases', ['country_code'], unique=False)
    op.create_index(op.f('ix_aml_cases_user_id'), 'aml_cases', ['user_id'], unique=False)
    op.create_index(op.f('ix_aml_cases_assigned_admin_user_id'), 'aml_cases', ['assigned_admin_user_id'], unique=False)
    op.create_index(op.f('ix_aml_cases_resolved_by_user_id'), 'aml_cases', ['resolved_by_user_id'], unique=False)

    op.create_table(
        'fraud_cases',
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('case_key', sa.String(length=96), nullable=False),
        sa.Column('fraud_type', sa.String(length=48), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='risk_severity', native_enum=False), nullable=False, server_default='medium'),
        sa.Column('status', sa.Enum('open', 'in_review', 'resolved', 'dismissed', name='risk_case_status', native_enum=False), nullable=False, server_default='open'),
        sa.Column('confidence_score', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('assigned_admin_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fraud_cases_case_key'), 'fraud_cases', ['case_key'], unique=True)
    op.create_index(op.f('ix_fraud_cases_fraud_type'), 'fraud_cases', ['fraud_type'], unique=False)
    op.create_index(op.f('ix_fraud_cases_user_id'), 'fraud_cases', ['user_id'], unique=False)
    op.create_index(op.f('ix_fraud_cases_assigned_admin_user_id'), 'fraud_cases', ['assigned_admin_user_id'], unique=False)
    op.create_index(op.f('ix_fraud_cases_resolved_by_user_id'), 'fraud_cases', ['resolved_by_user_id'], unique=False)

    op.create_table(
        'system_events',
        sa.Column('event_key', sa.String(length=120), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.Enum('info', 'warning', 'error', 'critical', name='system_event_severity', native_enum=False), nullable=False, server_default='info'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('subject_type', sa.String(length=48), nullable=True),
        sa.Column('subject_id', sa.String(length=64), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_key', name='uq_system_events_event_key')
    )
    op.create_index(op.f('ix_system_events_event_key'), 'system_events', ['event_key'], unique=False)
    op.create_index(op.f('ix_system_events_event_type'), 'system_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_system_events_subject_type'), 'system_events', ['subject_type'], unique=False)
    op.create_index(op.f('ix_system_events_subject_id'), 'system_events', ['subject_id'], unique=False)
    op.create_index(op.f('ix_system_events_created_by_user_id'), 'system_events', ['created_by_user_id'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('actor_user_id', sa.String(length=36), nullable=True),
        sa.Column('action_key', sa.String(length=96), nullable=False),
        sa.Column('resource_type', sa.String(length=48), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('outcome', sa.String(length=24), nullable=False, server_default='success'),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_actor_user_id'), 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action_key'), 'audit_logs', ['action_key'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_resource_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_resource_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action_key'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_user_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index(op.f('ix_system_events_created_by_user_id'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_subject_id'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_subject_type'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_event_type'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_event_key'), table_name='system_events')
    op.drop_table('system_events')

    op.drop_index(op.f('ix_fraud_cases_resolved_by_user_id'), table_name='fraud_cases')
    op.drop_index(op.f('ix_fraud_cases_assigned_admin_user_id'), table_name='fraud_cases')
    op.drop_index(op.f('ix_fraud_cases_user_id'), table_name='fraud_cases')
    op.drop_index(op.f('ix_fraud_cases_fraud_type'), table_name='fraud_cases')
    op.drop_index(op.f('ix_fraud_cases_case_key'), table_name='fraud_cases')
    op.drop_table('fraud_cases')

    op.drop_index(op.f('ix_aml_cases_resolved_by_user_id'), table_name='aml_cases')
    op.drop_index(op.f('ix_aml_cases_assigned_admin_user_id'), table_name='aml_cases')
    op.drop_index(op.f('ix_aml_cases_user_id'), table_name='aml_cases')
    op.drop_index(op.f('ix_aml_cases_country_code'), table_name='aml_cases')
    op.drop_index(op.f('ix_aml_cases_case_key'), table_name='aml_cases')
    op.drop_table('aml_cases')
