"""Upgrade the division migrations on a throwaway sqlite file.

These revisions are not run against a project database. The test builds only
the tables the revisions alter, then calls upgrade through Alembic operations.
"""

from __future__ import annotations

import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, UniqueConstraint, create_engine, inspect, text


def _upgrade(module, connection) -> None:
    original = module.op
    try:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
    finally:
        module.op = original


def test_foundation_migrations_upgrade_on_temporary_sqlite(tmp_path) -> None:
    database_path = tmp_path / "gtex-division-migrations.db"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    metadata = MetaData()
    Table("users", metadata, Column("id", String(36), primary_key=True))
    Table(
        "national_team_country_rankings",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("created_at", String(40), nullable=False),
        Column("updated_at", String(40), nullable=False),
        Column("country_code", String(8), nullable=False),
        Column("country_name", String(120), nullable=False),
        Column("elo_rating", Float, nullable=False, server_default="1500.0"),
        Column("matches_played", Integer, nullable=False, server_default="0"),
        Column("wins", Integer, nullable=False, server_default="0"),
        Column("draws", Integer, nullable=False, server_default="0"),
        Column("losses", Integer, nullable=False, server_default="0"),
        Column("titles", Integer, nullable=False, server_default="0"),
        Column("last_competition_id", String(36), nullable=True),
        Column("metadata_json", String, nullable=False, server_default="{}"),
        UniqueConstraint("country_code", name="uq_national_team_country_rankings_country_code"),
    )
    Table(
        "owner_club_states",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("club_id", String(36), nullable=False),
    )
    metadata.create_all(engine)

    migration_0232 = importlib.import_module(
        "migrations.versions.20261110_0232_competition_flag_bearers_and_foundation"
    )
    migration_0233 = importlib.import_module("migrations.versions.20261110_0233_division_season_memory")
    migration_0234 = importlib.import_module("migrations.versions.20261110_0234_champions_league_played_matches")

    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id) VALUES ('user-1')"))
        connection.execute(text("""
                INSERT INTO national_team_country_rankings (
                    id, created_at, updated_at, country_code, country_name, elo_rating,
                    matches_played, wins, draws, losses, titles, metadata_json
                ) VALUES (
                    'rank-1', '2026-11-10', '2026-11-10', 'NG', 'Nigeria', 1500,
                    0, 0, 0, 0, 0, '{}'
                )
                """))
        connection.execute(text("INSERT INTO owner_club_states (id, club_id) VALUES ('club-state-1', 'club-1')"))
        _upgrade(migration_0232, connection)
        _upgrade(migration_0233, connection)
        _upgrade(migration_0234, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        assert "national_team_flag_bearers" in tables
        assert "national_team_result_memories" in tables
        assert "champions_league_played_matches" in tables

        ranking_columns = {column["name"] for column in inspector.get_columns("national_team_country_rankings")}
        assert {"age_band", "competition_family"} <= ranking_columns
        unique_names = {
            constraint["name"] for constraint in inspector.get_unique_constraints("national_team_country_rankings")
        }
        assert "uq_national_team_country_rankings_scope" in unique_names

        club_columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
        assert "division_level" in club_columns
        assert "division_season_ids" in club_columns
        row = connection.execute(
            text("SELECT division_level, division_season_ids FROM owner_club_states WHERE id = 'club-state-1'")
        ).one()
        assert row.division_level == "foundation"
        assert row.division_season_ids in ("[]", [])
        kept = connection.execute(
            text("SELECT country_code FROM national_team_country_rankings WHERE id = 'rank-1'")
        ).scalar_one()
        assert kept == "NG"

    engine.dispose()
