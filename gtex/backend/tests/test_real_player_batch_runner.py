from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.real_player_batch_runner import RealPlayerBatchRunner
from app.ingestion.real_player_ingestion_service import RealPlayerPricingError
from app.models.base import Base
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _initialize_database(database_url: str):
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings(database_url: str):
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": database_url})


def _write_batch_file(tmp_path: Path, players: list[dict[str, object]]) -> Path:
    batch_path = tmp_path / "first_batch.json"
    batch_path.write_text(
        json.dumps(
            {
                "mode": "curated_seed",
                "ingestion_source_version": "test-first-batch-v1",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": players,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return batch_path


def _sample_players() -> list[dict[str, object]]:
    return [
        {
            "source_name": "curated-feed",
            "source_player_key": "osimhen-001",
            "canonical_name": "Victor Osimhen",
            "known_aliases": ["V. Osimhen"],
            "nationality": "Nigeria",
            "nationality_code": "NG",
            "date_of_birth": "1998-12-29",
            "dominant_foot": "right",
            "primary_position": "Striker",
            "secondary_positions": ["Winger"],
            "current_real_world_club": "Galatasaray",
            "current_real_world_league": "Super Lig",
            "competition_level": "top_flight",
            "appearances": 31,
            "minutes_played": 2410,
            "goals": 19,
            "assists": 4,
            "current_market_reference_value": 60000000,
            "market_reference_currency": "EUR",
        },
        {
            "source_name": "curated-feed",
            "source_player_key": "iwobi-001",
            "canonical_name": "Alex Iwobi",
            "known_aliases": ["Alexander Iwobi"],
            "nationality": "Nigeria",
            "nationality_code": "NG",
            "date_of_birth": "1996-05-03",
            "dominant_foot": "right",
            "primary_position": "Winger",
            "secondary_positions": ["Attacking Midfielder"],
            "current_real_world_club": "Fulham",
            "current_real_world_league": "Premier League",
            "competition_level": "elite",
            "appearances": 29,
            "minutes_played": 2280,
            "goals": 6,
            "assists": 7,
            "current_market_reference_value": 18000000,
            "market_reference_currency": "EUR",
        },
    ]


def _seed_batch_runner_canonical_entities(engine) -> None:
    with _session_factory(engine)() as session:
        nigeria = Country(
            source_provider="seed",
            provider_external_id="NG",
            name="Nigeria",
            alpha2_code="NG",
        )
        turkey = Country(
            source_provider="seed",
            provider_external_id="TR",
            name="Turkey",
            alpha2_code="TR",
        )
        england = Country(
            source_provider="seed",
            provider_external_id="ENG",
            name="England",
            alpha3_code="ENG",
        )
        super_lig = Competition(
            source_provider="seed",
            provider_external_id="tr1",
            country=turkey,
            name="Super Lig",
            slug="super-lig",
            competition_type="league",
            format_type="real_world",
            is_major=True,
            is_tradable=True,
        )
        premier_league = Competition(
            source_provider="seed",
            provider_external_id="eng1",
            country=england,
            name="Premier League",
            slug="premier-league",
            competition_type="league",
            format_type="real_world",
            is_major=True,
            is_tradable=True,
        )
        session.add_all(
            [
                nigeria,
                turkey,
                england,
                super_lig,
                premier_league,
                Club(
                    source_provider="seed",
                    provider_external_id="galatasaray",
                    country=turkey,
                    current_competition=super_lig,
                    name="Galatasaray",
                    slug="galatasaray",
                    short_name="Galatasaray",
                    is_tradable=True,
                ),
                Club(
                    source_provider="seed",
                    provider_external_id="fulham",
                    country=england,
                    current_competition=premier_league,
                    name="Fulham",
                    slug="fulham",
                    short_name="Fulham",
                    is_tradable=True,
                ),
            ]
        )
        session.commit()


def test_batch_runner_dry_run_rolls_back_all_real_player_writes(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "dry_run.db")
    engine = _initialize_database(database_url)
    try:
        _seed_batch_runner_canonical_entities(engine)
        batch_path = _write_batch_file(tmp_path, _sample_players())
        report = RealPlayerBatchRunner(
            database_url=database_url,
            batch_path=batch_path,
            settings=_settings(database_url),
        ).run(mode="dry-run")

        assert report.verdict == "pass"

        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 0
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 0
    finally:
        engine.dispose()


def test_batch_runner_write_commits_and_reruns_without_duplicates(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "write_run.db")
    engine = _initialize_database(database_url)
    try:
        _seed_batch_runner_canonical_entities(engine)
        batch_path = _write_batch_file(tmp_path, _sample_players())
        runner = RealPlayerBatchRunner(
            database_url=database_url,
            batch_path=batch_path,
            settings=_settings(database_url),
        )

        first_report = runner.run(mode="write")
        second_report = runner.run(mode="write")

        assert first_report.verdict == "pass"
        assert second_report.verdict == "pass"

        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 2
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 2
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 2
    finally:
        engine.dispose()


def test_batch_runner_aborts_when_preflight_detects_ambiguous_match(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "ambiguous.db")
    engine = _initialize_database(database_url)
    try:
        with _session_factory(engine)() as session:
            country = Country(
                source_provider="test-source",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            first = Player(
                source_provider="legacy-a",
                provider_external_id="bassey-a",
                full_name="Calvin Bassey",
                country=country,
                position="Centre-Back",
                normalized_position="defender",
                date_of_birth=date(1999, 12, 31),
            )
            second = Player(
                source_provider="legacy-b",
                provider_external_id="bassey-b",
                full_name="Calvin Bassey",
                country=country,
                position="Centre-Back",
                normalized_position="defender",
                date_of_birth=date(1999, 12, 31),
            )
            session.add_all([country, first, second])
            session.commit()

        batch_path = _write_batch_file(
            tmp_path,
            [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "bassey-001",
                    "canonical_name": "Calvin Bassey",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1999-12-31",
                    "primary_position": "Centre-Back",
                    "current_real_world_club": "Fulham",
                    "current_real_world_league": "Premier League",
                    "competition_level": "elite",
                    "appearances": 30,
                    "minutes_played": 2550,
                    "goals": 1,
                    "assists": 2,
                    "clean_sheets": 11,
                    "current_market_reference_value": 22000000,
                    "market_reference_currency": "EUR"
                }
            ],
        )

        report = RealPlayerBatchRunner(
            database_url=database_url,
            batch_path=batch_path,
            settings=_settings(database_url),
        ).run(mode="write")

        assert report.verdict == "fail"
        assert report.ambiguous_matches == 1

        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 0
    finally:
        engine.dispose()


def test_batch_runner_reports_missing_pricing_snapshot_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _database_url(tmp_path / "pricing.db")
    engine = _initialize_database(database_url)
    try:
        batch_path = _write_batch_file(tmp_path, _sample_players())

        class _FailingService:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def ingest(self, _request):
                raise RealPlayerPricingError(
                    "Authoritative value engine produced no snapshots for ['player-123']. No fallback pricing path was used."
                )

        monkeypatch.setattr("app.ingestion.real_player_batch_runner.RealPlayerIngestionService", _FailingService)
        monkeypatch.setattr("backend.app.ingestion.real_player_batch_runner.RealPlayerIngestionService", _FailingService)

        report = RealPlayerBatchRunner(
            database_url=database_url,
            batch_path=batch_path,
            settings=_settings(database_url),
        ).run(mode="dry-run")

        assert report.verdict == "fail"
        assert report.missing_pricing_snapshots == 1
    finally:
        engine.dispose()
