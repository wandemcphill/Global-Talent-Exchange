"""Repair history engagement schema drift on stamped databases.

Revision ID: 20260401_0079_history_engagement_schema_repair
Revises: 20260330_0078_user_role_width_repair
Create Date: 2026-04-01 12:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0079_history_engagement_schema_repair"
down_revision = "20260330_0078_user_role_width_repair"
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


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if index_name not in _index_names(bind, table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _ensure_history_tables(bind) -> None:
    if not _has_table(bind, "historical_records"):
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
    if _has_table(bind, "historical_records"):
        _create_index_if_missing(
            bind,
            table_name="historical_records",
            index_name="ix_historical_records_type",
            columns=["type"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_records",
            index_name="ix_historical_records_subject_type",
            columns=["subject_type"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_records",
            index_name="ix_historical_records_subject_id",
            columns=["subject_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_records",
            index_name="ix_historical_records_timestamp",
            columns=["timestamp"],
        )

    if not _has_table(bind, "historical_leaderboard_entries"):
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
    if _has_table(bind, "historical_leaderboard_entries"):
        _create_index_if_missing(
            bind,
            table_name="historical_leaderboard_entries",
            index_name="ix_historical_leaderboard_entries_board_key",
            columns=["board_key"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_leaderboard_entries",
            index_name="ix_historical_leaderboard_entries_entity_type",
            columns=["entity_type"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_leaderboard_entries",
            index_name="ix_historical_leaderboard_entries_entity_id",
            columns=["entity_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_leaderboard_entries",
            index_name="ix_historical_leaderboard_entries_rank",
            columns=["rank"],
        )
        _create_index_if_missing(
            bind,
            table_name="historical_leaderboard_entries",
            index_name="ix_historical_leaderboard_entries_generated_at",
            columns=["generated_at"],
        )

    if not _has_table(bind, "achievements"):
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
    if _has_table(bind, "achievements"):
        _create_index_if_missing(
            bind,
            table_name="achievements",
            index_name="ix_achievements_achievement_key",
            columns=["achievement_key"],
        )

    if not _has_table(bind, "user_achievements"):
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
    if _has_table(bind, "user_achievements"):
        _create_index_if_missing(
            bind,
            table_name="user_achievements",
            index_name="ix_user_achievements_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_achievements",
            index_name="ix_user_achievements_achievement_id",
            columns=["achievement_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_achievements",
            index_name="ix_user_achievements_unlocked_at",
            columns=["unlocked_at"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_achievements",
            index_name="ix_user_achievements_reward_settlement_id",
            columns=["reward_settlement_id"],
        )

    if not _has_table(bind, "milestone_progress"):
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
    if _has_table(bind, "milestone_progress"):
        _create_index_if_missing(
            bind,
            table_name="milestone_progress",
            index_name="ix_milestone_progress_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="milestone_progress",
            index_name="ix_milestone_progress_milestone_key",
            columns=["milestone_key"],
        )

    if not _has_table(bind, "user_profiles"):
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
    if _has_table(bind, "user_profiles"):
        _create_index_if_missing(
            bind,
            table_name="user_profiles",
            index_name="ix_user_profiles_user_id",
            columns=["user_id"],
        )

    if not _has_table(bind, "user_follows"):
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
    if _has_table(bind, "user_follows"):
        _create_index_if_missing(
            bind,
            table_name="user_follows",
            index_name="ix_user_follows_follower_user_id",
            columns=["follower_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_follows",
            index_name="ix_user_follows_target_key",
            columns=["target_key"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_follows",
            index_name="ix_user_follows_target_user_id",
            columns=["target_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_follows",
            index_name="ix_user_follows_target_club_id",
            columns=["target_club_id"],
        )

    if not _has_table(bind, "social_activities"):
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
    if _has_table(bind, "social_activities"):
        _create_index_if_missing(
            bind,
            table_name="social_activities",
            index_name="ix_social_activities_actor_user_id",
            columns=["actor_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="social_activities",
            index_name="ix_social_activities_activity_type",
            columns=["activity_type"],
        )
        _create_index_if_missing(
            bind,
            table_name="social_activities",
            index_name="ix_social_activities_target_user_id",
            columns=["target_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="social_activities",
            index_name="ix_social_activities_target_club_id",
            columns=["target_club_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="social_activities",
            index_name="ix_social_activities_rivalry_key",
            columns=["rivalry_key"],
        )


def _ensure_objective_tables(bind) -> None:
    if not _has_table(bind, "daily_tasks"):
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
    if _has_table(bind, "daily_tasks"):
        _create_index_if_missing(
            bind,
            table_name="daily_tasks",
            index_name="ix_daily_tasks_task_key",
            columns=["task_key"],
        )

    if not _has_table(bind, "weekly_tasks"):
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
    if _has_table(bind, "weekly_tasks"):
        _create_index_if_missing(
            bind,
            table_name="weekly_tasks",
            index_name="ix_weekly_tasks_task_key",
            columns=["task_key"],
        )

    if not _has_table(bind, "user_objective_progress"):
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
    if _has_table(bind, "user_objective_progress"):
        _create_index_if_missing(
            bind,
            table_name="user_objective_progress",
            index_name="ix_user_objective_progress_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_objective_progress",
            index_name="ix_user_objective_progress_task_frequency",
            columns=["task_frequency"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_objective_progress",
            index_name="ix_user_objective_progress_task_key",
            columns=["task_key"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_objective_progress",
            index_name="ix_user_objective_progress_period_key",
            columns=["period_key"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_objective_progress",
            index_name="ix_user_objective_progress_reward_settlement_id",
            columns=["reward_settlement_id"],
        )

    if not _has_table(bind, "user_streaks"):
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
    if _has_table(bind, "user_streaks"):
        _create_index_if_missing(
            bind,
            table_name="user_streaks",
            index_name="ix_user_streaks_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_streaks",
            index_name="ix_user_streaks_last_completed_on",
            columns=["last_completed_on"],
        )


def _ensure_season_pass_tables(bind) -> None:
    if not _has_table(bind, "season_pass_seasons"):
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
    if _has_table(bind, "season_pass_seasons"):
        _create_index_if_missing(
            bind,
            table_name="season_pass_seasons",
            index_name="ix_season_pass_seasons_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="season_pass_seasons",
            index_name="ix_season_pass_seasons_starts_at",
            columns=["starts_at"],
        )
        _create_index_if_missing(
            bind,
            table_name="season_pass_seasons",
            index_name="ix_season_pass_seasons_ends_at",
            columns=["ends_at"],
        )

    if not _has_table(bind, "season_pass_rewards"):
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
    if _has_table(bind, "season_pass_rewards"):
        _create_index_if_missing(
            bind,
            table_name="season_pass_rewards",
            index_name="ix_season_pass_rewards_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="season_pass_rewards",
            index_name="ix_season_pass_rewards_level",
            columns=["level"],
        )

    if not _has_table(bind, "season_pass_missions"):
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
    if _has_table(bind, "season_pass_missions"):
        _create_index_if_missing(
            bind,
            table_name="season_pass_missions",
            index_name="ix_season_pass_missions_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="season_pass_missions",
            index_name="ix_season_pass_missions_mission_key",
            columns=["mission_key"],
        )

    if not _has_table(bind, "user_season_progress"):
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
    if _has_table(bind, "user_season_progress"):
        _create_index_if_missing(
            bind,
            table_name="user_season_progress",
            index_name="ix_user_season_progress_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_progress",
            index_name="ix_user_season_progress_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_progress",
            index_name="ix_user_season_progress_last_synced_at",
            columns=["last_synced_at"],
        )

    if not _has_table(bind, "user_season_reward_claims"):
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
    if _has_table(bind, "user_season_reward_claims"):
        _create_index_if_missing(
            bind,
            table_name="user_season_reward_claims",
            index_name="ix_user_season_reward_claims_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_reward_claims",
            index_name="ix_user_season_reward_claims_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_reward_claims",
            index_name="ix_user_season_reward_claims_reward_id",
            columns=["reward_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_reward_claims",
            index_name="ix_user_season_reward_claims_claimed_at",
            columns=["claimed_at"],
        )

    if not _has_table(bind, "user_season_mission_progress"):
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
    if _has_table(bind, "user_season_mission_progress"):
        _create_index_if_missing(
            bind,
            table_name="user_season_mission_progress",
            index_name="ix_user_season_mission_progress_user_id",
            columns=["user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_mission_progress",
            index_name="ix_user_season_mission_progress_season_id",
            columns=["season_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_mission_progress",
            index_name="ix_user_season_mission_progress_mission_id",
            columns=["mission_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="user_season_mission_progress",
            index_name="ix_user_season_mission_progress_period_key",
            columns=["period_key"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_history_tables(bind)
    _ensure_objective_tables(bind)
    _ensure_season_pass_tables(bind)


def downgrade() -> None:
    return None
