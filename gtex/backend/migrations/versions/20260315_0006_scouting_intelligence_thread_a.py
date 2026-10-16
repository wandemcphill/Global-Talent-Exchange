"""thread a scouting intelligence and lifecycle persistence

Revision ID: 20260315_0006
Revises: 20260315_0005
Create Date: 2026-03-15 22:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0006"
down_revision = "20260315_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manager_scouting_profiles",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("manager_code", sa.String(length=64), nullable=False),
        sa.Column("manager_name", sa.String(length=160), nullable=False),
        sa.Column("persona_code", sa.String(length=48), nullable=False, server_default="balanced"),
        sa.Column("preferred_system", sa.String(length=64), nullable=True),
        sa.Column("youth_bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("market_bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tactical_bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("star_bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("accuracy_boost_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "manager_code", name="uq_manager_scouting_profiles_club_manager"),
    )
    op.create_index("ix_manager_scouting_profiles_club_id", "manager_scouting_profiles", ["club_id"], unique=False)
    op.create_index(
        "ix_manager_scouting_profiles_persona_code",
        "manager_scouting_profiles",
        ["persona_code"],
        unique=False,
    )

    op.create_table(
        "scouting_networks",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("manager_profile_id", sa.String(length=36), nullable=True),
        sa.Column("network_name", sa.String(length=160), nullable=False),
        sa.Column("region_code", sa.String(length=64), nullable=False),
        sa.Column("region_name", sa.String(length=160), nullable=False),
        sa.Column("specialty_code", sa.String(length=64), nullable=False),
        sa.Column("quality_tier", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("scout_identity", sa.String(length=120), nullable=True),
        sa.Column("scout_rating", sa.Integer(), nullable=False, server_default="55"),
        sa.Column("weekly_cost_coin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_cadence_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_profile_id"], ["manager_scouting_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "network_name", name="uq_scouting_networks_club_name"),
    )
    op.create_index("ix_scouting_networks_club_id", "scouting_networks", ["club_id"], unique=False)
    op.create_index("ix_scouting_networks_region_code", "scouting_networks", ["region_code"], unique=False)
    op.create_index("ix_scouting_networks_specialty_code", "scouting_networks", ["specialty_code"], unique=False)

    op.create_table(
        "scouting_network_assignments",
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_name", sa.String(length=160), nullable=False),
        sa.Column("assignment_scope", sa.String(length=48), nullable=False, server_default="region"),
        sa.Column("territory_code", sa.String(length=64), nullable=True),
        sa.Column("focus_position", sa.String(length=32), nullable=True),
        sa.Column("age_band_min", sa.Integer(), nullable=True),
        sa.Column("age_band_max", sa.Integer(), nullable=True),
        sa.Column("budget_profile", sa.String(length=48), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["network_id"], ["scouting_networks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scouting_network_assignments_network_id",
        "scouting_network_assignments",
        ["network_id"],
        unique=False,
    )
    op.create_index(
        "ix_scouting_network_assignments_club_id",
        "scouting_network_assignments",
        ["club_id"],
        unique=False,
    )
    op.create_index(
        "ix_scouting_network_assignments_status",
        "scouting_network_assignments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "scout_missions",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("manager_profile_id", sa.String(length=36), nullable=True),
        sa.Column("mission_name", sa.String(length=180), nullable=False),
        sa.Column("mission_type", sa.String(length=48), nullable=False, server_default="standard_assignment"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("target_position", sa.String(length=32), nullable=True),
        sa.Column("target_region", sa.String(length=120), nullable=True),
        sa.Column("target_age_min", sa.Integer(), nullable=True),
        sa.Column("target_age_max", sa.Integer(), nullable=True),
        sa.Column("budget_limit_coin", sa.Integer(), nullable=True),
        sa.Column("affordability_tier", sa.String(length=48), nullable=True),
        sa.Column("mission_duration_days", sa.Integer(), nullable=False, server_default="21"),
        sa.Column("talent_type", sa.String(length=48), nullable=False, server_default="balanced"),
        sa.Column("include_academy", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("system_profile", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_profile_id"], ["manager_scouting_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["network_id"], ["scouting_networks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scout_missions_club_id", "scout_missions", ["club_id"], unique=False)
    op.create_index("ix_scout_missions_network_id", "scout_missions", ["network_id"], unique=False)
    op.create_index("ix_scout_missions_status", "scout_missions", ["status"], unique=False)

    op.create_table(
        "scout_reports",
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("academy_candidate_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("recommendation_rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lifecycle_phase", sa.String(length=48), nullable=False),
        sa.Column("confidence_bps", sa.Integer(), nullable=False),
        sa.Column("fit_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("potential_signal_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("value_signal_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("hidden_gem_signal", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("current_ability_estimate", sa.Integer(), nullable=False),
        sa.Column("future_potential_estimate", sa.Integer(), nullable=False),
        sa.Column("value_hint_coin", sa.Integer(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["academy_candidate_id"], ["academy_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mission_id"], ["scout_missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["network_id"], ["scouting_networks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scout_reports_mission_id", "scout_reports", ["mission_id"], unique=False)
    op.create_index("ix_scout_reports_network_id", "scout_reports", ["network_id"], unique=False)
    op.create_index("ix_scout_reports_regen_profile_id", "scout_reports", ["regen_profile_id"], unique=False)
    op.create_index("ix_scout_reports_club_id", "scout_reports", ["club_id"], unique=False)

    op.create_table(
        "hidden_potential_estimates",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("scout_report_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("academy_candidate_id", sa.String(length=36), nullable=True),
        sa.Column("current_ability_low", sa.Integer(), nullable=False),
        sa.Column("current_ability_high", sa.Integer(), nullable=False),
        sa.Column("future_potential_low", sa.Integer(), nullable=False),
        sa.Column("future_potential_high", sa.Integer(), nullable=False),
        sa.Column("scout_confidence_bps", sa.Integer(), nullable=False),
        sa.Column("uncertainty_band", sa.Integer(), nullable=False),
        sa.Column("lifecycle_phase", sa.String(length=48), nullable=False),
        sa.Column("revealed_by_persona", sa.String(length=48), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["academy_candidate_id"], ["academy_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mission_id"], ["scout_missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["network_id"], ["scouting_networks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scout_report_id"], ["scout_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scout_report_id", name="uq_hidden_potential_estimates_report_id"),
    )
    op.create_index(
        "ix_hidden_potential_estimates_regen_profile_id",
        "hidden_potential_estimates",
        ["regen_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_hidden_potential_estimates_club_id",
        "hidden_potential_estimates",
        ["club_id"],
        unique=False,
    )

    op.create_table(
        "academy_supply_signals",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=True),
        sa.Column("signal_type", sa.String(length=48), nullable=False, server_default="academy_pipeline"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("standout_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_potential_high", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("visibility_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("signal_status", sa.String(length=32), nullable=False, server_default="visible"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id"], ["academy_intake_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "batch_id", "signal_type", name="uq_academy_supply_signals_club_batch_type"),
    )
    op.create_index("ix_academy_supply_signals_club_id", "academy_supply_signals", ["club_id"], unique=False)
    op.create_index("ix_academy_supply_signals_batch_id", "academy_supply_signals", ["batch_id"], unique=False)

    op.create_table(
        "player_lifecycle_profiles",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("phase", sa.String(length=48), nullable=False),
        sa.Column("phase_source", sa.String(length=48), nullable=False, server_default="age_curve"),
        sa.Column("age_years", sa.Integer(), nullable=False),
        sa.Column("lifecycle_age_months", sa.Integer(), nullable=True),
        sa.Column("market_desirability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("planning_horizon_months", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("development_confidence_bps", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_lifecycle_profiles_player_id"),
    )
    op.create_index("ix_player_lifecycle_profiles_club_id", "player_lifecycle_profiles", ["club_id"], unique=False)
    op.create_index("ix_player_lifecycle_profiles_phase", "player_lifecycle_profiles", ["phase"], unique=False)

    op.create_table(
        "talent_discovery_badges",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("academy_candidate_id", sa.String(length=36), nullable=True),
        sa.Column("badge_code", sa.String(length=80), nullable=False),
        sa.Column("badge_name", sa.String(length=180), nullable=False),
        sa.Column("evidence_level", sa.String(length=48), nullable=False, server_default="emerging"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["academy_candidate_id"], ["academy_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "regen_profile_id", "badge_code", name="uq_talent_discovery_badges_club_regen_code"),
    )
    op.create_index("ix_talent_discovery_badges_club_id", "talent_discovery_badges", ["club_id"], unique=False)
    op.create_index(
        "ix_talent_discovery_badges_regen_profile_id",
        "talent_discovery_badges",
        ["regen_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_talent_discovery_badges_badge_code",
        "talent_discovery_badges",
        ["badge_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_talent_discovery_badges_badge_code", table_name="talent_discovery_badges")
    op.drop_index("ix_talent_discovery_badges_regen_profile_id", table_name="talent_discovery_badges")
    op.drop_index("ix_talent_discovery_badges_club_id", table_name="talent_discovery_badges")
    op.drop_table("talent_discovery_badges")
    op.drop_index("ix_player_lifecycle_profiles_phase", table_name="player_lifecycle_profiles")
    op.drop_index("ix_player_lifecycle_profiles_club_id", table_name="player_lifecycle_profiles")
    op.drop_table("player_lifecycle_profiles")
    op.drop_index("ix_academy_supply_signals_batch_id", table_name="academy_supply_signals")
    op.drop_index("ix_academy_supply_signals_club_id", table_name="academy_supply_signals")
    op.drop_table("academy_supply_signals")
    op.drop_index("ix_hidden_potential_estimates_club_id", table_name="hidden_potential_estimates")
    op.drop_index("ix_hidden_potential_estimates_regen_profile_id", table_name="hidden_potential_estimates")
    op.drop_table("hidden_potential_estimates")
    op.drop_index("ix_scout_reports_club_id", table_name="scout_reports")
    op.drop_index("ix_scout_reports_regen_profile_id", table_name="scout_reports")
    op.drop_index("ix_scout_reports_network_id", table_name="scout_reports")
    op.drop_index("ix_scout_reports_mission_id", table_name="scout_reports")
    op.drop_table("scout_reports")
    op.drop_index("ix_scout_missions_status", table_name="scout_missions")
    op.drop_index("ix_scout_missions_network_id", table_name="scout_missions")
    op.drop_index("ix_scout_missions_club_id", table_name="scout_missions")
    op.drop_table("scout_missions")
    op.drop_index("ix_scouting_network_assignments_status", table_name="scouting_network_assignments")
    op.drop_index("ix_scouting_network_assignments_club_id", table_name="scouting_network_assignments")
    op.drop_index("ix_scouting_network_assignments_network_id", table_name="scouting_network_assignments")
    op.drop_table("scouting_network_assignments")
    op.drop_index("ix_scouting_networks_specialty_code", table_name="scouting_networks")
    op.drop_index("ix_scouting_networks_region_code", table_name="scouting_networks")
    op.drop_index("ix_scouting_networks_club_id", table_name="scouting_networks")
    op.drop_table("scouting_networks")
    op.drop_index("ix_manager_scouting_profiles_persona_code", table_name="manager_scouting_profiles")
    op.drop_index("ix_manager_scouting_profiles_club_id", table_name="manager_scouting_profiles")
    op.drop_table("manager_scouting_profiles")
