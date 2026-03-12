"""Add club reputation, replay archive, and league event persistence tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0008"
down_revision = "20260311_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_reputation_profile",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("current_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("highest_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("prestige_tier", sa.String(length=32), server_default=sa.text("'Local'"), nullable=False),
        sa.Column("total_seasons", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_active_season", sa.Integer(), nullable=True),
        sa.Column("last_rollup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_top_competition_seasons", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("consecutive_league_titles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("consecutive_continental_titles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_league_titles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_continental_qualifications", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_continental_titles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_world_super_cup_qualifications", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_world_super_cup_titles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_top_scorer_awards", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_top_assist_awards", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_club_reputation_profile"),
        sa.UniqueConstraint("club_id", name="uq_club_reputation_profile_club_id"),
    )
    op.create_index("ix_club_reputation_profile_club_id", "club_reputation_profile", ["club_id"], unique=False)

    op.create_table(
        "reputation_event_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("delta", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("score_after", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("milestone", sa.String(length=120), nullable=True),
        sa.Column("badge_code", sa.String(length=80), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reputation_event_log"),
    )
    op.create_index("ix_reputation_event_log_club_id", "reputation_event_log", ["club_id"], unique=False)
    op.create_index("ix_reputation_event_log_season", "reputation_event_log", ["season"], unique=False)

    op.create_table(
        "reputation_snapshot",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("score_before", sa.Integer(), nullable=False),
        sa.Column("season_delta", sa.Integer(), nullable=False),
        sa.Column("score_after", sa.Integer(), nullable=False),
        sa.Column("prestige_tier", sa.String(length=32), nullable=False),
        sa.Column("badges", sa.JSON(), nullable=False),
        sa.Column("milestones", sa.JSON(), nullable=False),
        sa.Column("event_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rolled_up_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reputation_snapshot"),
        sa.UniqueConstraint("club_id", "season", name="uq_reputation_snapshot_club_season"),
    )
    op.create_index("ix_reputation_snapshot_club_id", "reputation_snapshot", ["club_id"], unique=False)
    op.create_index("ix_reputation_snapshot_season", "reputation_snapshot", ["season"], unique=False)

    op.create_table(
        "league_event_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_league_event_records"),
    )
    op.create_index("ix_league_event_records_season_id", "league_event_records", ["season_id"], unique=False)

    op.create_table(
        "replay_archive_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("replay_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_whistle_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("home_club_json", sa.JSON(), nullable=False),
        sa.Column("away_club_json", sa.JSON(), nullable=False),
        sa.Column("scoreline_json", sa.JSON(), nullable=False),
        sa.Column("timeline_json", sa.JSON(), nullable=False),
        sa.Column("scorers_json", sa.JSON(), nullable=False),
        sa.Column("assisters_json", sa.JSON(), nullable=False),
        sa.Column("cards_json", sa.JSON(), nullable=False),
        sa.Column("injuries_json", sa.JSON(), nullable=False),
        sa.Column("substitutions_json", sa.JSON(), nullable=False),
        sa.Column("participant_user_ids_json", sa.JSON(), nullable=False),
        sa.Column("competition_context_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_replay_archive_records"),
        sa.UniqueConstraint("replay_id", "version", name="uq_replay_archive_records_replay_version"),
    )
    op.create_index("ix_replay_archive_records_replay_id", "replay_archive_records", ["replay_id"], unique=False)
    op.create_index("ix_replay_archive_records_fixture_id", "replay_archive_records", ["fixture_id"], unique=False)

    op.create_table(
        "replay_archive_countdowns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fixture_id", sa.String(length=120), nullable=False),
        sa.Column("replay_id", sa.String(length=120), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("home_club_json", sa.JSON(), nullable=False),
        sa.Column("away_club_json", sa.JSON(), nullable=False),
        sa.Column("competition_context_json", sa.JSON(), nullable=False),
        sa.Column("last_notification_key", sa.String(length=64), nullable=True),
        sa.Column("next_notification_key", sa.String(length=64), nullable=True),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_replay_archive_countdowns"),
        sa.UniqueConstraint("fixture_id", name="uq_replay_archive_countdowns_fixture_id"),
    )
    op.create_index("ix_replay_archive_countdowns_fixture_id", "replay_archive_countdowns", ["fixture_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_replay_archive_countdowns_fixture_id", table_name="replay_archive_countdowns")
    op.drop_table("replay_archive_countdowns")

    op.drop_index("ix_replay_archive_records_fixture_id", table_name="replay_archive_records")
    op.drop_index("ix_replay_archive_records_replay_id", table_name="replay_archive_records")
    op.drop_table("replay_archive_records")

    op.drop_index("ix_league_event_records_season_id", table_name="league_event_records")
    op.drop_table("league_event_records")

    op.drop_index("ix_reputation_snapshot_season", table_name="reputation_snapshot")
    op.drop_index("ix_reputation_snapshot_club_id", table_name="reputation_snapshot")
    op.drop_table("reputation_snapshot")

    op.drop_index("ix_reputation_event_log_season", table_name="reputation_event_log")
    op.drop_index("ix_reputation_event_log_club_id", table_name="reputation_event_log")
    op.drop_table("reputation_event_log")

    op.drop_index("ix_club_reputation_profile_club_id", table_name="club_reputation_profile")
    op.drop_table("club_reputation_profile")
