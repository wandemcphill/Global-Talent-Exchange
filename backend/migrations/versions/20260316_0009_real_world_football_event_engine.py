"""real-world football event engine and player form modifiers

Revision ID: 20260316_0009b
Revises: 20260316_0008
Create Date: 2026-03-16 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0009b"
down_revision = "20260316_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_ingestion_jobs",
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_label", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("submitted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_ingestion_jobs_source_type", "event_ingestion_jobs", ["source_type"], unique=False)
    op.create_index("ix_event_ingestion_jobs_status", "event_ingestion_jobs", ["status"], unique=False)
    op.create_index("ix_event_ingestion_jobs_started_at", "event_ingestion_jobs", ["started_at"], unique=False)

    op.create_table(
        "event_effect_rules",
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("effect_type", sa.String(length=32), nullable=False),
        sa.Column("effect_code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("base_magnitude", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("duration_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gameplay_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("market_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("recommendation_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type", "effect_type", "effect_code", name="uq_event_effect_rules_event_effect"),
    )
    op.create_index("ix_event_effect_rules_event_type", "event_effect_rules", ["event_type"], unique=False)
    op.create_index("ix_event_effect_rules_enabled", "event_effect_rules", ["is_enabled"], unique=False)

    op.create_table(
        "real_world_football_events",
        sa.Column("ingestion_job_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_label", sa.String(length=80), nullable=False),
        sa.Column("external_event_id", sa.String(length=160), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="approved"),
        sa.Column("requires_admin_review", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("severity", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("effect_severity_override", sa.Float(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("effects_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("normalized_payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["current_club_id"], ["ingestion_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ingestion_job_id"], ["event_ingestion_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_real_world_football_events_dedupe_key"),
    )
    op.create_index("ix_real_world_football_events_player_id", "real_world_football_events", ["player_id"], unique=False)
    op.create_index("ix_real_world_football_events_event_type", "real_world_football_events", ["event_type"], unique=False)
    op.create_index("ix_real_world_football_events_approval_status", "real_world_football_events", ["approval_status"], unique=False)
    op.create_index("ix_real_world_football_events_occurred_at", "real_world_football_events", ["occurred_at"], unique=False)

    op.create_table(
        "player_form_modifiers",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("modifier_type", sa.String(length=64), nullable=False),
        sa.Column("modifier_label", sa.String(length=160), nullable=False),
        sa.Column("modifier_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("gameplay_effect_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("market_effect_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommendation_effect_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("visible_to_users", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["real_world_football_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_form_modifiers_player_id", "player_form_modifiers", ["player_id"], unique=False)
    op.create_index("ix_player_form_modifiers_status", "player_form_modifiers", ["status"], unique=False)
    op.create_index("ix_player_form_modifiers_expires_at", "player_form_modifiers", ["expires_at"], unique=False)

    op.create_table(
        "trending_player_flags",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("flag_label", sa.String(length=160), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["real_world_football_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trending_player_flags_player_id", "trending_player_flags", ["player_id"], unique=False)
    op.create_index("ix_trending_player_flags_flag_type", "trending_player_flags", ["flag_type"], unique=False)
    op.create_index("ix_trending_player_flags_status", "trending_player_flags", ["status"], unique=False)
    op.create_index("ix_trending_player_flags_expires_at", "trending_player_flags", ["expires_at"], unique=False)

    op.create_table(
        "player_demand_signals",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("signal_label", sa.String(length=160), nullable=False),
        sa.Column("demand_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("scouting_interest_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommendation_priority_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("market_buzz_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["real_world_football_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_demand_signals_player_id", "player_demand_signals", ["player_id"], unique=False)
    op.create_index("ix_player_demand_signals_signal_type", "player_demand_signals", ["signal_type"], unique=False)
    op.create_index("ix_player_demand_signals_status", "player_demand_signals", ["status"], unique=False)
    op.create_index("ix_player_demand_signals_expires_at", "player_demand_signals", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_demand_signals_expires_at", table_name="player_demand_signals")
    op.drop_index("ix_player_demand_signals_status", table_name="player_demand_signals")
    op.drop_index("ix_player_demand_signals_signal_type", table_name="player_demand_signals")
    op.drop_index("ix_player_demand_signals_player_id", table_name="player_demand_signals")
    op.drop_table("player_demand_signals")

    op.drop_index("ix_trending_player_flags_expires_at", table_name="trending_player_flags")
    op.drop_index("ix_trending_player_flags_status", table_name="trending_player_flags")
    op.drop_index("ix_trending_player_flags_flag_type", table_name="trending_player_flags")
    op.drop_index("ix_trending_player_flags_player_id", table_name="trending_player_flags")
    op.drop_table("trending_player_flags")

    op.drop_index("ix_player_form_modifiers_expires_at", table_name="player_form_modifiers")
    op.drop_index("ix_player_form_modifiers_status", table_name="player_form_modifiers")
    op.drop_index("ix_player_form_modifiers_player_id", table_name="player_form_modifiers")
    op.drop_table("player_form_modifiers")

    op.drop_index("ix_real_world_football_events_occurred_at", table_name="real_world_football_events")
    op.drop_index("ix_real_world_football_events_approval_status", table_name="real_world_football_events")
    op.drop_index("ix_real_world_football_events_event_type", table_name="real_world_football_events")
    op.drop_index("ix_real_world_football_events_player_id", table_name="real_world_football_events")
    op.drop_table("real_world_football_events")

    op.drop_index("ix_event_effect_rules_enabled", table_name="event_effect_rules")
    op.drop_index("ix_event_effect_rules_event_type", table_name="event_effect_rules")
    op.drop_table("event_effect_rules")

    op.drop_index("ix_event_ingestion_jobs_started_at", table_name="event_ingestion_jobs")
    op.drop_index("ix_event_ingestion_jobs_status", table_name="event_ingestion_jobs")
    op.drop_index("ix_event_ingestion_jobs_source_type", table_name="event_ingestion_jobs")
    op.drop_table("event_ingestion_jobs")
