"""Regression test: a fresh database must reach alembic head.

Revisions 0108-0111 shipped with bare op.alter_column / op.create_foreign_key
calls (rejected by SQLite, which supports neither) and compared the boolean
`active` column against the integer 1 (rejected by PostgreSQL). Neither backend
could replay the chain, which meant no new environment could be provisioned and
every HTTP-level backend test errored during fixture setup.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"

# Every revision that predates 0108 already guards these operations behind a
# dialect check or batch_alter_table; this list pins the ones that regressed.
PORTABILITY_SENSITIVE_REVISIONS = (
    "20260821_0108_gift_currency_semantics.py",
    "20260822_0109_competition_fee_policy_default.py",
    "20260822_0110_agent_wallet_fail_closed.py",
    "20260822_0111_hosted_competition_template_fee_default.py",
)

_BARE_ALTER = re.compile(r"^\s*op\.(alter_column|create_foreign_key|drop_constraint)\(", re.MULTILINE)
_BOOLEAN_INT_COMPARISON = re.compile(r"\bactive\s*=\s*[01]\b")


@pytest.mark.parametrize("filename", PORTABILITY_SENSITIVE_REVISIONS)
def test_revision_avoids_sqlite_incompatible_operations(filename: str) -> None:
    source = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    offenders = _BARE_ALTER.findall(source)
    assert not offenders, f"{filename} uses bare op.{offenders} instead of batch_alter_table"


@pytest.mark.parametrize("filename", PORTABILITY_SENSITIVE_REVISIONS)
def test_revision_avoids_boolean_integer_comparison(filename: str) -> None:
    source = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    match = _BOOLEAN_INT_COMPARISON.search(source)
    assert match is None, f"{filename} compares the boolean 'active' column to {match.group(0)!r}"


def test_fresh_database_upgrades_to_head(tmp_path: Path) -> None:
    from alembic import command
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    from app.core.database import build_alembic_config

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration_replay.db').as_posix()}"
    config = build_alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            applied = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))
    finally:
        engine.dispose()

    expected_head = ScriptDirectory.from_config(config).get_current_head()
    assert applied == (expected_head,)


def test_calibration_migration_0251_supports_seeded_sqlite(tmp_path: Path) -> None:
    import json

    from alembic import command
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.database import build_alembic_config, load_model_modules
    from app.ingestion.models import Player
    from app.models.base import Base, utcnow
    from app.models.legendary_player import LegendaryPlayerProfile
    from app.models.player_token_market import PlayerShareMarket
    from app.players.read_models import PlayerSummaryReadModel

    load_model_modules()
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'seeded_0251.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        now = utcnow()
        player_ids = [
            ("d3d75031-9136-470a-a98e-4d3e13cac3b2", "Hamza Abdelkarim"),
            ("30227832-9cfd-4529-92f0-2dbde53a937e", "Victor Ozhianvuna"),
            ("c477096f-c848-4d33-84fc-055bf3063eb8", "Segun Odegbami"),
            ("746a2331-aa04-440e-9fac-59e6f1c98002", "Lamine Camara"),
            ("4f9aa9f1-e043-4eef-8c77-4b135e49d084", "Lamine Camara Duplicate"),
        ]
        with Session(engine) as session:
            for index, (pid, full_name) in enumerate(player_ids):
                session.add(
                    Player(
                        id=pid,
                        source_provider="test",
                        provider_external_id=f"ext-{index}",
                        full_name=full_name,
                        dna_profile={"existing": True},
                        last_synced_at=now,
                    )
                )
                session.add(
                    PlayerSummaryReadModel(
                        player_id=pid,
                        player_name=full_name,
                        last_snapshot_at=now,
                        current_value_credits=100.0,
                        previous_value_credits=100.0,
                        movement_pct=0.0,
                        summary_json={},
                    )
                )
                session.add(PlayerShareMarket(player_id=pid, metadata_json={}))
            session.add(
                LegendaryPlayerProfile(
                    id="c477096f-c848-4d33-84fc-055bf3063eb8",
                    slug="segun-odegbami",
                    full_name="Segun Odegbami",
                    country_code="NGA",
                    primary_position="RW",
                    historical_height_cm=178,
                    gtex_height_cm=178,
                    era="1970s-1980s",
                )
            )
            session.commit()

        config = build_alembic_config(database_url)
        command.stamp(config, "20261115_0250_academy_first_team_minutes")
        command.upgrade(config, "20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration")

        with engine.connect() as conn:
            victor = (
                conn.execute(
                    text(
                        "SELECT governed_gsi, governed_potential_gsi, position, "
                        "secondary_positions_json, dna_profile FROM ingestion_players WHERE id = :pid"
                    ),
                    {"pid": "30227832-9cfd-4529-92f0-2dbde53a937e"},
                )
                .mappings()
                .one()
            )
            assert victor["governed_gsi"] == 74
            assert victor["governed_potential_gsi"] == 86
            assert victor["position"] == "CM"
            assert json.loads(victor["secondary_positions_json"]) == ["AM", "LM", "LW"]
            assert json.loads(victor["dna_profile"])["overall"] == 74

            camara_dup = (
                conn.execute(
                    text("SELECT governed_gsi, governed_potential_gsi FROM ingestion_players WHERE id = :pid"),
                    {"pid": "4f9aa9f1-e043-4eef-8c77-4b135e49d084"},
                )
                .mappings()
                .one()
            )
            assert camara_dup["governed_gsi"] == 83
            assert camara_dup["governed_potential_gsi"] == 90

            odegbami_leg = (
                conn.execute(
                    text(
                        "SELECT primary_position, technical_profile_json FROM legendary_player_profiles WHERE id = :lid"
                    ),
                    {"lid": "c477096f-c848-4d33-84fc-055bf3063eb8"},
                )
                .mappings()
                .one()
            )
            assert odegbami_leg["primary_position"] == "RW"
            assert json.loads(odegbami_leg["technical_profile_json"])["dribbling"] == 89
    finally:
        engine.dispose()
