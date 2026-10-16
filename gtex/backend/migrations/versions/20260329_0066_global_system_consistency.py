"""Add global consistency projection and ranking support.

Revision ID: 20260329_0066_global_system_consistency
Revises: 20260329_0065_commentary_personalities_and_club_dao, 20260329_0065_event_reliability_guards
Create Date: 2026-03-29 18:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0066_global_system_consistency"
down_revision = (
    "20260329_0065_commentary_personalities_and_club_dao",
    "20260329_0065_event_reliability_guards",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "player_history",
        sa.Column("event_type", sa.String(length=64), nullable=False, server_default="history_recorded"),
    )
    op.add_column("player_history", sa.Column("global_player_id", sa.String(length=80), nullable=True))
    op.add_column("player_history", sa.Column("global_competition_id", sa.String(length=80), nullable=True))
    op.add_column("player_history", sa.Column("global_match_id", sa.String(length=80), nullable=True))
    op.add_column(
        "player_history",
        sa.Column("timeline_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_player_history_event_type", "player_history", ["event_type"], unique=False)
    op.create_index("ix_player_history_global_player_id", "player_history", ["global_player_id"], unique=False)
    op.create_index(
        "ix_player_history_global_competition_id",
        "player_history",
        ["global_competition_id"],
        unique=False,
    )
    op.create_index("ix_player_history_global_match_id", "player_history", ["global_match_id"], unique=False)

    op.add_column(
        "user_dynasty",
        sa.Column("earnings_minor", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_dynasty",
        sa.Column("player_development_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "user_dynasty",
        sa.Column("legacy_boost_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column("user_dynasty", sa.Column("last_event_id", sa.String(length=36), nullable=True))
    op.create_index("ix_user_dynasty_last_event_id", "user_dynasty", ["last_event_id"], unique=False)

    op.add_column(
        "global_regen_evolution",
        sa.Column("scarcity_tier", sa.String(length=24), nullable=False, server_default="rare"),
    )
    op.add_column(
        "global_regen_evolution",
        sa.Column("unique_traits_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "global_regen_evolution",
        sa.Column("legacy_boost_score", sa.Float(), nullable=False, server_default="0.0"),
    )

    op.create_table(
        "global_projection_checkpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("projection_name", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_global_projection_checkpoints"),
        sa.UniqueConstraint(
            "projection_name",
            "event_id",
            name="uq_global_projection_checkpoints_projection_event",
        ),
    )
    op.create_index(
        "ix_global_projection_checkpoints_projection_name",
        "global_projection_checkpoints",
        ["projection_name"],
        unique=False,
    )
    op.create_index(
        "ix_global_projection_checkpoints_event_id",
        "global_projection_checkpoints",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_global_projection_checkpoints_event_name",
        "global_projection_checkpoints",
        ["event_name"],
        unique=False,
    )
    op.create_index(
        "ix_global_projection_checkpoints_aggregate_id",
        "global_projection_checkpoints",
        ["aggregate_id"],
        unique=False,
    )

    op.create_table(
        "national_team_country_rankings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("elo_rating", sa.Float(), nullable=False, server_default="1500.0"),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("titles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_competition_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_national_team_country_rankings"),
        sa.UniqueConstraint("country_code", name="uq_national_team_country_rankings_country_code"),
    )
    op.create_index(
        "ix_national_team_country_rankings_country_code",
        "national_team_country_rankings",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        "ix_national_team_country_rankings_last_competition_id",
        "national_team_country_rankings",
        ["last_competition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_national_team_country_rankings_last_competition_id",
        table_name="national_team_country_rankings",
    )
    op.drop_index(
        "ix_national_team_country_rankings_country_code",
        table_name="national_team_country_rankings",
    )
    op.drop_table("national_team_country_rankings")

    op.drop_index(
        "ix_global_projection_checkpoints_aggregate_id",
        table_name="global_projection_checkpoints",
    )
    op.drop_index(
        "ix_global_projection_checkpoints_event_name",
        table_name="global_projection_checkpoints",
    )
    op.drop_index(
        "ix_global_projection_checkpoints_event_id",
        table_name="global_projection_checkpoints",
    )
    op.drop_index(
        "ix_global_projection_checkpoints_projection_name",
        table_name="global_projection_checkpoints",
    )
    op.drop_table("global_projection_checkpoints")

    op.drop_column("global_regen_evolution", "legacy_boost_score")
    op.drop_column("global_regen_evolution", "unique_traits_json")
    op.drop_column("global_regen_evolution", "scarcity_tier")

    op.drop_index("ix_user_dynasty_last_event_id", table_name="user_dynasty")
    op.drop_column("user_dynasty", "last_event_id")
    op.drop_column("user_dynasty", "legacy_boost_score")
    op.drop_column("user_dynasty", "player_development_score")
    op.drop_column("user_dynasty", "earnings_minor")

    op.drop_index("ix_player_history_global_match_id", table_name="player_history")
    op.drop_index("ix_player_history_global_competition_id", table_name="player_history")
    op.drop_index("ix_player_history_global_player_id", table_name="player_history")
    op.drop_index("ix_player_history_event_type", table_name="player_history")
    op.drop_column("player_history", "timeline_json")
    op.drop_column("player_history", "global_match_id")
    op.drop_column("player_history", "global_competition_id")
    op.drop_column("player_history", "global_player_id")
    op.drop_column("player_history", "event_type")
