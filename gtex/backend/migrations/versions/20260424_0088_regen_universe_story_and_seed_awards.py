"""Add regen universe story surfaces and seed-capable award storage.

Revision ID: 20260424_0088_regen_universe_story_and_seed_awards
Revises: 20260424_0087_club_progression_intake_batches
Create Date: 2026-04-24 17:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260424_0088_regen_universe_story_and_seed_awards"
down_revision = "20260424_0087_club_progression_intake_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_achievements",
        sa.Column("achievement_key", sa.String(length=160), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("national_seed_id", sa.String(length=36), nullable=True),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("achievement_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["national_seed_id"], ["national_regen_seeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regen_achievements")),
        sa.UniqueConstraint("achievement_key", name="uq_regen_achievements_achievement_key"),
    )
    op.create_index("ix_regen_achievements_subject_key", "regen_achievements", ["subject_key"], unique=False)
    op.create_index("ix_regen_achievements_player_id", "regen_achievements", ["player_id"], unique=False)
    op.create_index(
        "ix_regen_achievements_national_seed_id",
        "regen_achievements",
        ["national_seed_id"],
        unique=False,
    )
    op.create_index(
        "ix_regen_achievements_achievement_type",
        "regen_achievements",
        ["achievement_type"],
        unique=False,
    )
    op.create_index("ix_regen_achievements_earned_at", "regen_achievements", ["earned_at"], unique=False)

    op.create_table(
        "regen_story_events",
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("national_seed_id", sa.String(length=36), nullable=True),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["national_seed_id"], ["national_regen_seeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regen_story_events")),
        sa.UniqueConstraint("event_key", name="uq_regen_story_events_event_key"),
    )
    op.create_index("ix_regen_story_events_subject_key", "regen_story_events", ["subject_key"], unique=False)
    op.create_index("ix_regen_story_events_player_id", "regen_story_events", ["player_id"], unique=False)
    op.create_index(
        "ix_regen_story_events_national_seed_id",
        "regen_story_events",
        ["national_seed_id"],
        unique=False,
    )
    op.create_index("ix_regen_story_events_event_type", "regen_story_events", ["event_type"], unique=False)
    op.create_index("ix_regen_story_events_occurred_at", "regen_story_events", ["occurred_at"], unique=False)

    with op.batch_alter_table("regen_universe_performance_records") as batch_op:
        batch_op.add_column(sa.Column("subject_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("national_seed_id", sa.String(length=36), nullable=True))
    op.execute(
        sa.text("UPDATE regen_universe_performance_records " "SET subject_key = player_id " "WHERE subject_key IS NULL")
    )
    with op.batch_alter_table("regen_universe_performance_records") as batch_op:
        batch_op.alter_column("subject_key", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.create_foreign_key(
            "fk_regen_universe_performance_records_national_seed_id",
            "national_regen_seeds",
            ["national_seed_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint("uq_regen_universe_performance_records_season_player", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_performance_records_season_subject",
            ["season_id", "subject_key"],
        )
        batch_op.create_index("ix_regen_universe_performance_records_subject_key", ["subject_key"], unique=False)
        batch_op.create_index(
            "ix_regen_universe_performance_records_national_seed_id",
            ["national_seed_id"],
            unique=False,
        )

    with op.batch_alter_table("regen_universe_ranking_snapshots") as batch_op:
        batch_op.add_column(sa.Column("subject_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("national_seed_id", sa.String(length=36), nullable=True))
    op.execute(
        sa.text("UPDATE regen_universe_ranking_snapshots " "SET subject_key = player_id " "WHERE subject_key IS NULL")
    )
    with op.batch_alter_table("regen_universe_ranking_snapshots") as batch_op:
        batch_op.alter_column("subject_key", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.create_foreign_key(
            "fk_regen_universe_ranking_snapshots_national_seed_id",
            "national_regen_seeds",
            ["national_seed_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint("uq_regen_universe_ranking_snapshots_category_player", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_ranking_snapshots_category_subject",
            ["season_id", "category", "subject_key"],
        )
        batch_op.create_index("ix_regen_universe_ranking_snapshots_subject_key", ["subject_key"], unique=False)
        batch_op.create_index(
            "ix_regen_universe_ranking_snapshots_national_seed_id",
            ["national_seed_id"],
            unique=False,
        )

    with op.batch_alter_table("regen_universe_award_winners") as batch_op:
        batch_op.add_column(sa.Column("subject_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("national_seed_id", sa.String(length=36), nullable=True))
    op.execute(
        sa.text("UPDATE regen_universe_award_winners " "SET subject_key = player_id " "WHERE subject_key IS NULL")
    )
    with op.batch_alter_table("regen_universe_award_winners") as batch_op:
        batch_op.alter_column("subject_key", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.create_foreign_key(
            "fk_regen_universe_award_winners_national_seed_id",
            "national_regen_seeds",
            ["national_seed_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint("uq_regen_universe_award_winners_award_season_player", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_award_winners_award_season_subject",
            ["award_id", "season_id", "subject_key"],
        )
        batch_op.create_index("ix_regen_universe_award_winners_subject_key", ["subject_key"], unique=False)
        batch_op.create_index(
            "ix_regen_universe_award_winners_national_seed_id",
            ["national_seed_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("regen_universe_award_winners") as batch_op:
        batch_op.drop_index("ix_regen_universe_award_winners_national_seed_id")
        batch_op.drop_index("ix_regen_universe_award_winners_subject_key")
        batch_op.drop_constraint("uq_regen_universe_award_winners_award_season_subject", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_award_winners_award_season_player",
            ["award_id", "season_id", "player_id"],
        )
        batch_op.drop_constraint("fk_regen_universe_award_winners_national_seed_id", type_="foreignkey")
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.drop_column("national_seed_id")
        batch_op.drop_column("subject_key")

    with op.batch_alter_table("regen_universe_ranking_snapshots") as batch_op:
        batch_op.drop_index("ix_regen_universe_ranking_snapshots_national_seed_id")
        batch_op.drop_index("ix_regen_universe_ranking_snapshots_subject_key")
        batch_op.drop_constraint("uq_regen_universe_ranking_snapshots_category_subject", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_ranking_snapshots_category_player",
            ["season_id", "category", "player_id"],
        )
        batch_op.drop_constraint("fk_regen_universe_ranking_snapshots_national_seed_id", type_="foreignkey")
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.drop_column("national_seed_id")
        batch_op.drop_column("subject_key")

    with op.batch_alter_table("regen_universe_performance_records") as batch_op:
        batch_op.drop_index("ix_regen_universe_performance_records_national_seed_id")
        batch_op.drop_index("ix_regen_universe_performance_records_subject_key")
        batch_op.drop_constraint("uq_regen_universe_performance_records_season_subject", type_="unique")
        batch_op.create_unique_constraint(
            "uq_regen_universe_performance_records_season_player",
            ["season_id", "player_id"],
        )
        batch_op.drop_constraint("fk_regen_universe_performance_records_national_seed_id", type_="foreignkey")
        batch_op.alter_column("player_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.drop_column("national_seed_id")
        batch_op.drop_column("subject_key")

    op.drop_index("ix_regen_story_events_occurred_at", table_name="regen_story_events")
    op.drop_index("ix_regen_story_events_event_type", table_name="regen_story_events")
    op.drop_index("ix_regen_story_events_national_seed_id", table_name="regen_story_events")
    op.drop_index("ix_regen_story_events_player_id", table_name="regen_story_events")
    op.drop_index("ix_regen_story_events_subject_key", table_name="regen_story_events")
    op.drop_table("regen_story_events")

    op.drop_index("ix_regen_achievements_earned_at", table_name="regen_achievements")
    op.drop_index("ix_regen_achievements_achievement_type", table_name="regen_achievements")
    op.drop_index("ix_regen_achievements_national_seed_id", table_name="regen_achievements")
    op.drop_index("ix_regen_achievements_player_id", table_name="regen_achievements")
    op.drop_index("ix_regen_achievements_subject_key", table_name="regen_achievements")
    op.drop_table("regen_achievements")
