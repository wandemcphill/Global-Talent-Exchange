from __future__ import annotations

from alembic import command as alembic_command
from sqlalchemy import create_engine, inspect

from app.core import database as database_module

REQUIRED_REGEN_TABLES = {
    "career_events",
    "national_regen_seeds",
    "regen_creation_orders",
    "regen_agents",
    "regen_achievements",
    "regen_attribute_profiles",
    "regen_bloodline_links",
    "regen_personality_profiles",
    "regen_profiles",
    "regen_scouts",
    "regen_story_events",
    "regen_universe_award_winners",
    "regen_universe_awards",
    "regen_universe_hall_of_fame",
    "regen_universe_performance_records",
    "regen_universe_ranking_snapshots",
    "regen_universe_seasons",
    "youth_academies",
}


def test_regen_head_upgrade_materializes_required_tables_and_columns(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'regen-phase-migrations.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    try:
        config = database_module.build_alembic_config(database_url)
        alembic_command.upgrade(config, "head")

        inspector = inspect(engine)
        missing_tables = sorted(table for table in REQUIRED_REGEN_TABLES if not inspector.has_table(table))
        assert not missing_tables, "Missing migrated regen tables: " + ", ".join(missing_tables)

        national_seed_columns = {column["name"] for column in inspector.get_columns("national_regen_seeds")}
        assert {"age", "age_band", "seed_key", "status", "primary_position"} <= national_seed_columns

        national_seed_indexes = {index["name"] for index in inspector.get_indexes("national_regen_seeds")}
        assert {
            "ix_national_regen_seeds_age_band",
            "ix_national_regen_seeds_country_age_band_position_status",
        } <= national_seed_indexes

        academy_batch_columns = {column["name"] for column in inspector.get_columns("academy_intake_batches")}
        assert {"season_id", "trigger_reason", "idempotency_key"} <= academy_batch_columns

        academy_batch_indexes = {index["name"] for index in inspector.get_indexes("academy_intake_batches")}
        assert {
            "ix_academy_intake_batches_idempotency_key",
            "ix_academy_intake_batches_season_id",
            "ix_academy_intake_batches_trigger_reason",
        } <= academy_batch_indexes

        rental_contract_fks = inspector.get_foreign_keys("national_team_rental_contracts")
        rental_member_fks = inspector.get_foreign_keys("national_team_rental_squad_members")
        assert all("player_id" not in set(fk.get("constrained_columns") or ()) for fk in rental_contract_fks)
        assert all("player_id" not in set(fk.get("constrained_columns") or ()) for fk in rental_member_fks)

        performance_columns = {column["name"] for column in inspector.get_columns("regen_universe_performance_records")}
        ranking_columns = {column["name"] for column in inspector.get_columns("regen_universe_ranking_snapshots")}
        award_columns = {column["name"] for column in inspector.get_columns("regen_universe_award_winners")}
        assert {"subject_key", "national_seed_id"} <= performance_columns
        assert {"subject_key", "national_seed_id"} <= ranking_columns
        assert {"subject_key", "national_seed_id"} <= award_columns
    finally:
        engine.dispose()


def test_regen_models_are_registered_in_target_metadata() -> None:
    metadata = database_module.get_target_metadata()
    missing_tables = sorted(table for table in REQUIRED_REGEN_TABLES if table not in metadata.tables)
    assert not missing_tables, "Regen tables missing from Alembic target metadata: " + ", ".join(missing_tables)
