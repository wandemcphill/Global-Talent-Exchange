"""Add fan prediction system tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0016_fan_prediction"
down_revision = "20260317_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fixture_status = sa.Enum(
        "scheduled",
        "open",
        "locked",
        "pending_settlement",
        "settled",
        "cancelled",
        name="fan_prediction_fixture_status",
    )
    submission_status = sa.Enum(
        "submitted",
        "settled",
        "cancelled",
        name="fan_prediction_submission_status",
    )
    token_reason = sa.Enum(
        "daily_refill",
        "season_pass_bonus",
        "prediction_submission",
        "prediction_refund",
        "admin_adjustment",
        name="fan_prediction_token_reason",
    )
    reward_type = sa.Enum("fancoin", "badge", name="fan_prediction_reward_type")
    leaderboard_scope = sa.Enum("match", "weekly", "creator_club_weekly", name="fan_prediction_leaderboard_scope")

    op.create_table(
        "fan_prediction_fixtures",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", fixture_status, nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locks_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewards_disbursed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_cost", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("promo_pool_fancoin", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("reward_funding_source", sa.String(length=64), nullable=False, server_default=sa.text("'gtex_promotional_pool'")),
        sa.Column("badge_code", sa.String(length=64), nullable=True),
        sa.Column("max_reward_winners", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("allow_creator_club_segmentation", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("settlement_rule_version", sa.String(length=32), nullable=False, server_default=sa.text("'fan_prediction_v1'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["away_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_prediction_fixtures"),
        sa.UniqueConstraint("match_id", name="uq_fan_prediction_fixtures_match"),
    )

    op.create_table(
        "fan_prediction_outcomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fixture_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("first_goal_scorer_player_id", sa.String(length=36), nullable=True),
        sa.Column("total_goals", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("mvp_player_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=48), nullable=False, server_default=sa.text("'match_completion'")),
        sa.Column("settled_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fan_prediction_fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_prediction_outcomes"),
        sa.UniqueConstraint("fixture_id", name="uq_fan_prediction_outcomes_fixture"),
    )

    op.create_table(
        "fan_prediction_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fixture_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fan_segment_club_id", sa.String(length=36), nullable=True),
        sa.Column("fan_group_id", sa.String(length=36), nullable=True),
        sa.Column("leaderboard_week_start", sa.Date(), nullable=False),
        sa.Column("winner_club_id", sa.String(length=36), nullable=False),
        sa.Column("first_goal_scorer_player_id", sa.String(length=36), nullable=False),
        sa.Column("total_goals", sa.Integer(), nullable=False),
        sa.Column("mvp_player_id", sa.String(length=36), nullable=False),
        sa.Column("tokens_spent", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", submission_status, nullable=False, server_default=sa.text("'submitted'")),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("correct_pick_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("perfect_card", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reward_rank", sa.Integer(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fan_prediction_fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fan_segment_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fan_group_id"], ["creator_fan_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_prediction_submissions"),
        sa.UniqueConstraint("fixture_id", "user_id", name="uq_fan_prediction_submissions_fixture_user"),
    )

    op.create_table(
        "fan_prediction_token_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_pass_id", sa.String(length=36), nullable=True),
        sa.Column("submission_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reason", token_reason, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("unique_key", sa.String(length=120), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_pass_id"], ["creator_season_passes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["fan_prediction_submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_prediction_token_ledger"),
        sa.UniqueConstraint("unique_key", name="uq_fan_prediction_token_ledger_unique_key"),
    )

    op.create_table(
        "fan_prediction_reward_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fixture_id", sa.String(length=36), nullable=True),
        sa.Column("submission_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("reward_settlement_id", sa.String(length=36), nullable=True),
        sa.Column("awarded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("leaderboard_scope", leaderboard_scope, nullable=False, server_default=sa.text("'match'")),
        sa.Column("reward_type", reward_type, nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("badge_code", sa.String(length=64), nullable=True),
        sa.Column("fancoin_amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("promo_pool_reference", sa.String(length=128), nullable=True),
        sa.Column("unique_key", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fixture_id"], ["fan_prediction_fixtures.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["fan_prediction_submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reward_settlement_id"], ["reward_settlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["awarded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_prediction_reward_grants"),
        sa.UniqueConstraint("unique_key", name="uq_fan_prediction_reward_grants_unique_key"),
    )


def downgrade() -> None:
    op.drop_table("fan_prediction_reward_grants")
    op.drop_table("fan_prediction_token_ledger")
    op.drop_table("fan_prediction_submissions")
    op.drop_table("fan_prediction_outcomes")
    op.drop_table("fan_prediction_fixtures")
