"""Add club growth tables for staff, academy, and sponsorship bridge.

Revision ID: 20260511_0092_club_growth_batches_25_27
Revises: 20260511_0091_club_lifecycle_batch24
Create Date: 2026-05-11 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260511_0092_club_growth_batches_25_27"
down_revision = "20260511_0091_club_lifecycle_batch24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_staff_profiles",
        sa.Column("market_key", sa.String(length=96), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("staff_type", sa.String(length=32), nullable=False),
        sa.Column("rarity", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("skills_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("salary_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commission_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market_key", name="uq_club_staff_profiles_market_key"),
    )
    op.create_index("ix_club_staff_profiles_market_key", "club_staff_profiles", ["market_key"])
    op.create_index("ix_club_staff_profiles_staff_type", "club_staff_profiles", ["staff_type"])

    op.create_table(
        "academy_profiles",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("investment_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generation_cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_academy_profiles_club_id"),
    )
    op.create_index("ix_academy_profiles_club_id", "academy_profiles", ["club_id"])

    op.create_table(
        "club_staff_contracts",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("staff_profile_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offered"),
        sa.Column("salary_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commission_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("role_scope", sa.String(length=64), nullable=False, server_default="club"),
        sa.Column("exclusive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["club_staff_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_staff_contracts_club_id", "club_staff_contracts", ["club_id"])
    op.create_index("ix_club_staff_contracts_staff_profile_id", "club_staff_contracts", ["staff_profile_id"])

    op.create_table(
        "academy_prospects",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("academy_profile_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("nationality", sa.String(length=8), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("personality_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("current_ability", sa.Integer(), nullable=False, server_default="35"),
        sa.Column("potential", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("portrait_asset_ref", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="discovered"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["academy_profile_id"], ["academy_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academy_prospects_academy_profile_id", "academy_prospects", ["academy_profile_id"])
    op.create_index("ix_academy_prospects_club_id", "academy_prospects", ["club_id"])
    op.create_index("ix_academy_prospects_nationality", "academy_prospects", ["nationality"])

    op.create_table(
        "academy_training_plans",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("focus", sa.String(length=64), nullable=False, server_default="balanced"),
        sa.Column("intensity", sa.String(length=32), nullable=False, server_default="normal"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academy_training_plans_club_id", "academy_training_plans", ["club_id"])

    op.create_table(
        "club_staff_assignments",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("staff_contract_id", sa.String(length=36), nullable=False),
        sa.Column("role_key", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_contract_id"], ["club_staff_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "role_key", name="uq_club_staff_assignments_club_role"),
    )
    op.create_index("ix_club_staff_assignments_club_id", "club_staff_assignments", ["club_id"])
    op.create_index("ix_club_staff_assignments_staff_contract_id", "club_staff_assignments", ["staff_contract_id"])

    op.create_table(
        "club_staff_performance_logs",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("staff_contract_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("rating_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_contract_id"], ["club_staff_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_staff_performance_logs_club_id", "club_staff_performance_logs", ["club_id"])
    op.create_index(
        "ix_club_staff_performance_logs_staff_contract_id",
        "club_staff_performance_logs",
        ["staff_contract_id"],
    )

    op.create_table(
        "academy_regen_contract_offers",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("prospect_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offered"),
        sa.Column("wage_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_months", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("response_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prospect_id"], ["academy_prospects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academy_regen_contract_offers_club_id", "academy_regen_contract_offers", ["club_id"])
    op.create_index("ix_academy_regen_contract_offers_prospect_id", "academy_regen_contract_offers", ["prospect_id"])

    op.create_table(
        "academy_promotion_history",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("prospect_id", sa.String(length=36), nullable=False),
        sa.Column("senior_player_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prospect_id"], ["academy_prospects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["senior_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academy_promotion_history_club_id", "academy_promotion_history", ["club_id"])
    op.create_index("ix_academy_promotion_history_prospect_id", "academy_promotion_history", ["prospect_id"])
    op.create_index("ix_academy_promotion_history_senior_player_id", "academy_promotion_history", ["senior_player_id"])

    op.create_table(
        "academy_generation_runs",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("run_seed", sa.String(length=128), nullable=False),
        sa.Column("prospects_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academy_generation_runs_club_id", "academy_generation_runs", ["club_id"])

    op.create_table(
        "club_growth_audit_events",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("previous_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("next_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_growth_audit_events_actor_user_id", "club_growth_audit_events", ["actor_user_id"])
    op.create_index("ix_club_growth_audit_events_club_id", "club_growth_audit_events", ["club_id"])


def downgrade() -> None:
    op.drop_index("ix_club_growth_audit_events_club_id", table_name="club_growth_audit_events")
    op.drop_index("ix_club_growth_audit_events_actor_user_id", table_name="club_growth_audit_events")
    op.drop_table("club_growth_audit_events")
    op.drop_index("ix_academy_generation_runs_club_id", table_name="academy_generation_runs")
    op.drop_table("academy_generation_runs")
    op.drop_index("ix_academy_promotion_history_senior_player_id", table_name="academy_promotion_history")
    op.drop_index("ix_academy_promotion_history_prospect_id", table_name="academy_promotion_history")
    op.drop_index("ix_academy_promotion_history_club_id", table_name="academy_promotion_history")
    op.drop_table("academy_promotion_history")
    op.drop_index("ix_academy_regen_contract_offers_prospect_id", table_name="academy_regen_contract_offers")
    op.drop_index("ix_academy_regen_contract_offers_club_id", table_name="academy_regen_contract_offers")
    op.drop_table("academy_regen_contract_offers")
    op.drop_index("ix_club_staff_performance_logs_staff_contract_id", table_name="club_staff_performance_logs")
    op.drop_index("ix_club_staff_performance_logs_club_id", table_name="club_staff_performance_logs")
    op.drop_table("club_staff_performance_logs")
    op.drop_index("ix_club_staff_assignments_staff_contract_id", table_name="club_staff_assignments")
    op.drop_index("ix_club_staff_assignments_club_id", table_name="club_staff_assignments")
    op.drop_table("club_staff_assignments")
    op.drop_index("ix_academy_training_plans_club_id", table_name="academy_training_plans")
    op.drop_table("academy_training_plans")
    op.drop_index("ix_academy_prospects_nationality", table_name="academy_prospects")
    op.drop_index("ix_academy_prospects_club_id", table_name="academy_prospects")
    op.drop_index("ix_academy_prospects_academy_profile_id", table_name="academy_prospects")
    op.drop_table("academy_prospects")
    op.drop_index("ix_club_staff_contracts_staff_profile_id", table_name="club_staff_contracts")
    op.drop_index("ix_club_staff_contracts_club_id", table_name="club_staff_contracts")
    op.drop_table("club_staff_contracts")
    op.drop_index("ix_academy_profiles_club_id", table_name="academy_profiles")
    op.drop_table("academy_profiles")
    op.drop_index("ix_club_staff_profiles_staff_type", table_name="club_staff_profiles")
    op.drop_index("ix_club_staff_profiles_market_key", table_name="club_staff_profiles")
    op.drop_table("club_staff_profiles")
