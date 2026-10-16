"""Add history, achievements, social, and objective systems.

Revision ID: 20260327_0042_history_engagement_engine
Revises: 20260327_0041_merge_transfer_market_and_universe_heads
Create Date: 2026-03-27 18:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0042_history_engagement_engine"
down_revision = "20260327_0041_merge_transfer_market_and_universe_heads"
branch_labels = None
depends_on = None


historical_record_type_enum = sa.Enum(
    "match",
    "season",
    "player",
    "club",
    "competition",
    name="historicalrecordtype",
    native_enum=False,
)
achievement_category_enum = sa.Enum(
    "performance",
    "progression",
    "rare",
    "social",
    name="achievementcategory",
    native_enum=False,
)
follow_target_type_enum = sa.Enum(
    "manager",
    "club",
    name="followtargettype",
    native_enum=False,
)
objective_frequency_enum = sa.Enum(
    "daily",
    "weekly",
    name="objectivefrequency",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "historical_records",
        sa.Column("type", historical_record_type_enum, nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=True),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_records")),
    )
    op.create_index("ix_historical_records_type", "historical_records", ["type"], unique=False)
    op.create_index("ix_historical_records_subject_type", "historical_records", ["subject_type"], unique=False)
    op.create_index("ix_historical_records_subject_id", "historical_records", ["subject_id"], unique=False)
    op.create_index("ix_historical_records_timestamp", "historical_records", ["timestamp"], unique=False)

    op.create_table(
        "historical_leaderboard_entries",
        sa.Column("board_key", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("entity_name", sa.String(length=180), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_leaderboard_entries")),
        sa.UniqueConstraint("board_key", "entity_id", name="uq_historical_leaderboard_entries_board_entity"),
    )
    op.create_index("ix_historical_leaderboard_entries_board_key", "historical_leaderboard_entries", ["board_key"], unique=False)
    op.create_index("ix_historical_leaderboard_entries_entity_type", "historical_leaderboard_entries", ["entity_type"], unique=False)
    op.create_index("ix_historical_leaderboard_entries_entity_id", "historical_leaderboard_entries", ["entity_id"], unique=False)
    op.create_index("ix_historical_leaderboard_entries_rank", "historical_leaderboard_entries", ["rank"], unique=False)
    op.create_index("ix_historical_leaderboard_entries_generated_at", "historical_leaderboard_entries", ["generated_at"], unique=False)

    op.create_table(
        "achievements",
        sa.Column("achievement_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", achievement_category_enum, nullable=False),
        sa.Column("condition", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reward", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_achievements")),
        sa.UniqueConstraint("achievement_key", name="uq_achievements_achievement_key"),
    )
    op.create_index("ix_achievements_achievement_key", "achievements", ["achievement_key"], unique=False)

    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("achievement_id", sa.String(length=36), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reward_settlement_id", sa.String(length=36), nullable=True),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_settlement_id"], ["reward_settlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_achievements")),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievements_user_achievement"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"], unique=False)
    op.create_index("ix_user_achievements_achievement_id", "user_achievements", ["achievement_id"], unique=False)
    op.create_index("ix_user_achievements_unlocked_at", "user_achievements", ["unlocked_at"], unique=False)
    op.create_index("ix_user_achievements_reward_settlement_id", "user_achievements", ["reward_settlement_id"], unique=False)

    op.create_table(
        "milestone_progress",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("milestone_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("current_value", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("best_value", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_milestone_progress")),
        sa.UniqueConstraint("user_id", "milestone_key", name="uq_milestone_progress_user_key"),
    )
    op.create_index("ix_milestone_progress_user_id", "milestone_progress", ["user_id"], unique=False)
    op.create_index("ix_milestone_progress_milestone_key", "milestone_progress", ["milestone_key"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("following", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reputation_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("profile_boost_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("badge_inventory_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("cosmetic_inventory_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_profiles")),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=False)

    op.create_table(
        "user_follows",
        sa.Column("follower_user_id", sa.String(length=36), nullable=False),
        sa.Column("target_key", sa.String(length=96), nullable=False),
        sa.Column("target_type", follow_target_type_enum, nullable=False),
        sa.Column("target_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_club_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["follower_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_follows")),
        sa.UniqueConstraint("follower_user_id", "target_key", name="uq_user_follows_follower_target"),
    )
    op.create_index("ix_user_follows_follower_user_id", "user_follows", ["follower_user_id"], unique=False)
    op.create_index("ix_user_follows_target_key", "user_follows", ["target_key"], unique=False)
    op.create_index("ix_user_follows_target_user_id", "user_follows", ["target_user_id"], unique=False)
    op.create_index("ix_user_follows_target_club_id", "user_follows", ["target_club_id"], unique=False)

    op.create_table(
        "social_activities",
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("activity_type", sa.String(length=48), nullable=False),
        sa.Column("target_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_club_id", sa.String(length=36), nullable=True),
        sa.Column("rivalry_key", sa.String(length=96), nullable=True),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_social_activities")),
    )
    op.create_index("ix_social_activities_actor_user_id", "social_activities", ["actor_user_id"], unique=False)
    op.create_index("ix_social_activities_activity_type", "social_activities", ["activity_type"], unique=False)
    op.create_index("ix_social_activities_target_user_id", "social_activities", ["target_user_id"], unique=False)
    op.create_index("ix_social_activities_target_club_id", "social_activities", ["target_club_id"], unique=False)
    op.create_index("ix_social_activities_rivalry_key", "social_activities", ["rivalry_key"], unique=False)

    op.create_table(
        "daily_tasks",
        sa.Column("task_key", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reward", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("condition", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_tasks")),
        sa.UniqueConstraint("task_key", name="uq_daily_tasks_task_key"),
    )
    op.create_index("ix_daily_tasks_task_key", "daily_tasks", ["task_key"], unique=False)

    op.create_table(
        "weekly_tasks",
        sa.Column("task_key", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reward", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("condition", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_tasks")),
        sa.UniqueConstraint("task_key", name="uq_weekly_tasks_task_key"),
    )
    op.create_index("ix_weekly_tasks_task_key", "weekly_tasks", ["task_key"], unique=False)

    op.create_table(
        "season_pass_seasons",
        sa.Column("season_id", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("levels", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("xp_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("premium_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_pass_seasons")),
        sa.UniqueConstraint("season_id", name="uq_season_pass_seasons_season_id"),
    )
    op.create_index("ix_season_pass_seasons_season_id", "season_pass_seasons", ["season_id"], unique=False)
    op.create_index("ix_season_pass_seasons_starts_at", "season_pass_seasons", ["starts_at"], unique=False)
    op.create_index("ix_season_pass_seasons_ends_at", "season_pass_seasons", ["ends_at"], unique=False)

    op.create_table(
        "season_pass_rewards",
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("premium_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["season_id"], ["season_pass_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_pass_rewards")),
        sa.UniqueConstraint("season_id", "level", "premium_only", name="uq_season_pass_rewards_season_level_track"),
    )
    op.create_index("ix_season_pass_rewards_season_id", "season_pass_rewards", ["season_id"], unique=False)
    op.create_index("ix_season_pass_rewards_level", "season_pass_rewards", ["level"], unique=False)

    op.create_table(
        "season_pass_missions",
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("mission_key", sa.String(length=80), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False, server_default=sa.text("'daily'")),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("condition", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["season_id"], ["season_pass_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_pass_missions")),
        sa.UniqueConstraint("season_id", "mission_key", "frequency", name="uq_season_pass_missions_season_key_frequency"),
    )
    op.create_index("ix_season_pass_missions_season_id", "season_pass_missions", ["season_id"], unique=False)
    op.create_index("ix_season_pass_missions_mission_key", "season_pass_missions", ["mission_key"], unique=False)

    op.create_table(
        "user_objective_progress",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("task_frequency", objective_frequency_enum, nullable=False),
        sa.Column("task_key", sa.String(length=80), nullable=False),
        sa.Column("period_key", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("progress_value", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("reward_multiplier", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_settlement_id", sa.String(length=36), nullable=True),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["reward_settlement_id"], ["reward_settlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_objective_progress")),
        sa.UniqueConstraint(
            "user_id",
            "task_frequency",
            "task_key",
            "period_key",
            name="uq_user_objective_progress_user_task_period",
        ),
    )
    op.create_index("ix_user_objective_progress_user_id", "user_objective_progress", ["user_id"], unique=False)
    op.create_index("ix_user_objective_progress_task_frequency", "user_objective_progress", ["task_frequency"], unique=False)
    op.create_index("ix_user_objective_progress_task_key", "user_objective_progress", ["task_key"], unique=False)
    op.create_index("ix_user_objective_progress_period_key", "user_objective_progress", ["period_key"], unique=False)
    op.create_index("ix_user_objective_progress_reward_settlement_id", "user_objective_progress", ["reward_settlement_id"], unique=False)

    op.create_table(
        "user_season_progress",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("current_level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("has_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["season_id"], ["season_pass_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_season_progress")),
        sa.UniqueConstraint("user_id", "season_id", name="uq_user_season_progress_user_season"),
    )
    op.create_index("ix_user_season_progress_user_id", "user_season_progress", ["user_id"], unique=False)
    op.create_index("ix_user_season_progress_season_id", "user_season_progress", ["season_id"], unique=False)
    op.create_index("ix_user_season_progress_last_synced_at", "user_season_progress", ["last_synced_at"], unique=False)

    op.create_table(
        "user_season_reward_claims",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("reward_id", sa.String(length=36), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("granted_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["reward_id"], ["season_pass_rewards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["season_pass_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_season_reward_claims")),
        sa.UniqueConstraint("user_id", "reward_id", name="uq_user_season_reward_claims_user_reward"),
    )
    op.create_index("ix_user_season_reward_claims_user_id", "user_season_reward_claims", ["user_id"], unique=False)
    op.create_index("ix_user_season_reward_claims_season_id", "user_season_reward_claims", ["season_id"], unique=False)
    op.create_index("ix_user_season_reward_claims_reward_id", "user_season_reward_claims", ["reward_id"], unique=False)
    op.create_index("ix_user_season_reward_claims_claimed_at", "user_season_reward_claims", ["claimed_at"], unique=False)

    op.create_table(
        "user_season_mission_progress",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("period_key", sa.String(length=24), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False, server_default=sa.text("'daily'")),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("progress_value", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["mission_id"], ["season_pass_missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["season_pass_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_season_mission_progress")),
        sa.UniqueConstraint("user_id", "mission_id", "period_key", name="uq_user_season_mission_progress_user_mission_period"),
    )
    op.create_index("ix_user_season_mission_progress_user_id", "user_season_mission_progress", ["user_id"], unique=False)
    op.create_index("ix_user_season_mission_progress_season_id", "user_season_mission_progress", ["season_id"], unique=False)
    op.create_index("ix_user_season_mission_progress_mission_id", "user_season_mission_progress", ["mission_id"], unique=False)
    op.create_index("ix_user_season_mission_progress_period_key", "user_season_mission_progress", ["period_key"], unique=False)

    op.create_table(
        "user_streaks",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_completed_on", sa.Date(), nullable=True),
        sa.Column("reward_multiplier", sa.Numeric(8, 4), nullable=False, server_default=sa.text("1.0000")),
        sa.Column("xp_boost_multiplier", sa.Numeric(8, 4), nullable=False, server_default=sa.text("1.0000")),
        sa.Column("coin_boost_multiplier", sa.Numeric(8, 4), nullable=False, server_default=sa.text("1.0000")),
        sa.Column("warning_sent_on", sa.Date(), nullable=True),
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_streaks")),
        sa.UniqueConstraint("user_id", name="uq_user_streaks_user_id"),
    )
    op.create_index("ix_user_streaks_user_id", "user_streaks", ["user_id"], unique=False)
    op.create_index("ix_user_streaks_last_completed_on", "user_streaks", ["last_completed_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_streaks_last_completed_on", table_name="user_streaks")
    op.drop_index("ix_user_streaks_user_id", table_name="user_streaks")
    op.drop_table("user_streaks")

    op.drop_index("ix_user_season_mission_progress_period_key", table_name="user_season_mission_progress")
    op.drop_index("ix_user_season_mission_progress_mission_id", table_name="user_season_mission_progress")
    op.drop_index("ix_user_season_mission_progress_season_id", table_name="user_season_mission_progress")
    op.drop_index("ix_user_season_mission_progress_user_id", table_name="user_season_mission_progress")
    op.drop_table("user_season_mission_progress")

    op.drop_index("ix_user_season_reward_claims_claimed_at", table_name="user_season_reward_claims")
    op.drop_index("ix_user_season_reward_claims_reward_id", table_name="user_season_reward_claims")
    op.drop_index("ix_user_season_reward_claims_season_id", table_name="user_season_reward_claims")
    op.drop_index("ix_user_season_reward_claims_user_id", table_name="user_season_reward_claims")
    op.drop_table("user_season_reward_claims")

    op.drop_index("ix_user_season_progress_last_synced_at", table_name="user_season_progress")
    op.drop_index("ix_user_season_progress_season_id", table_name="user_season_progress")
    op.drop_index("ix_user_season_progress_user_id", table_name="user_season_progress")
    op.drop_table("user_season_progress")

    op.drop_index("ix_user_objective_progress_reward_settlement_id", table_name="user_objective_progress")
    op.drop_index("ix_user_objective_progress_period_key", table_name="user_objective_progress")
    op.drop_index("ix_user_objective_progress_task_key", table_name="user_objective_progress")
    op.drop_index("ix_user_objective_progress_task_frequency", table_name="user_objective_progress")
    op.drop_index("ix_user_objective_progress_user_id", table_name="user_objective_progress")
    op.drop_table("user_objective_progress")

    op.drop_index("ix_season_pass_missions_mission_key", table_name="season_pass_missions")
    op.drop_index("ix_season_pass_missions_season_id", table_name="season_pass_missions")
    op.drop_table("season_pass_missions")

    op.drop_index("ix_season_pass_rewards_level", table_name="season_pass_rewards")
    op.drop_index("ix_season_pass_rewards_season_id", table_name="season_pass_rewards")
    op.drop_table("season_pass_rewards")

    op.drop_index("ix_season_pass_seasons_ends_at", table_name="season_pass_seasons")
    op.drop_index("ix_season_pass_seasons_starts_at", table_name="season_pass_seasons")
    op.drop_index("ix_season_pass_seasons_season_id", table_name="season_pass_seasons")
    op.drop_table("season_pass_seasons")

    op.drop_index("ix_weekly_tasks_task_key", table_name="weekly_tasks")
    op.drop_table("weekly_tasks")

    op.drop_index("ix_daily_tasks_task_key", table_name="daily_tasks")
    op.drop_table("daily_tasks")

    op.drop_index("ix_social_activities_rivalry_key", table_name="social_activities")
    op.drop_index("ix_social_activities_target_club_id", table_name="social_activities")
    op.drop_index("ix_social_activities_target_user_id", table_name="social_activities")
    op.drop_index("ix_social_activities_activity_type", table_name="social_activities")
    op.drop_index("ix_social_activities_actor_user_id", table_name="social_activities")
    op.drop_table("social_activities")

    op.drop_index("ix_user_follows_target_club_id", table_name="user_follows")
    op.drop_index("ix_user_follows_target_user_id", table_name="user_follows")
    op.drop_index("ix_user_follows_target_key", table_name="user_follows")
    op.drop_index("ix_user_follows_follower_user_id", table_name="user_follows")
    op.drop_table("user_follows")

    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index("ix_milestone_progress_milestone_key", table_name="milestone_progress")
    op.drop_index("ix_milestone_progress_user_id", table_name="milestone_progress")
    op.drop_table("milestone_progress")

    op.drop_index("ix_user_achievements_reward_settlement_id", table_name="user_achievements")
    op.drop_index("ix_user_achievements_unlocked_at", table_name="user_achievements")
    op.drop_index("ix_user_achievements_achievement_id", table_name="user_achievements")
    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_table("user_achievements")

    op.drop_index("ix_achievements_achievement_key", table_name="achievements")
    op.drop_table("achievements")

    op.drop_index("ix_historical_leaderboard_entries_generated_at", table_name="historical_leaderboard_entries")
    op.drop_index("ix_historical_leaderboard_entries_rank", table_name="historical_leaderboard_entries")
    op.drop_index("ix_historical_leaderboard_entries_entity_id", table_name="historical_leaderboard_entries")
    op.drop_index("ix_historical_leaderboard_entries_entity_type", table_name="historical_leaderboard_entries")
    op.drop_index("ix_historical_leaderboard_entries_board_key", table_name="historical_leaderboard_entries")
    op.drop_table("historical_leaderboard_entries")

    op.drop_index("ix_historical_records_timestamp", table_name="historical_records")
    op.drop_index("ix_historical_records_subject_id", table_name="historical_records")
    op.drop_index("ix_historical_records_subject_type", table_name="historical_records")
    op.drop_index("ix_historical_records_type", table_name="historical_records")
    op.drop_table("historical_records")
