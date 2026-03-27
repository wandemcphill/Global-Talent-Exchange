"""Add GTEX competitive integrity tables.

Revision ID: 20260327_0036_gtex_competitive_integrity
Revises: 20260326_0035_merge_parallel_feature_heads
Create Date: 2026-03-27 09:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0036_gtex_competitive_integrity"
down_revision = "20260326_0035_merge_parallel_feature_heads"
branch_labels = None
depends_on = None


manager_type = sa.Enum("user", "real_manager", name="competitive_manager_type", native_enum=False)
match_competition_type = sa.Enum("gtex_hosted", "fast_game", "casual", name="competitive_match_competition_type", native_enum=False)
match_status = sa.Enum("scheduled", "in_progress", "completed", "blocked", name="competitive_match_status", native_enum=False)
notification_status = sa.Enum("pending", "sent", "failed", name="competitive_notification_status", native_enum=False)
notification_channel = sa.Enum("push", "sms", name="competitive_notification_channel", native_enum=False)
match_control_side = sa.Enum("home", "away", name="match_control_side", native_enum=False)
match_controller_type = sa.Enum("user", "manager", "frozen", name="match_controller_type", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "competitive_managers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", manager_type, nullable=False),
        sa.Column("appointed_user_id", sa.String(length=36), nullable=True),
        sa.Column("instructions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("tactical_profile", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="1000"),
        sa.ForeignKeyConstraint(["appointed_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitive_managers_user_id", "competitive_managers", ["user_id"], unique=False)
    op.create_index("ix_competitive_managers_type", "competitive_managers", ["type"], unique=False)
    op.create_index("ix_competitive_managers_appointed_user_id", "competitive_managers", ["appointed_user_id"], unique=False)

    op.create_table(
        "fast_game_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("manager_locked_id", sa.String(length=36), nullable=True),
        sa.Column("entry_fee_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("base_reward_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("base_rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("scaling_factor", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("reward_amount_paid", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["manager_locked_id"], ["competitive_managers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fast_game_runs_user_id", "fast_game_runs", ["user_id"], unique=False)
    op.create_index("ix_fast_game_runs_is_active", "fast_game_runs", ["is_active"], unique=False)

    op.create_table(
        "competitive_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_type", match_competition_type, nullable=False),
        sa.Column("home_user_id", sa.String(length=36), nullable=False),
        sa.Column("away_user_id", sa.String(length=36), nullable=False),
        sa.Column("home_manager_id", sa.String(length=36), nullable=True),
        sa.Column("away_manager_id", sa.String(length=36), nullable=True),
        sa.Column("fast_game_run_id", sa.String(length=36), nullable=True),
        sa.Column("is_user_online_home", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_user_online_away", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_lineup_home", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("locked_lineup_away", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", match_status, nullable=False, server_default="scheduled"),
        sa.Column("result_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["away_manager_id"], ["competitive_managers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["away_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fast_game_run_id"], ["fast_game_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_manager_id"], ["competitive_managers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitive_matches_competition_type", "competitive_matches", ["competition_type"], unique=False)
    op.create_index("ix_competitive_matches_home_user_id", "competitive_matches", ["home_user_id"], unique=False)
    op.create_index("ix_competitive_matches_away_user_id", "competitive_matches", ["away_user_id"], unique=False)
    op.create_index("ix_competitive_matches_kickoff_at", "competitive_matches", ["kickoff_at"], unique=False)
    op.create_index("ix_competitive_matches_status", "competitive_matches", ["status"], unique=False)

    op.create_table(
        "competitive_notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", notification_status, nullable=False, server_default="pending"),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitive_notifications_user_id", "competitive_notifications", ["user_id"], unique=False)
    op.create_index("ix_competitive_notifications_status", "competitive_notifications", ["status"], unique=False)
    op.create_index("ix_competitive_notifications_channel", "competitive_notifications", ["channel"], unique=False)
    op.create_index("ix_competitive_notifications_scheduled_for", "competitive_notifications", ["scheduled_for"], unique=False)

    op.create_table(
        "match_control_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("side", match_control_side, nullable=False),
        sa.Column("controller_type", match_controller_type, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["match_id"], ["competitive_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_control_logs_match_id", "match_control_logs", ["match_id"], unique=False)
    op.create_index("ix_match_control_logs_side", "match_control_logs", ["side"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_match_control_logs_side", table_name="match_control_logs")
    op.drop_index("ix_match_control_logs_match_id", table_name="match_control_logs")
    op.drop_table("match_control_logs")

    op.drop_index("ix_competitive_notifications_scheduled_for", table_name="competitive_notifications")
    op.drop_index("ix_competitive_notifications_channel", table_name="competitive_notifications")
    op.drop_index("ix_competitive_notifications_status", table_name="competitive_notifications")
    op.drop_index("ix_competitive_notifications_user_id", table_name="competitive_notifications")
    op.drop_table("competitive_notifications")

    op.drop_index("ix_competitive_matches_status", table_name="competitive_matches")
    op.drop_index("ix_competitive_matches_kickoff_at", table_name="competitive_matches")
    op.drop_index("ix_competitive_matches_away_user_id", table_name="competitive_matches")
    op.drop_index("ix_competitive_matches_home_user_id", table_name="competitive_matches")
    op.drop_index("ix_competitive_matches_competition_type", table_name="competitive_matches")
    op.drop_table("competitive_matches")

    op.drop_index("ix_fast_game_runs_is_active", table_name="fast_game_runs")
    op.drop_index("ix_fast_game_runs_user_id", table_name="fast_game_runs")
    op.drop_table("fast_game_runs")

    op.drop_index("ix_competitive_managers_appointed_user_id", table_name="competitive_managers")
    op.drop_index("ix_competitive_managers_type", table_name="competitive_managers")
    op.drop_index("ix_competitive_managers_user_id", table_name="competitive_managers")
    op.drop_table("competitive_managers")
