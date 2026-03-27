"""Add GTEX engagement systems and merge current 0036 heads.

Revision ID: 20260327_0037_gtex_engagement_systems
Revises: 20260327_0036_live_match_manager_duels, 20260327_0036_match_replay_and_manager_marketplace
Create Date: 2026-03-27 13:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0037_gtex_engagement_systems"
down_revision = (
    "20260327_0036_live_match_manager_duels",
    "20260327_0036_match_replay_and_manager_marketplace",
)
branch_labels = None
depends_on = None


prediction_outcome_enum = sa.Enum(
    "home_win",
    "away_win",
    "draw",
    name="prediction_outcome",
    native_enum=False,
)
sponsor_tier_enum = sa.Enum(
    "local",
    "regional",
    "global",
    name="club_finance_sponsor_tier",
    native_enum=False,
)
season_pass_tier_enum = sa.Enum(
    "free",
    "premium",
    name="season_pass_tier",
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "ingestion_players",
        sa.Column("morale", sa.Float(), nullable=False, server_default=sa.text("50.0")),
    )

    op.create_table(
        "predictions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("predicted_outcome", prediction_outcome_enum, nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("reward_earned", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("difficulty_multiplier", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("actual_outcome", prediction_outcome_enum, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predictions")),
        sa.UniqueConstraint("user_id", "match_id", name="uq_predictions_user_match"),
    )
    op.create_index("ix_predictions_match_id", "predictions", ["match_id"], unique=False)
    op.create_index("ix_predictions_user_id", "predictions", ["user_id"], unique=False)
    op.create_index("ix_predictions_resolved_at", "predictions", ["resolved_at"], unique=False)

    op.create_table(
        "club_finance_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("weekly_wages", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("sponsorship_income", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("match_income", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("transfer_profit", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("expenses", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("transfers_blocked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("forced_sale_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("forced_sale_player_id", sa.String(length=36), nullable=True),
        sa.Column("last_weekly_cycle_on", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["forced_sale_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_finance_profiles")),
        sa.UniqueConstraint("user_id", name="uq_club_finance_profiles_user_id"),
    )
    op.create_index("ix_club_finance_profiles_balance", "club_finance_profiles", ["balance"], unique=False)

    op.create_table(
        "club_finance_sponsors",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("tier", sponsor_tier_enum, nullable=False),
        sa.Column("payout", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("requirements_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_finance_sponsors")),
        sa.UniqueConstraint("name", name="uq_club_finance_sponsors_name"),
    )
    op.create_index("ix_club_finance_sponsors_tier", "club_finance_sponsors", ["tier"], unique=False)

    op.create_table(
        "club_finance_transactions",
        sa.Column("finance_profile_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("sponsor_id", sa.String(length=36), nullable=True),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["finance_profile_id"], ["club_finance_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_id"], ["club_finance_sponsors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_finance_transactions")),
        sa.UniqueConstraint("reference_key", name="uq_club_finance_transactions_reference_key"),
    )
    op.create_index("ix_club_finance_transactions_user_id", "club_finance_transactions", ["user_id"], unique=False)
    op.create_index("ix_club_finance_transactions_transaction_type", "club_finance_transactions", ["transaction_type"], unique=False)

    op.create_table(
        "player_relationships",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("teammate_player_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_score", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("tactical_fit", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("matches_together", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_match_together_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teammate_player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_relationships")),
        sa.UniqueConstraint("player_id", "teammate_player_id", name="uq_player_relationships_pair"),
    )
    op.create_index("ix_player_relationships_player_id", "player_relationships", ["player_id"], unique=False)
    op.create_index("ix_player_relationships_teammate_player_id", "player_relationships", ["teammate_player_id"], unique=False)

    op.create_table(
        "season_passes",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=False),
        sa.Column("tier", season_pass_tier_enum, nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("rewards_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_passes")),
        sa.UniqueConstraint("user_id", "season_id", name="uq_season_passes_user_season"),
    )
    op.create_index("ix_season_passes_user_id", "season_passes", ["user_id"], unique=False)
    op.create_index("ix_season_passes_season_id", "season_passes", ["season_id"], unique=False)

    op.create_table(
        "season_pass_claims",
        sa.Column("season_pass_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["season_pass_id"], ["season_passes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_pass_claims")),
        sa.UniqueConstraint("season_pass_id", "level", name="uq_season_pass_claims_pass_level"),
    )
    op.create_index("ix_season_pass_claims_user_id", "season_pass_claims", ["user_id"], unique=False)

    op.create_table(
        "season_pass_xp_grants",
        sa.Column("season_pass_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["season_pass_id"], ["season_passes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_pass_xp_grants")),
        sa.UniqueConstraint("reference_key", name="uq_season_pass_xp_grants_reference_key"),
    )
    op.create_index("ix_season_pass_xp_grants_user_id", "season_pass_xp_grants", ["user_id"], unique=False)
    op.create_index("ix_season_pass_xp_grants_source_type", "season_pass_xp_grants", ["source_type"], unique=False)

    op.create_table(
        "live_events",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rewards_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("started_notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_events")),
    )
    op.create_index("ix_live_events_start_date", "live_events", ["start_date"], unique=False)
    op.create_index("ix_live_events_end_date", "live_events", ["end_date"], unique=False)
    op.create_index(
        "ix_live_events_started_notification_sent_at",
        "live_events",
        ["started_notification_sent_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_live_events_started_notification_sent_at", table_name="live_events")
    op.drop_index("ix_live_events_end_date", table_name="live_events")
    op.drop_index("ix_live_events_start_date", table_name="live_events")
    op.drop_table("live_events")

    op.drop_index("ix_season_pass_xp_grants_source_type", table_name="season_pass_xp_grants")
    op.drop_index("ix_season_pass_xp_grants_user_id", table_name="season_pass_xp_grants")
    op.drop_table("season_pass_xp_grants")

    op.drop_index("ix_season_pass_claims_user_id", table_name="season_pass_claims")
    op.drop_table("season_pass_claims")

    op.drop_index("ix_season_passes_season_id", table_name="season_passes")
    op.drop_index("ix_season_passes_user_id", table_name="season_passes")
    op.drop_table("season_passes")

    op.drop_index("ix_player_relationships_teammate_player_id", table_name="player_relationships")
    op.drop_index("ix_player_relationships_player_id", table_name="player_relationships")
    op.drop_table("player_relationships")

    op.drop_index("ix_club_finance_transactions_transaction_type", table_name="club_finance_transactions")
    op.drop_index("ix_club_finance_transactions_user_id", table_name="club_finance_transactions")
    op.drop_table("club_finance_transactions")

    op.drop_index("ix_club_finance_sponsors_tier", table_name="club_finance_sponsors")
    op.drop_table("club_finance_sponsors")

    op.drop_index("ix_club_finance_profiles_balance", table_name="club_finance_profiles")
    op.drop_table("club_finance_profiles")

    op.drop_index("ix_predictions_resolved_at", table_name="predictions")
    op.drop_index("ix_predictions_user_id", table_name="predictions")
    op.drop_index("ix_predictions_match_id", table_name="predictions")
    op.drop_table("predictions")

    op.drop_column("ingestion_players", "morale")
