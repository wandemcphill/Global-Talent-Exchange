from __future__ import annotations

from sqlalchemy import create_engine, inspect

from backend.app.core.database import ensure_database_schema_current


def test_persistence_migrations_create_expected_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'persistence-migrations.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    ensure_database_schema_current(engine)

    inspector = inspect(engine)
    assert inspector.has_table("club_reputation_profile")
    assert inspector.has_table("reputation_event_log")
    assert inspector.has_table("reputation_snapshot")
    assert inspector.has_table("league_event_records")
    assert inspector.has_table("replay_archive_records")
    assert inspector.has_table("replay_archive_countdowns")
    assert inspector.has_table("fast_cup_records")

    engine.dispose()
