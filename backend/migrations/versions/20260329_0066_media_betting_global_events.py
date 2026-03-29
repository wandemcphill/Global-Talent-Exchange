"""Add pundit profiles, betting, and global event tables.

Revision ID: 20260329_0066_media_betting_global_events
Revises: 20260329_0065_commentary_personalities_and_club_dao, 20260329_0065_event_reliability_guards
Create Date: 2026-03-29 15:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0066_media_betting_global_events"
down_revision = ("20260329_0065_commentary_personalities_and_club_dao", "20260329_0065_event_reliability_guards")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pundit_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("bias", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence_level", sa.Float(), nullable=False, server_default="0.65"),
        sa.Column("debate_style", sa.String(length=64), nullable=False, server_default="measured"),
        sa.Column("signature_line", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_pundit_profiles"),
        sa.UniqueConstraint("name", name="uq_pundit_profiles_name"),
    )
    op.create_index("ix_pundit_profiles_name", "pundit_profiles", ["name"], unique=False)
    op.create_index("ix_pundit_profiles_style", "pundit_profiles", ["style"], unique=False)

    op.create_table(
        "global_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("event_key", sa.String(length=120), nullable=False),
        sa.Column("event_name", sa.String(length=200), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("calendar_event_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["calendar_event_id"], ["calendar_events.id"], name="fk_global_events_calendar_event_id_calendar_events", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_global_events"),
        sa.UniqueConstraint("event_key", name="uq_global_events_event_key"),
    )
    op.create_index("ix_global_events_event_key", "global_events", ["event_key"], unique=False)
    op.create_index("ix_global_events_start_time", "global_events", ["start_time"], unique=False)
    op.create_index("ix_global_events_end_time", "global_events", ["end_time"], unique=False)
    op.create_index("ix_global_events_event_type", "global_events", ["event_type"], unique=False)
    op.create_index("ix_global_events_priority", "global_events", ["priority"], unique=False)
    op.create_index("ix_global_events_calendar_event_id", "global_events", ["calendar_event_id"], unique=False)
    op.create_index("ix_global_events_match_id", "global_events", ["match_id"], unique=False)
    op.create_index("ix_global_events_status", "global_events", ["status"], unique=False)

    op.create_table(
        "betting_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("region_code", sa.String(length=32), nullable=False, server_default="GLOBAL"),
        sa.Column("compliance_mode", sa.String(length=32), nullable=False, server_default="regulated"),
        sa.Column("is_opted_in", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("available_bet_balance", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("locked_bet_balance", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("max_bet_amount", sa.Numeric(20, 4), nullable=False, server_default="50.0000"),
        sa.Column("daily_loss_cap", sa.Numeric(20, 4), nullable=False, server_default="250.0000"),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("self_excluded_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_bet_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_betting_profiles_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_betting_profiles"),
        sa.UniqueConstraint("user_id", name="uq_betting_profiles_user_id"),
    )
    op.create_index("ix_betting_profiles_user_id", "betting_profiles", ["user_id"], unique=False)
    op.create_index("ix_betting_profiles_region_code", "betting_profiles", ["region_code"], unique=False)
    op.create_index("ix_betting_profiles_cooldown_until", "betting_profiles", ["cooldown_until"], unique=False)

    op.create_table(
        "bet_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=True),
        sa.Column("bet_type", sa.String(length=48), nullable=False),
        sa.Column("selection_key", sa.String(length=160), nullable=False),
        sa.Column("selection_label", sa.String(length=200), nullable=False),
        sa.Column("region_code", sa.String(length=32), nullable=False, server_default="GLOBAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="placed"),
        sa.Column("stake_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("odds_decimal", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("implied_probability", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("potential_payout_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("market_demand_factor", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("risk_adjustment_factor", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("settled_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["event_id"], ["global_events.id"], name="fk_bet_tickets_event_id_global_events", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bet_tickets_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_bet_tickets"),
    )
    op.create_index("ix_bet_tickets_user_id", "bet_tickets", ["user_id"], unique=False)
    op.create_index("ix_bet_tickets_match_id", "bet_tickets", ["match_id"], unique=False)
    op.create_index("ix_bet_tickets_event_id", "bet_tickets", ["event_id"], unique=False)
    op.create_index("ix_bet_tickets_bet_type", "bet_tickets", ["bet_type"], unique=False)
    op.create_index("ix_bet_tickets_status", "bet_tickets", ["status"], unique=False)
    op.create_index("ix_bet_tickets_settled_at", "bet_tickets", ["settled_at"], unique=False)
    op.create_index("ix_bet_tickets_match_id_status", "bet_tickets", ["match_id", "status"], unique=False)
    op.create_index("ix_bet_tickets_user_id_created_at", "bet_tickets", ["user_id", "created_at"], unique=False)

    op.create_table(
        "bet_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("bet_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("before_available_balance", sa.Numeric(20, 4), nullable=True),
        sa.Column("after_available_balance", sa.Numeric(20, 4), nullable=True),
        sa.Column("before_locked_balance", sa.Numeric(20, 4), nullable=True),
        sa.Column("after_locked_balance", sa.Numeric(20, 4), nullable=True),
        sa.Column("reference", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["bet_id"], ["bet_tickets.id"], name="fk_bet_audit_logs_bet_id_bet_tickets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bet_audit_logs_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_bet_audit_logs"),
    )
    op.create_index("ix_bet_audit_logs_bet_id", "bet_audit_logs", ["bet_id"], unique=False)
    op.create_index("ix_bet_audit_logs_user_id", "bet_audit_logs", ["user_id"], unique=False)
    op.create_index("ix_bet_audit_logs_event_type", "bet_audit_logs", ["event_type"], unique=False)
    op.create_index("ix_bet_audit_logs_reference", "bet_audit_logs", ["reference"], unique=False)
    op.create_index("ix_bet_audit_logs_user_id_created_at", "bet_audit_logs", ["user_id", "created_at"], unique=False)

    op.create_table(
        "bet_integrity_alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("bet_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=24), nullable=False, server_default="low"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["bet_id"], ["bet_tickets.id"], name="fk_bet_integrity_alerts_bet_id_bet_tickets", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bet_integrity_alerts_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_bet_integrity_alerts"),
    )
    op.create_index("ix_bet_integrity_alerts_match_id", "bet_integrity_alerts", ["match_id"], unique=False)
    op.create_index("ix_bet_integrity_alerts_bet_id", "bet_integrity_alerts", ["bet_id"], unique=False)
    op.create_index("ix_bet_integrity_alerts_user_id", "bet_integrity_alerts", ["user_id"], unique=False)
    op.create_index("ix_bet_integrity_alerts_issue_type", "bet_integrity_alerts", ["issue_type"], unique=False)
    op.create_index("ix_bet_integrity_alerts_status", "bet_integrity_alerts", ["status"], unique=False)
    op.create_index("ix_bet_integrity_alerts_match_id_status", "bet_integrity_alerts", ["match_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bet_integrity_alerts_match_id_status", table_name="bet_integrity_alerts")
    op.drop_index("ix_bet_integrity_alerts_status", table_name="bet_integrity_alerts")
    op.drop_index("ix_bet_integrity_alerts_issue_type", table_name="bet_integrity_alerts")
    op.drop_index("ix_bet_integrity_alerts_user_id", table_name="bet_integrity_alerts")
    op.drop_index("ix_bet_integrity_alerts_bet_id", table_name="bet_integrity_alerts")
    op.drop_index("ix_bet_integrity_alerts_match_id", table_name="bet_integrity_alerts")
    op.drop_table("bet_integrity_alerts")

    op.drop_index("ix_bet_audit_logs_user_id_created_at", table_name="bet_audit_logs")
    op.drop_index("ix_bet_audit_logs_reference", table_name="bet_audit_logs")
    op.drop_index("ix_bet_audit_logs_event_type", table_name="bet_audit_logs")
    op.drop_index("ix_bet_audit_logs_user_id", table_name="bet_audit_logs")
    op.drop_index("ix_bet_audit_logs_bet_id", table_name="bet_audit_logs")
    op.drop_table("bet_audit_logs")

    op.drop_index("ix_bet_tickets_user_id_created_at", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_match_id_status", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_settled_at", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_status", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_bet_type", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_event_id", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_match_id", table_name="bet_tickets")
    op.drop_index("ix_bet_tickets_user_id", table_name="bet_tickets")
    op.drop_table("bet_tickets")

    op.drop_index("ix_betting_profiles_cooldown_until", table_name="betting_profiles")
    op.drop_index("ix_betting_profiles_region_code", table_name="betting_profiles")
    op.drop_index("ix_betting_profiles_user_id", table_name="betting_profiles")
    op.drop_table("betting_profiles")

    op.drop_index("ix_global_events_status", table_name="global_events")
    op.drop_index("ix_global_events_match_id", table_name="global_events")
    op.drop_index("ix_global_events_calendar_event_id", table_name="global_events")
    op.drop_index("ix_global_events_priority", table_name="global_events")
    op.drop_index("ix_global_events_event_type", table_name="global_events")
    op.drop_index("ix_global_events_end_time", table_name="global_events")
    op.drop_index("ix_global_events_start_time", table_name="global_events")
    op.drop_index("ix_global_events_event_key", table_name="global_events")
    op.drop_table("global_events")

    op.drop_index("ix_pundit_profiles_style", table_name="pundit_profiles")
    op.drop_index("ix_pundit_profiles_name", table_name="pundit_profiles")
    op.drop_table("pundit_profiles")
