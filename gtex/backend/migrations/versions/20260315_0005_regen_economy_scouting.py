"""regen economy scouting and balance

Revision ID: 20260315_0005
Revises: 20260315_0004
Create Date: 2026-03-15 20:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0005"
down_revision = "20260315_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_value_snapshots",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("current_value_coin", sa.Integer(), nullable=False),
        sa.Column("ability_component", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("potential_component", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reputation_component", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("narrative_component", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demand_component", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("guardrail_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_value_snapshots_regen_id", "regen_value_snapshots", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_value_snapshots_calculated_at",
        "regen_value_snapshots",
        ["calculated_at"],
        unique=False,
    )

    op.create_table(
        "regen_market_activity",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("activity_type", sa.String(length=48), nullable=False),
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default="competition"),
        sa.Column("impact_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("value_delta_coin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stat_line_json", sa.JSON(), nullable=False),
        sa.Column("narrative_tags_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_market_activity_regen_id", "regen_market_activity", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_market_activity_activity_type",
        "regen_market_activity",
        ["activity_type"],
        unique=False,
    )
    op.create_index("ix_regen_market_activity_occurred_at", "regen_market_activity", ["occurred_at"], unique=False)

    op.create_table(
        "regen_scout_reports",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("scout_identity", sa.String(length=120), nullable=True),
        sa.Column("manager_style", sa.String(length=48), nullable=False),
        sa.Column("system_profile", sa.String(length=64), nullable=True),
        sa.Column("current_ability_estimate", sa.Integer(), nullable=False),
        sa.Column("future_potential_estimate", sa.Integer(), nullable=False),
        sa.Column("scout_confidence_bps", sa.Integer(), nullable=False),
        sa.Column("role_fit_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("hidden_gem_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("wonderkid_signal", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("value_hint_coin", sa.Integer(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_scout_reports_regen_id", "regen_scout_reports", ["regen_id"], unique=False)
    op.create_index("ix_regen_scout_reports_club_id", "regen_scout_reports", ["club_id"], unique=False)
    op.create_index(
        "ix_regen_scout_reports_manager_style",
        "regen_scout_reports",
        ["manager_style"],
        unique=False,
    )

    op.create_table(
        "regen_recommendation_items",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("manager_style", sa.String(length=48), nullable=False),
        sa.Column("premium_tier", sa.String(length=24), nullable=False, server_default="standard"),
        sa.Column("position_need", sa.String(length=32), nullable=True),
        sa.Column("system_profile", sa.String(length=64), nullable=True),
        sa.Column("budget_coin", sa.Integer(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("role_fit_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("market_value_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regen_recommendation_items_regen_id",
        "regen_recommendation_items",
        ["regen_id"],
        unique=False,
    )
    op.create_index(
        "ix_regen_recommendation_items_club_id",
        "regen_recommendation_items",
        ["club_id"],
        unique=False,
    )
    op.create_index(
        "ix_regen_recommendation_items_priority_score",
        "regen_recommendation_items",
        ["priority_score"],
        unique=False,
    )

    op.create_table(
        "regen_demand_signals",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("signal_type", sa.String(length=48), nullable=False),
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default="market"),
        sa.Column("signal_strength", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("supporting_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("signal_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_demand_signals_regen_id", "regen_demand_signals", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_demand_signals_signal_type",
        "regen_demand_signals",
        ["signal_type"],
        unique=False,
    )
    op.create_index("ix_regen_demand_signals_occurred_at", "regen_demand_signals", ["occurred_at"], unique=False)

    op.create_table(
        "regen_onboarding_flags",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("onboarding_type", sa.String(length=32), nullable=False, server_default="starter_bundle"),
        sa.Column("squad_bucket", sa.String(length=32), nullable=False, server_default="first_team"),
        sa.Column("squad_slot", sa.Integer(), nullable=True),
        sa.Column("is_non_tradable", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("replacement_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_onboarding_flags_regen_id"),
    )
    op.create_index("ix_regen_onboarding_flags_club_id", "regen_onboarding_flags", ["club_id"], unique=False)

    op.create_table(
        "regen_transfer_fee_rules",
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("fee_bps", sa.Integer(), nullable=False),
        sa.Column("min_fee_bps", sa.Integer(), nullable=False),
        sa.Column("max_fee_bps", sa.Integer(), nullable=False),
        sa.Column("regen_share_soft_cap", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("elite_regen_share_cap", sa.Float(), nullable=False, server_default="0.08"),
        sa.Column("demand_cooling_floor", sa.Float(), nullable=False, server_default="0.55"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("policy_source", sa.String(length=32), nullable=False, server_default="system_default"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_key", name="uq_regen_transfer_fee_rules_rule_key"),
    )
    op.create_index("ix_regen_transfer_fee_rules_rule_key", "regen_transfer_fee_rules", ["rule_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regen_transfer_fee_rules_rule_key", table_name="regen_transfer_fee_rules")
    op.drop_table("regen_transfer_fee_rules")
    op.drop_index("ix_regen_onboarding_flags_club_id", table_name="regen_onboarding_flags")
    op.drop_table("regen_onboarding_flags")
    op.drop_index("ix_regen_demand_signals_occurred_at", table_name="regen_demand_signals")
    op.drop_index("ix_regen_demand_signals_signal_type", table_name="regen_demand_signals")
    op.drop_index("ix_regen_demand_signals_regen_id", table_name="regen_demand_signals")
    op.drop_table("regen_demand_signals")
    op.drop_index("ix_regen_recommendation_items_priority_score", table_name="regen_recommendation_items")
    op.drop_index("ix_regen_recommendation_items_club_id", table_name="regen_recommendation_items")
    op.drop_index("ix_regen_recommendation_items_regen_id", table_name="regen_recommendation_items")
    op.drop_table("regen_recommendation_items")
    op.drop_index("ix_regen_scout_reports_manager_style", table_name="regen_scout_reports")
    op.drop_index("ix_regen_scout_reports_club_id", table_name="regen_scout_reports")
    op.drop_index("ix_regen_scout_reports_regen_id", table_name="regen_scout_reports")
    op.drop_table("regen_scout_reports")
    op.drop_index("ix_regen_market_activity_occurred_at", table_name="regen_market_activity")
    op.drop_index("ix_regen_market_activity_activity_type", table_name="regen_market_activity")
    op.drop_index("ix_regen_market_activity_regen_id", table_name="regen_market_activity")
    op.drop_table("regen_market_activity")
    op.drop_index("ix_regen_value_snapshots_calculated_at", table_name="regen_value_snapshots")
    op.drop_index("ix_regen_value_snapshots_regen_id", table_name="regen_value_snapshots")
    op.drop_table("regen_value_snapshots")
