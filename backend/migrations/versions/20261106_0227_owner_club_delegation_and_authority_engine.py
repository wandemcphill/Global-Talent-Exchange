"""Create owner club delegation policies and delegated decisions tables for Phase 1D.

Revision ID: 20261106_0227_owner_club_delegation_and_authority_engine
Revises: 20261105_0226_phase2_4_relationship_pair_uniqueness
Create Date: 2026-11-06 14:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261106_0227_owner_club_delegation_and_authority_engine"
down_revision = "20261105_0226_phase2_4_relationship_pair_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "owner_club_delegation_policies" not in tables:
        op.create_table(
            "owner_club_delegation_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("owner_user_id", sa.String(36), nullable=False),
            sa.Column("mode", sa.String(32), nullable=False, server_default="balanced"),
            sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("suspension_reason", sa.String(255), nullable=True),
            sa.Column("financial_thresholds_json", sa.JSON(), nullable=False),
            sa.Column("activity_assignments_json", sa.JSON(), nullable=False),
            sa.Column("reserved_decisions_json", sa.JSON(), nullable=False),
            sa.Column("temporary_overrides_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_owner_club_delegation_policies_club_id",
            "owner_club_delegation_policies",
            ["club_id"],
            unique=True,
        )
        op.create_index(
            "ix_owner_club_delegation_policies_owner_user_id",
            "owner_club_delegation_policies",
            ["owner_user_id"],
        )

    if "owner_club_delegated_decisions" not in tables:
        op.create_table(
            "owner_club_delegated_decisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("owner_user_id", sa.String(36), nullable=False),
            sa.Column("activity_key", sa.String(64), nullable=False),
            sa.Column("domain", sa.String(32), nullable=False, server_default="sporting"),
            sa.Column("proposed_by_role", sa.String(40), nullable=False),
            sa.Column("proposed_by_staff_name", sa.String(120), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("financial_amount_gtex", sa.Numeric(20, 2), nullable=True),
            sa.Column("requires_owner_approval", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("approval_reason", sa.String(255), nullable=True),
            sa.Column("status", sa.String(24), nullable=False, server_default="pending_approval"),
            sa.Column("execution_status", sa.String(24), nullable=False, server_default="pending_execution"),
            sa.Column("decided_by_user_id", sa.String(36), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("outcome_text", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("staff_competence_rating", sa.Integer(), nullable=True),
            sa.Column("staff_impact_json", sa.JSON(), nullable=False),
            sa.Column("ecosystem_event_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_owner_club_delegated_decisions_club_id",
            "owner_club_delegated_decisions",
            ["club_id"],
        )
        op.create_index(
            "ix_owner_club_delegated_decisions_owner_user_id",
            "owner_club_delegated_decisions",
            ["owner_user_id"],
        )
        op.create_index(
            "ix_owner_club_delegated_decisions_activity_key",
            "owner_club_delegated_decisions",
            ["activity_key"],
        )
        op.create_index(
            "ix_owner_club_delegated_decisions_status",
            "owner_club_delegated_decisions",
            ["status"],
        )

    if "owner_club_decision_audit_logs" not in tables:
        op.create_table(
            "owner_club_decision_audit_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("decision_id", sa.String(36), nullable=False),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("actor_id", sa.String(36), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("previous_status", sa.String(24), nullable=True),
            sa.Column("new_status", sa.String(24), nullable=False),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_owner_club_decision_audit_logs_decision_id",
            "owner_club_decision_audit_logs",
            ["decision_id"],
        )
        op.create_index(
            "ix_owner_club_decision_audit_logs_club_id",
            "owner_club_decision_audit_logs",
            ["club_id"],
        )
        op.create_index(
            "ix_owner_club_decision_audit_logs_created_at",
            "owner_club_decision_audit_logs",
            ["created_at"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "owner_club_decision_audit_logs" in tables:
        op.drop_table("owner_club_decision_audit_logs")
    if "owner_club_delegated_decisions" in tables:
        op.drop_table("owner_club_delegated_decisions")
    if "owner_club_delegation_policies" in tables:
        op.drop_table("owner_club_delegation_policies")
