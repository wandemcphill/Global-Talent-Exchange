from __future__ import annotations

import os

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.ingestion.transfermarkt_second_zip import (
    SECOND_ZIP_SOURCE_NAME,
    TransfermarktSecondZipReferenceCatalog,
    map_player_row_to_source_item,
)
from app.models.base import Base
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_reference_mapping import RealPlayerUnresolvedReference
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings():
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "0",
        }
    )


def _reference_catalog() -> TransfermarktSecondZipReferenceCatalog:
    return TransfermarktSecondZipReferenceCatalog.from_rows(
        clubs=[
            {
                "club_id": "100",
                "club_code": "test-fc",
                "name": "Test FC",
                "domestic_competition_id": "NG1",
            }
        ],
        competitions=[
            {
                "competition_id": "NG1",
                "competition_code": "nigeria-premier-league",
                "name": "Nigeria Premier League",
                "country_id": "160",
                "country_name": "Nigeria",
                "type": "league",
            }
        ],
        countries=[
            {
                "country_id": "160",
                "country_name": "Nigeria",
                "country_code": "NGA",
                "confederation": "caf",
            }
        ],
    )


def _player_row(**overrides: object) -> dict[str, object]:
    row = {
        "player_id": "1",
        "player_code": "victor-osimhen",
        "name": "Victor Osimhen",
        "first_name": "Victor",
        "last_name": "Osimhen",
        "date_of_birth": "1998-12-29 00:00:00",
        "country_of_citizenship": "Nigeria",
        "foot": "right",
        "height_in_cm": "186",
        "position": "Attack",
        "sub_position": "Centre-Forward",
        "current_club_id": "100",
        "current_club_name": "",
        "current_club_domestic_competition_id": "NG1",
        "market_value_in_eur": "75000000",
        "highest_market_value_in_eur": "120000000",
        "url": "https://example.test/player/1",
        "last_season": "2025",
    }
    row.update(overrides)
    return row


def _request_from_source_item(source_item) -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": "curated_seed",
            "as_of": "2026-03-23T12:00:00+00:00",
            "ingestion_source_version": "2ndzip-reference-mapping",
            "players": [source_item.raw_payload],
        }
    )


def test_second_zip_ingestion_resolves_country_competition_and_club_from_dataset_keys() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            country = Country(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="160",
                name="Nigeria",
                alpha3_code="NGA",
            )
            competition = Competition(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="NG1",
                country=country,
                name="Nigeria Premier League",
                slug="nigeria-premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            club = Club(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="100",
                country=country,
                current_competition=competition,
                name="Test FC",
                slug="test-fc",
                short_name="Test FC",
                is_tradable=True,
            )
            session.add_all([country, competition, club])
            session.commit()

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        source_item = map_player_row_to_source_item(_player_row(), reference_catalog=_reference_catalog())

        result = service.ingest(_request_from_source_item(source_item))

        assert result.players_processed == 1
        assert result.players_created == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.source_provider == SECOND_ZIP_SOURCE_NAME))
            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_name == SECOND_ZIP_SOURCE_NAME))

            assert player is not None
            assert profile is not None
            assert player.country_id == country.id
            assert player.current_competition_id == competition.id
            assert player.current_club_id == club.id
            assert profile.metadata_json["canonical_mapping"]["country"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["competition"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["club"]["status"] == "resolved"
            assert session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference)) == 0
    finally:
        engine.dispose()


def test_second_zip_ingestion_tracks_unresolved_references_without_blocking_the_row() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        source_item = map_player_row_to_source_item(
            _player_row(
                country_of_citizenship="Atlantis",
                current_club_id="999",
                current_club_name="Mystery FC",
                current_club_domestic_competition_id="ZZ1",
            ),
            reference_catalog=_reference_catalog(),
        )

        result = service.ingest(_request_from_source_item(source_item))

        assert result.players_processed == 1
        assert result.players_created == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.source_provider == SECOND_ZIP_SOURCE_NAME))
            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_name == SECOND_ZIP_SOURCE_NAME))
            unresolved_rows = list(session.scalars(select(RealPlayerUnresolvedReference)))

            assert player is not None
            assert profile is not None
            assert player.current_club_id is None
            assert player.current_competition_id is None
            assert player.country_id is None
            assert profile.metadata_json["canonical_mapping"]["country"]["status"] == "unresolved"
            assert profile.metadata_json["canonical_mapping"]["competition"]["status"] == "unresolved"
            assert profile.metadata_json["canonical_mapping"]["club"]["status"] == "unresolved"
            assert len(unresolved_rows) == 3
            assert {row.entity_type for row in unresolved_rows} == {"country", "competition", "club"}
    finally:
        engine.dispose()


def test_second_zip_ingestion_treats_free_agent_placeholder_as_non_fatal_club_fallback() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            session.add(
                Country(
                    source_provider=SECOND_ZIP_SOURCE_NAME,
                    provider_external_id="160",
                    name="Nigeria",
                    alpha3_code="NGA",
                )
            )
            session.commit()

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        source_item = map_player_row_to_source_item(
            _player_row(
                current_club_id="",
                current_club_name="",
                current_club_domestic_competition_id="",
            ),
            reference_catalog=_reference_catalog(),
        )

        result = service.ingest(_request_from_source_item(source_item))

        assert result.players_processed == 1
        assert result.players_created == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.source_provider == SECOND_ZIP_SOURCE_NAME))
            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_name == SECOND_ZIP_SOURCE_NAME))
            unresolved_clubs = list(
                session.scalars(
                    select(RealPlayerUnresolvedReference).where(
                        RealPlayerUnresolvedReference.entity_type == "club"
                    )
                )
            )

            assert player is not None
            assert profile is not None
            assert player.current_club_id is None
            assert profile.metadata_json["canonical_mapping"]["club"]["status"] == "skipped"
            assert profile.metadata_json["canonical_mapping"]["club"]["reason_code"] == "club_placeholder"
            assert unresolved_clubs == []
    finally:
        engine.dispose()
