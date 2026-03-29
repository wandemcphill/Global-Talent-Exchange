"""Add GTEX unified jackpot, creator market, and AI league economy tables.

Revision ID: 20260329_0064_gtex_unified_economy
Revises: 20260329_0063_global_memory_dynasty
Create Date: 2026-03-29 11:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0064_gtex_unified_economy"
down_revision = "20260329_0063_global_memory_dynasty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gtex_leagues",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("league_type", sa.String(length=32), nullable=False),
        sa.Column("min_elo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_elo", sa.Integer(), nullable=False, server_default="4000"),
        sa.Column("default_entry_fee", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("ai_backfill_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("leaderboard_key", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_leagues"),
        sa.UniqueConstraint("code", name="uq_gtex_leagues_code"),
    )
    op.create_index("ix_gtex_leagues_code", "gtex_leagues", ["code"], unique=False)

    op.create_table(
        "gtex_jackpot_rounds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("pool_key", sa.String(length=64), nullable=False, server_default="global"),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("distribution_mode", sa.String(length=32), nullable=False, server_default="single_winner"),
        sa.Column("threshold_amount", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("max_probability_limit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("probability_cap", sa.Numeric(10, 4), nullable=False, server_default="0.5000"),
        sa.Column("contribution_rate", sa.Numeric(10, 4), nullable=False, server_default="0.1000"),
        sa.Column("current_balance", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("winner_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("top_split_percent", sa.Numeric(10, 4), nullable=False, server_default="0.1000"),
        sa.Column("min_activity_score", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("trigger_mode", sa.String(length=32), nullable=True),
        sa.Column("trigger_reason", sa.String(length=255), nullable=True),
        sa.Column("winning_user_id", sa.String(length=36), nullable=True),
        sa.Column("failsafe_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["winning_user_id"], ["users.id"], name="fk_gtex_jackpot_rounds_winning_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_jackpot_rounds"),
        sa.UniqueConstraint("pool_key", "round_number", name="uq_gtex_jackpot_rounds_pool_round"),
    )
    op.create_index("ix_gtex_jackpot_rounds_pool_key", "gtex_jackpot_rounds", ["pool_key"], unique=False)
    op.create_index("ix_gtex_jackpot_rounds_status", "gtex_jackpot_rounds", ["status"], unique=False)
    op.create_index("ix_gtex_jackpot_rounds_failsafe_at", "gtex_jackpot_rounds", ["failsafe_at"], unique=False)

    op.create_table(
        "gtex_ai_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("league_id", sa.String(length=36), nullable=True),
        sa.Column("profile_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("skill_level", sa.Numeric(10, 4), nullable=False),
        sa.Column("playstyle", sa.String(length=64), nullable=False),
        sa.Column("adaptation_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("aggression", sa.Numeric(10, 4), nullable=False),
        sa.Column("elo", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["league_id"], ["gtex_leagues.id"], name="fk_gtex_ai_profiles_league_id_gtex_leagues", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_ai_profiles"),
    )
    op.create_index("ix_gtex_ai_profiles_league_id", "gtex_ai_profiles", ["league_id"], unique=False)
    op.create_index("ix_gtex_ai_profiles_name", "gtex_ai_profiles", ["name"], unique=False)
    op.create_index("ix_gtex_ai_profiles_elo", "gtex_ai_profiles", ["elo"], unique=False)

    op.create_table(
        "gtex_creator_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_user_id", sa.String(length=36), nullable=True),
        sa.Column("subject_ai_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("base_price", sa.Numeric(20, 4), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 4), nullable=False),
        sa.Column("total_shares", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("available_shares", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("circulating_shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demand_score", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("momentum_score", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_volume", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["subject_ai_id"], ["gtex_ai_profiles.id"], name="fk_gtex_creator_assets_subject_ai_id_gtex_ai_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"], name="fk_gtex_creator_assets_subject_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_creator_assets"),
        sa.UniqueConstraint("subject_key", name="uq_gtex_creator_assets_subject_key"),
    )
    op.create_index("ix_gtex_creator_assets_subject_key", "gtex_creator_assets", ["subject_key"], unique=False)
    op.create_index("ix_gtex_creator_assets_subject_user_id", "gtex_creator_assets", ["subject_user_id"], unique=False)
    op.create_index("ix_gtex_creator_assets_subject_ai_id", "gtex_creator_assets", ["subject_ai_id"], unique=False)
    op.create_index("ix_gtex_creator_assets_display_name", "gtex_creator_assets", ["display_name"], unique=False)

    op.create_table(
        "gtex_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("league_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("home_participant_type", sa.String(length=16), nullable=False),
        sa.Column("home_user_id", sa.String(length=36), nullable=True),
        sa.Column("home_ai_id", sa.String(length=36), nullable=True),
        sa.Column("away_participant_type", sa.String(length=16), nullable=False),
        sa.Column("away_user_id", sa.String(length=36), nullable=True),
        sa.Column("away_ai_id", sa.String(length=36), nullable=True),
        sa.Column("entry_fee", sa.Numeric(20, 4), nullable=False),
        sa.Column("effective_pot", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("jackpot_contribution", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("home_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("away_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winner_participant_type", sa.String(length=16), nullable=True),
        sa.Column("winner_user_id", sa.String(length=36), nullable=True),
        sa.Column("winner_ai_id", sa.String(length=36), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_score", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["away_ai_id"], ["gtex_ai_profiles.id"], name="fk_gtex_matches_away_ai_id_gtex_ai_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["away_user_id"], ["users.id"], name="fk_gtex_matches_away_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_ai_id"], ["gtex_ai_profiles.id"], name="fk_gtex_matches_home_ai_id_gtex_ai_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_user_id"], ["users.id"], name="fk_gtex_matches_home_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["league_id"], ["gtex_leagues.id"], name="fk_gtex_matches_league_id_gtex_leagues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], name="fk_gtex_matches_requested_by_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_ai_id"], ["gtex_ai_profiles.id"], name="fk_gtex_matches_winner_ai_id_gtex_ai_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], name="fk_gtex_matches_winner_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_matches"),
    )
    op.create_index("ix_gtex_matches_league_id", "gtex_matches", ["league_id"], unique=False)
    op.create_index("ix_gtex_matches_status", "gtex_matches", ["status"], unique=False)
    op.create_index("ix_gtex_matches_completed_at", "gtex_matches", ["completed_at"], unique=False)

    op.create_table(
        "gtex_match_queue_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("requester_user_id", sa.String(length=36), nullable=False),
        sa.Column("league_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("entry_fee", sa.Numeric(20, 4), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["league_id"], ["gtex_leagues.id"], name="fk_gtex_match_queue_entries_league_id_gtex_leagues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], name="fk_gtex_match_queue_entries_match_id_gtex_matches", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], name="fk_gtex_match_queue_entries_requester_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_match_queue_entries"),
    )
    op.create_index("ix_gtex_match_queue_entries_requester_user_id", "gtex_match_queue_entries", ["requester_user_id"], unique=False)
    op.create_index("ix_gtex_match_queue_entries_status", "gtex_match_queue_entries", ["status"], unique=False)
    op.create_index("ix_gtex_match_queue_entries_expires_at", "gtex_match_queue_entries", ["expires_at"], unique=False)

    op.create_table(
        "gtex_jackpot_contributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("participant_user_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("entry_fee", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("contribution_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("eligibility_score", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["participant_user_id"], ["users.id"], name="fk_gtex_jackpot_contributions_participant_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["round_id"], ["gtex_jackpot_rounds.id"], name="fk_gtex_jackpot_contributions_round_id_gtex_jackpot_rounds", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_jackpot_contributions"),
    )
    op.create_index("ix_gtex_jackpot_contributions_round_id", "gtex_jackpot_contributions", ["round_id"], unique=False)
    op.create_index("ix_gtex_jackpot_contributions_participant_user_id", "gtex_jackpot_contributions", ["participant_user_id"], unique=False)
    op.create_index("ix_gtex_jackpot_contributions_source_id", "gtex_jackpot_contributions", ["source_id"], unique=False)

    op.create_table(
        "gtex_jackpot_payouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payout_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("payout_ratio", sa.Numeric(10, 4), nullable=False, server_default="1.0000"),
        sa.Column("eligibility_weight", sa.Numeric(20, 4), nullable=False, server_default="1.0000"),
        sa.ForeignKeyConstraint(["round_id"], ["gtex_jackpot_rounds.id"], name="fk_gtex_jackpot_payouts_round_id_gtex_jackpot_rounds", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_gtex_jackpot_payouts_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_jackpot_payouts"),
    )
    op.create_index("ix_gtex_jackpot_payouts_round_id", "gtex_jackpot_payouts", ["round_id"], unique=False)
    op.create_index("ix_gtex_jackpot_payouts_user_id", "gtex_jackpot_payouts", ["user_id"], unique=False)

    op.create_table(
        "gtex_creator_holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("shares_owned", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("reserved_shares", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("avg_price", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.ForeignKeyConstraint(["player_id"], ["gtex_creator_assets.id"], name="fk_gtex_creator_holdings_player_id_gtex_creator_assets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_gtex_creator_holdings_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_creator_holdings"),
        sa.UniqueConstraint("user_id", "player_id", name="uq_gtex_creator_holdings_user_player"),
    )
    op.create_index("ix_gtex_creator_holdings_user_id", "gtex_creator_holdings", ["user_id"], unique=False)
    op.create_index("ix_gtex_creator_holdings_player_id", "gtex_creator_holdings", ["player_id"], unique=False)

    op.create_table(
        "gtex_creator_trades",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("buyer_id", sa.String(length=36), nullable=True),
        sa.Column("seller_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("shares", sa.Numeric(20, 4), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=False),
        sa.Column("gross_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("demand_impact", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("anomaly_flag", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], name="fk_gtex_creator_trades_buyer_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["gtex_creator_assets.id"], name="fk_gtex_creator_trades_player_id_gtex_creator_assets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], name="fk_gtex_creator_trades_seller_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_creator_trades"),
    )
    op.create_index("ix_gtex_creator_trades_player_id", "gtex_creator_trades", ["player_id"], unique=False)
    op.create_index("ix_gtex_creator_trades_buyer_id", "gtex_creator_trades", ["buyer_id"], unique=False)
    op.create_index("ix_gtex_creator_trades_seller_id", "gtex_creator_trades", ["seller_id"], unique=False)

    op.create_table(
        "gtex_creator_price_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=False),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("demand_score", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("reason", sa.String(length=128), nullable=False, server_default="revaluation"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_id"], ["gtex_creator_assets.id"], name="fk_gtex_creator_price_history_player_id_gtex_creator_assets", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_creator_price_history"),
    )
    op.create_index("ix_gtex_creator_price_history_player_id", "gtex_creator_price_history", ["player_id"], unique=False)

    op.create_table(
        "gtex_match_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("actor_key", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], name="fk_gtex_match_events_match_id_gtex_matches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_match_events"),
        sa.UniqueConstraint("match_id", "event_index", name="uq_gtex_match_events_match_event_index"),
    )
    op.create_index("ix_gtex_match_events_match_id", "gtex_match_events", ["match_id"], unique=False)

    op.create_table(
        "gtex_league_standings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("league_id", sa.String(length=36), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("participant_type", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("ai_id", sa.String(length=36), nullable=True),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("elo", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["ai_id"], ["gtex_ai_profiles.id"], name="fk_gtex_league_standings_ai_id_gtex_ai_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["league_id"], ["gtex_leagues.id"], name="fk_gtex_league_standings_league_id_gtex_leagues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_gtex_league_standings_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_league_standings"),
        sa.UniqueConstraint("league_id", "subject_key", name="uq_gtex_league_standings_league_subject"),
    )
    op.create_index("ix_gtex_league_standings_league_id", "gtex_league_standings", ["league_id"], unique=False)
    op.create_index("ix_gtex_league_standings_subject_key", "gtex_league_standings", ["subject_key"], unique=False)

    op.create_table(
        "gtex_risk_flags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("signal_score", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_risk_flags"),
    )
    op.create_index("ix_gtex_risk_flags_category", "gtex_risk_flags", ["category"], unique=False)
    op.create_index("ix_gtex_risk_flags_subject_key", "gtex_risk_flags", ["subject_key"], unique=False)
    op.create_index("ix_gtex_risk_flags_reference_id", "gtex_risk_flags", ["reference_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gtex_risk_flags_reference_id", table_name="gtex_risk_flags")
    op.drop_index("ix_gtex_risk_flags_subject_key", table_name="gtex_risk_flags")
    op.drop_index("ix_gtex_risk_flags_category", table_name="gtex_risk_flags")
    op.drop_table("gtex_risk_flags")

    op.drop_index("ix_gtex_league_standings_subject_key", table_name="gtex_league_standings")
    op.drop_index("ix_gtex_league_standings_league_id", table_name="gtex_league_standings")
    op.drop_table("gtex_league_standings")

    op.drop_index("ix_gtex_match_events_match_id", table_name="gtex_match_events")
    op.drop_table("gtex_match_events")

    op.drop_index("ix_gtex_creator_price_history_player_id", table_name="gtex_creator_price_history")
    op.drop_table("gtex_creator_price_history")

    op.drop_index("ix_gtex_creator_trades_seller_id", table_name="gtex_creator_trades")
    op.drop_index("ix_gtex_creator_trades_buyer_id", table_name="gtex_creator_trades")
    op.drop_index("ix_gtex_creator_trades_player_id", table_name="gtex_creator_trades")
    op.drop_table("gtex_creator_trades")

    op.drop_index("ix_gtex_creator_holdings_player_id", table_name="gtex_creator_holdings")
    op.drop_index("ix_gtex_creator_holdings_user_id", table_name="gtex_creator_holdings")
    op.drop_table("gtex_creator_holdings")

    op.drop_index("ix_gtex_jackpot_payouts_user_id", table_name="gtex_jackpot_payouts")
    op.drop_index("ix_gtex_jackpot_payouts_round_id", table_name="gtex_jackpot_payouts")
    op.drop_table("gtex_jackpot_payouts")

    op.drop_index("ix_gtex_jackpot_contributions_source_id", table_name="gtex_jackpot_contributions")
    op.drop_index("ix_gtex_jackpot_contributions_participant_user_id", table_name="gtex_jackpot_contributions")
    op.drop_index("ix_gtex_jackpot_contributions_round_id", table_name="gtex_jackpot_contributions")
    op.drop_table("gtex_jackpot_contributions")

    op.drop_index("ix_gtex_match_queue_entries_expires_at", table_name="gtex_match_queue_entries")
    op.drop_index("ix_gtex_match_queue_entries_status", table_name="gtex_match_queue_entries")
    op.drop_index("ix_gtex_match_queue_entries_requester_user_id", table_name="gtex_match_queue_entries")
    op.drop_table("gtex_match_queue_entries")

    op.drop_index("ix_gtex_matches_completed_at", table_name="gtex_matches")
    op.drop_index("ix_gtex_matches_status", table_name="gtex_matches")
    op.drop_index("ix_gtex_matches_league_id", table_name="gtex_matches")
    op.drop_table("gtex_matches")

    op.drop_index("ix_gtex_creator_assets_display_name", table_name="gtex_creator_assets")
    op.drop_index("ix_gtex_creator_assets_subject_ai_id", table_name="gtex_creator_assets")
    op.drop_index("ix_gtex_creator_assets_subject_user_id", table_name="gtex_creator_assets")
    op.drop_index("ix_gtex_creator_assets_subject_key", table_name="gtex_creator_assets")
    op.drop_table("gtex_creator_assets")

    op.drop_index("ix_gtex_ai_profiles_elo", table_name="gtex_ai_profiles")
    op.drop_index("ix_gtex_ai_profiles_name", table_name="gtex_ai_profiles")
    op.drop_index("ix_gtex_ai_profiles_league_id", table_name="gtex_ai_profiles")
    op.drop_table("gtex_ai_profiles")

    op.drop_index("ix_gtex_jackpot_rounds_failsafe_at", table_name="gtex_jackpot_rounds")
    op.drop_index("ix_gtex_jackpot_rounds_status", table_name="gtex_jackpot_rounds")
    op.drop_index("ix_gtex_jackpot_rounds_pool_key", table_name="gtex_jackpot_rounds")
    op.drop_table("gtex_jackpot_rounds")

    op.drop_index("ix_gtex_leagues_code", table_name="gtex_leagues")
    op.drop_table("gtex_leagues")
