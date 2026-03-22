from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Club, Country, Player
from app.ingestion.real_player_identity_matcher import AmbiguousRealPlayerMatchError, RealPlayerIdentityMatcher
from app.models.base import Base
from app.models.real_player_source_link import RealPlayerSourceLink
from app.schemas.real_player_ingestion import RealPlayerSeedInput


@pytest.fixture()
def session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def test_identity_matcher_prefers_existing_source_link(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="NG",
            name="Nigeria",
            alpha2_code="NG",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="legacy-osimhen",
            full_name="Victor Osimhen",
            country=country,
            position="Striker",
            normalized_position="forward",
            date_of_birth=date(1998, 12, 29),
            is_real_player=True,
        )
        session.add_all([country, player])
        session.flush()
        session.add(
            RealPlayerSourceLink(
                gtex_player_id=player.id,
                source_name="curated-feed",
                source_player_key="osimhen-001",
                canonical_name="Victor Osimhen",
                nationality="Nigeria",
                date_of_birth=date(1998, 12, 29),
                birth_year=1998,
                primary_position="Striker",
                identity_confidence_score=0.97,
            )
        )
        session.commit()

        result = matcher.match(
            session,
            RealPlayerSeedInput.model_validate(
                {
                    "source_name": "curated-feed",
                    "source_player_key": "osimhen-001",
                    "canonical_name": "Victor Osimhen",
                    "nationality": "Nigeria",
                    "date_of_birth": "1998-12-29",
                    "primary_position": "Striker",
                }
            ),
        )

        assert result.action == "source_link"
        assert result.player_id == player.id
        assert result.confidence_score >= 0.99


def test_identity_matcher_is_deterministic_for_high_confidence_existing_match(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="NG",
            name="Nigeria",
            alpha2_code="NG",
        )
        matching_club = Club(
            source_provider="test-source",
            provider_external_id="club-fulham",
            name="Fulham",
            slug="fulham",
        )
        off_club = Club(
            source_provider="test-source",
            provider_external_id="club-random",
            name="Random Club",
            slug="random-club",
        )
        target_player = Player(
            source_provider="legacy-source",
            provider_external_id="iwobi-main",
            full_name="Alex Iwobi",
            country=country,
            current_club=matching_club,
            position="Winger",
            normalized_position="forward",
            date_of_birth=date(1996, 5, 3),
        )
        distractor = Player(
            source_provider="legacy-source",
            provider_external_id="iwobi-distractor",
            full_name="Alex Iwobi",
            country=country,
            current_club=off_club,
            position="Central Midfielder",
            normalized_position="midfielder",
            date_of_birth=date(1997, 5, 3),
        )
        session.add_all([country, matching_club, off_club, target_player, distractor])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "iwobi-001",
                "canonical_name": "Alex Iwobi",
                "nationality": "Nigeria",
                "date_of_birth": "1996-05-03",
                "primary_position": "Winger",
                "current_real_world_club": "Fulham",
            }
        )

        first = matcher.match(session, payload)
        second = matcher.match(session, payload)

        assert first.action == "matched_existing"
        assert first.player_id == target_player.id
        assert second.player_id == target_player.id
        assert first.confidence_score == second.confidence_score


def test_identity_matcher_raises_for_ambiguous_candidates(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
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

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "bassey-001",
                "canonical_name": "Calvin Bassey",
                "nationality": "Nigeria",
                "date_of_birth": "1999-12-31",
                "primary_position": "Centre-Back",
            }
        )

        with pytest.raises(AmbiguousRealPlayerMatchError):
            matcher.match(session, payload)
