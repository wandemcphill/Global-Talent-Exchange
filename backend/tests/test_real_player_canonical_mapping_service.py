from __future__ import annotations

import os

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country
from app.ingestion.real_player_canonical_mapping_service import RealPlayerCanonicalMappingService
from app.models.base import Base
from app.models.real_player_reference_mapping import RealPlayerReferenceMapping, RealPlayerUnresolvedReference


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings(*, auto_create: bool = False):
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "1" if auto_create else "0",
        }
    )


def test_mapping_service_resolves_existing_country_competition_and_club_by_name() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerCanonicalMappingService(settings=_settings())
        with session_factory() as session:
            nigeria = Country(
                source_provider="football_data",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            england = Country(
                source_provider="football_data",
                provider_external_id="ENG",
                name="England",
                alpha3_code="ENG",
                fifa_code="ENG",
            )
            competition = Competition(
                source_provider="football_data",
                provider_external_id="pl",
                country=england,
                name="Premier League",
                slug="premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            club = Club(
                source_provider="football_data",
                provider_external_id="fulham",
                country=england,
                current_competition=competition,
                name="Fulham",
                slug="fulham",
                short_name="Fulham",
                is_tradable=True,
            )
            session.add_all([nigeria, england, competition, club])
            session.commit()

            country_resolution = service.resolve_country(
                session,
                source_name="curated-feed",
                provider_external_id="NG",
                name="Nigeria",
            )
            competition_resolution = service.resolve_competition(
                session,
                source_name="curated-feed",
                name="Premier League",
                country=england,
                country_name="England",
            )
            club_resolution = service.resolve_club(
                session,
                source_name="curated-feed",
                name="Fulham",
                competition=competition,
                competition_name="Premier League",
                country=england,
                country_name="England",
            )

            assert country_resolution.status == "resolved"
            assert country_resolution.canonical_country_id == nigeria.id
            assert competition_resolution.status == "resolved"
            assert competition_resolution.canonical_competition_id == competition.id
            assert club_resolution.status == "resolved"
            assert club_resolution.canonical_club_id == club.id

            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference)) == 0
    finally:
        engine.dispose()


def test_mapping_service_records_unresolved_references_and_increments_occurrence_count() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerCanonicalMappingService(settings=_settings())
        with session_factory() as session:
            first = service.resolve_competition(
                session,
                source_name="curated-feed",
                name="Unmapped League",
                sample_payload={"player": "Victor Osimhen"},
            )
            second = service.resolve_competition(
                session,
                source_name="curated-feed",
                name="Unmapped League",
                sample_payload={"player": "Victor Osimhen"},
            )

            assert first.status == "unresolved"
            assert second.status == "unresolved"

            unresolved = session.scalar(select(RealPlayerUnresolvedReference))
            assert unresolved is not None
            assert unresolved.entity_type == "competition"
            assert unresolved.occurrence_count == 2
            assert unresolved.status == "open"

            assert session.scalar(select(func.count()).select_from(Competition)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 0
    finally:
        engine.dispose()


def test_mapping_service_can_auto_create_missing_entities_when_enabled() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerCanonicalMappingService(settings=_settings(auto_create=True))
        with session_factory() as session:
            turkey = Country(
                source_provider="curated-feed",
                provider_external_id="TR",
                name="Turkey",
                alpha2_code="TR",
            )
            session.add(turkey)
            session.flush()
            competition_resolution = service.resolve_competition(
                session,
                source_name="curated-feed",
                name="Super Lig",
                country=turkey,
                country_name="Turkey",
                auto_create_values={
                    "competition_type": "league",
                    "format_type": "real_world",
                    "is_major": False,
                    "is_tradable": True,
                },
            )
            competition = competition_resolution.entity
            club_resolution = service.resolve_club(
                session,
                source_name="curated-feed",
                name="Galatasaray",
                competition=competition,
                competition_name="Super Lig",
                auto_create_values={
                    "short_name": "Galatasaray",
                    "popularity_score": 80.0,
                    "is_tradable": True,
                },
            )

            assert competition_resolution.status == "auto_created"
            assert club_resolution.status == "auto_created"
            assert session.scalar(select(func.count()).select_from(Competition)) == 1
            assert session.scalar(select(func.count()).select_from(Club)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 2
            assert session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference)) == 0
    finally:
        engine.dispose()


def test_mapping_service_does_not_auto_create_club_without_safe_competition_context() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerCanonicalMappingService(settings=_settings(auto_create=True))
        with session_factory() as session:
            england = Country(
                source_provider="seed",
                provider_external_id="ENG",
                name="England",
                alpha3_code="ENG",
                fifa_code="ENG",
            )
            session.add(england)
            session.commit()

            club_resolution = service.resolve_club(
                session,
                source_name="sportmonks",
                provider_external_id="18645",
                name="England",
                country=england,
                country_name="England",
                competition=None,
                competition_name=None,
            )

            assert club_resolution.status == "unresolved"
            assert session.scalar(select(func.count()).select_from(Club)) == 0
    finally:
        engine.dispose()


def test_mapping_service_reuses_inactive_reference_mapping() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerCanonicalMappingService(settings=_settings())
        with session_factory() as session:
            england = Country(
                source_provider="seed",
                provider_external_id="ENG",
                name="England",
                alpha3_code="ENG",
                fifa_code="ENG",
            )
            session.add(england)
            session.flush()
            session.add(
                RealPlayerReferenceMapping(
                    source_name="sportmonks",
                    entity_type="country",
                    provider_external_id="EN",
                    provider_reference_key="en",
                    provider_label="England",
                    normalized_label="England",
                    canonical_country_id=england.id,
                    mapping_status="resolved",
                    resolution_method="country_name_exact",
                    confidence_score=0.94,
                    is_active=False,
                    metadata_json={},
                )
            )
            session.commit()

            resolution = service.resolve_country(
                session,
                source_name="sportmonks",
                provider_external_id="EN",
                name="England",
            )

            assert resolution.status == "resolved"
            mappings = list(session.scalars(select(RealPlayerReferenceMapping)))
            assert len(mappings) == 1
            assert mappings[0].provider_reference_key == "en"
            assert mappings[0].provider_external_id == "EN"
            assert mappings[0].is_active is True
            assert mappings[0].canonical_country_id == england.id
    finally:
        engine.dispose()
