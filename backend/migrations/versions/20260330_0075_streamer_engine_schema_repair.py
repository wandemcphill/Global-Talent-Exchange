"""Repair streamer enum drift and missing leaderboard season tables.

Revision ID: 20260330_0075_streamer_engine_schema_repair
Revises: 20260330_0074_player_share_market_schema_repair
Create Date: 2026-03-30 09:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_0075_streamer_engine_schema_repair"
down_revision = "20260330_0074_player_share_market_schema_repair"
branch_labels = None
depends_on = None


leaderboard_season_status = sa.Enum(
    "active",
    "ended",
    name="leaderboard_season_status",
    native_enum=False,
)

leaderboard_reset_strategy = sa.Enum(
    "hard",
    "soft",
    name="leaderboard_reset_strategy",
    native_enum=False,
)

leaderboard_reward_delivery_status = sa.Enum(
    "pending",
    "distributed",
    "failed",
    name="leaderboard_reward_delivery_status",
    native_enum=False,
)

STREAMER_ENUM_COLUMNS = (
    ("streamer_tournaments", "tournament_type"),
    ("streamer_tournaments", "status"),
    ("streamer_tournaments", "approval_status"),
    ("streamer_tournament_invites", "status"),
    ("streamer_tournament_entries", "qualification_source"),
    ("streamer_tournament_entries", "status"),
    ("streamer_tournament_rewards", "reward_type"),
    ("streamer_tournament_risk_signals", "status"),
    ("streamer_tournament_reward_grants", "reward_type"),
    ("streamer_tournament_reward_grants", "settlement_status"),
)

LEADERBOARD_ENUM_COLUMNS = (
    ("leaderboard_seasons", "status"),
    ("leaderboard_seasons", "reset_strategy"),
    ("leaderboard_season_rewards", "status"),
)


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


def _normalize_enum_columns(bind, *, columns: tuple[tuple[str, str], ...]) -> None:
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name
    for table_name, column_name in columns:
        if not inspector.has_table(table_name):
            continue
        if dialect_name == "postgresql":
            column_type = next(
                (column["type"] for column in inspector.get_columns(table_name) if column["name"] == column_name),
                None,
            )
            if isinstance(column_type, sa.Enum):
                continue
            bind.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                    SET {column_name} = LOWER({column_name}::text)
                    WHERE {column_name} IS NOT NULL
                      AND {column_name}::text <> LOWER({column_name}::text)
                    """
                )
            )
            continue
        bind.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET {column_name} = LOWER({column_name})
                WHERE {column_name} IS NOT NULL
                  AND {column_name} <> LOWER({column_name})
                """
            )
        )


def _ensure_leaderboard_tables(bind) -> None:
    inspector = sa.inspect(bind)
    leaderboard_season_status.create(bind, checkfirst=True)
    leaderboard_reset_strategy.create(bind, checkfirst=True)
    leaderboard_reward_delivery_status.create(bind, checkfirst=True)

    if not inspector.has_table("leaderboard_seasons"):
        op.create_table(
            "leaderboard_seasons",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", leaderboard_season_status, nullable=False, server_default="active"),
            sa.Column("default_rating", sa.Integer(), nullable=False, server_default="1200"),
            sa.Column("k_factor", sa.Integer(), nullable=False, server_default="32"),
            sa.Column("reset_strategy", leaderboard_reset_strategy, nullable=False, server_default="soft"),
            sa.Column("soft_reset_factor", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rewards_distributed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("leaderboard_seasons"):
        _create_index_if_missing(bind, table_name="leaderboard_seasons", index_name="ix_leaderboard_seasons_start_date", columns=["start_date"])
        _create_index_if_missing(bind, table_name="leaderboard_seasons", index_name="ix_leaderboard_seasons_end_date", columns=["end_date"])
        _create_index_if_missing(
            bind,
            table_name="leaderboard_seasons",
            index_name="ix_leaderboard_seasons_status_dates",
            columns=["status", "start_date", "end_date"],
        )

    if not inspector.has_table("leaderboard_player_ratings"):
        op.create_table(
            "leaderboard_player_ratings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("season_id", sa.String(length=36), nullable=False),
            sa.Column("player_id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=160), nullable=False),
            sa.Column("region", sa.String(length=32), nullable=True),
            sa.Column("division", sa.String(length=32), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("highest_rating", sa.Integer(), nullable=False, server_default="1200"),
            sa.Column("last_rating_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_match_id", sa.String(length=128), nullable=True),
            sa.Column("last_result", sa.Float(), nullable=True),
            sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season_id", "player_id", name="uq_leaderboard_player_ratings_season_player"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("leaderboard_player_ratings"):
        _create_index_if_missing(bind, table_name="leaderboard_player_ratings", index_name="ix_leaderboard_player_ratings_season_id", columns=["season_id"])
        _create_index_if_missing(bind, table_name="leaderboard_player_ratings", index_name="ix_leaderboard_player_ratings_player_id", columns=["player_id"])
        _create_index_if_missing(bind, table_name="leaderboard_player_ratings", index_name="ix_leaderboard_player_ratings_region", columns=["region"])
        _create_index_if_missing(bind, table_name="leaderboard_player_ratings", index_name="ix_leaderboard_player_ratings_division", columns=["division"])
        _create_index_if_missing(
            bind,
            table_name="leaderboard_player_ratings",
            index_name="ix_leaderboard_player_ratings_season_rating",
            columns=["season_id", "rating"],
        )
        _create_index_if_missing(
            bind,
            table_name="leaderboard_player_ratings",
            index_name="ix_leaderboard_player_ratings_season_region",
            columns=["season_id", "region"],
        )
        _create_index_if_missing(
            bind,
            table_name="leaderboard_player_ratings",
            index_name="ix_leaderboard_player_ratings_season_division",
            columns=["season_id", "division"],
        )

    if not inspector.has_table("leaderboard_match_results"):
        op.create_table(
            "leaderboard_match_results",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("season_id", sa.String(length=36), nullable=False),
            sa.Column("match_id", sa.String(length=128), nullable=False),
            sa.Column("source_event_id", sa.String(length=64), nullable=True),
            sa.Column("player_a_id", sa.String(length=64), nullable=False),
            sa.Column("player_b_id", sa.String(length=64), nullable=False),
            sa.Column("result", sa.Float(), nullable=False),
            sa.Column("player_a_rating_before", sa.Integer(), nullable=False),
            sa.Column("player_b_rating_before", sa.Integer(), nullable=False),
            sa.Column("player_a_rating_after", sa.Integer(), nullable=False),
            sa.Column("player_b_rating_after", sa.Integer(), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season_id", "match_id", name="uq_leaderboard_match_results_season_match"),
            sa.UniqueConstraint("source_event_id", name="uq_leaderboard_match_results_source_event"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("leaderboard_match_results"):
        _create_index_if_missing(bind, table_name="leaderboard_match_results", index_name="ix_leaderboard_match_results_season_id", columns=["season_id"])
        _create_index_if_missing(bind, table_name="leaderboard_match_results", index_name="ix_leaderboard_match_results_match_id", columns=["match_id"])
        _create_index_if_missing(
            bind,
            table_name="leaderboard_match_results",
            index_name="ix_leaderboard_match_results_source_event_id",
            columns=["source_event_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="leaderboard_match_results",
            index_name="ix_leaderboard_match_results_processed_at",
            columns=["processed_at"],
        )
        _create_index_if_missing(bind, table_name="leaderboard_match_results", index_name="ix_leaderboard_match_results_player_a_id", columns=["player_a_id"])
        _create_index_if_missing(bind, table_name="leaderboard_match_results", index_name="ix_leaderboard_match_results_player_b_id", columns=["player_b_id"])

    if not inspector.has_table("leaderboard_season_snapshots"):
        op.create_table(
            "leaderboard_season_snapshots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("season_id", sa.String(length=36), nullable=False),
            sa.Column("board_key", sa.String(length=96), nullable=False),
            sa.Column("player_id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=160), nullable=False),
            sa.Column("region", sa.String(length=32), nullable=True),
            sa.Column("division", sa.String(length=32), nullable=True),
            sa.Column("rank_position", sa.Integer(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_snapshots_board_player"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("leaderboard_season_snapshots"):
        _create_index_if_missing(bind, table_name="leaderboard_season_snapshots", index_name="ix_leaderboard_season_snapshots_season_id", columns=["season_id"])
        _create_index_if_missing(bind, table_name="leaderboard_season_snapshots", index_name="ix_leaderboard_season_snapshots_board_key", columns=["board_key"])
        _create_index_if_missing(bind, table_name="leaderboard_season_snapshots", index_name="ix_leaderboard_season_snapshots_player_id", columns=["player_id"])
        _create_index_if_missing(bind, table_name="leaderboard_season_snapshots", index_name="ix_leaderboard_season_snapshots_region", columns=["region"])
        _create_index_if_missing(bind, table_name="leaderboard_season_snapshots", index_name="ix_leaderboard_season_snapshots_division", columns=["division"])
        _create_index_if_missing(
            bind,
            table_name="leaderboard_season_snapshots",
            index_name="ix_leaderboard_season_snapshots_captured_at",
            columns=["captured_at"],
        )
        _create_index_if_missing(
            bind,
            table_name="leaderboard_season_snapshots",
            index_name="ix_leaderboard_season_snapshots_season_board_rank",
            columns=["season_id", "board_key", "rank_position"],
        )

    if not inspector.has_table("leaderboard_season_rewards"):
        op.create_table(
            "leaderboard_season_rewards",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("season_id", sa.String(length=36), nullable=False),
            sa.Column("board_key", sa.String(length=96), nullable=False, server_default="global"),
            sa.Column("player_id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=160), nullable=False),
            sa.Column("rank_position", sa.Integer(), nullable=False),
            sa.Column("coins", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
            sa.Column("trophies", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("badges_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("status", leaderboard_reward_delivery_status, nullable=False, server_default="pending"),
            sa.Column("distributed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_rewards_board_player"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("leaderboard_season_rewards"):
        _create_index_if_missing(bind, table_name="leaderboard_season_rewards", index_name="ix_leaderboard_season_rewards_season_id", columns=["season_id"])
        _create_index_if_missing(bind, table_name="leaderboard_season_rewards", index_name="ix_leaderboard_season_rewards_player_id", columns=["player_id"])
        _create_index_if_missing(
            bind,
            table_name="leaderboard_season_rewards",
            index_name="ix_leaderboard_season_rewards_ledger_transaction_id",
            columns=["ledger_transaction_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="leaderboard_season_rewards",
            index_name="ix_leaderboard_season_rewards_season_rank",
            columns=["season_id", "board_key", "rank_position"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    _normalize_enum_columns(bind, columns=STREAMER_ENUM_COLUMNS)
    _ensure_leaderboard_tables(bind)
    _normalize_enum_columns(bind, columns=LEADERBOARD_ENUM_COLUMNS)


def downgrade() -> None:
    pass
