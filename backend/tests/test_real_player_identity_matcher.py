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
from app.models.real_player_import_batch import RealPlayerImportBatch, RealPlayerImportRow
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


def test_identity_matcher_resolves_unique_exact_name_real_player_without_dob_or_club_anchor(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="BE",
            name="Belgium",
            alpha2_code="BE",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="de-bruyne-main",
            full_name="Kevin De Bruyne",
            canonical_display_name="Kevin De Bruyne",
            country=country,
            position="Attacking Midfielder",
            normalized_position="midfielder",
            is_real_player=True,
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "de-bruyne-001",
                "canonical_name": "Kevin De Bruyne",
                "nationality": "Belgium",
                "date_of_birth": "1991-06-28",
                "primary_position": "Central Midfielder",
                "current_real_world_club": "Napoli",
                "current_real_world_league": "Serie A",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id
        assert result.confidence_score == pytest.approx(0.71)


def test_identity_matcher_uses_position_tiebreak_for_same_exact_name_candidates(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="NG",
            name="Nigeria",
            alpha2_code="NG",
        )
        centre_back = Player(
            source_provider="legacy-a",
            provider_external_id="torunarigha-centre-back",
            full_name="Jordan Torunarigha",
            canonical_display_name="Jordan Torunarigha",
            country=country,
            position="Centre-Back",
            normalized_position="defender",
            is_real_player=True,
        )
        full_back = Player(
            source_provider="legacy-b",
            provider_external_id="torunarigha-full-back",
            full_name="Jordan Torunarigha",
            canonical_display_name="Jordan Torunarigha",
            country=country,
            position="Full-Back",
            normalized_position="defender",
            is_real_player=True,
        )
        session.add_all([country, centre_back, full_back])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "torunarigha-001",
                "canonical_name": "Jordan Torunarigha",
                "nationality": "Nigeria",
                "date_of_birth": "1997-08-07",
                "primary_position": "Centre-Back",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == centre_back.id
        assert result.confidence_score == pytest.approx(0.74)


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


def test_identity_matcher_matches_accented_name_via_safe_normalization(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="BR",
            name="Brazil",
            alpha2_code="BR",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="vinicius-main",
            full_name="Vinicius Junior",
            country=country,
            position="Winger",
            normalized_position="forward",
            date_of_birth=date(2000, 7, 12),
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "vinicius-001",
                "canonical_name": "Vinícius Júnior",
                "nationality": "Brazil",
                "date_of_birth": "2000-07-12",
                "primary_position": "Winger",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id


def test_identity_matcher_matches_normalized_name_without_club_anchor(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="BR",
            name="Brazil",
            alpha2_code="BR",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="vinicius-main",
            full_name="Vinícius Júnior",
            canonical_display_name="Vinícius Júnior",
            country=country,
            position="Winger",
            normalized_position="forward",
            date_of_birth=date(2000, 7, 12),
            is_real_player=True,
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "vinicius-junior-001",
                "canonical_name": "Vinicius Junior",
                "nationality": "Brazil",
                "birth_year": 2000,
                "primary_position": "Winger",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id


def test_identity_matcher_matches_hyphen_and_spacing_variant_without_alias(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="DZ",
            name="Algeria",
            alpha2_code="DZ",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="compound-main",
            full_name="Ait El Haj Abakar",
            country=country,
            position="Winger",
            normalized_position="forward",
            date_of_birth=date(2001, 1, 1),
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "compound-001",
                "canonical_name": "Ait El-Haj Abakar",
                "nationality": "Algeria",
                "date_of_birth": "2001-01-01",
                "primary_position": "Winger",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id


def test_identity_matcher_uses_short_name_as_alias_match(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="PT",
            name="Portugal",
            alpha2_code="PT",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="ronaldo-main",
            full_name="Cristiano Ronaldo dos Santos Aveiro",
            short_name="Cristiano Ronaldo",
            country=country,
            position="Striker",
            normalized_position="forward",
            date_of_birth=date(1985, 2, 5),
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "ronaldo-001",
                "canonical_name": "Cristiano Ronaldo",
                "nationality": "Portugal",
                "date_of_birth": "1985-02-05",
                "primary_position": "Striker",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id
        assert result.confidence_score >= matcher.confident_match_threshold


def test_identity_matcher_does_not_merge_distinct_players_without_exact_name_or_alias(session_factory) -> None:
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
            provider_external_id="moreno-main",
            full_name="Alex Moreno",
            short_name="Alex Moreno",
            country=country,
            position="Full-Back",
            normalized_position="defender",
            date_of_birth=date(1996, 5, 3),
        )
        session.add_all([country, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "curated-feed",
                "source_player_key": "iwobi-001",
                "canonical_name": "Alex Iwobi",
                "nationality": "Nigeria",
                "date_of_birth": "1996-05-03",
                "primary_position": "Winger",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "create_new"
        assert result.player_id is None


def test_identity_matcher_prefers_resolved_import_row_exact_identity_key(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="BR",
            name="Brazil",
            alpha2_code="BR",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="vinicius-main",
            full_name="Vinicius Junior",
            canonical_display_name="Vinicius Junior",
            country=country,
            position="Winger",
            normalized_position="forward",
            date_of_birth=date(2000, 7, 12),
            is_real_player=True,
        )
        session.add_all([country, player])
        session.flush()
        batch = RealPlayerImportBatch(
            batch_key="historical-batch",
            provider_name="provider-a",
            source_type="real_player_ingestion",
            mode="curated_seed",
            status="completed",
        )
        session.add(batch)
        session.flush()
        session.add(
            RealPlayerImportRow(
                batch_id=batch.id,
                row_number=1,
                source_name="provider-a",
                source_player_key="vinicius-legacy-001",
                canonical_name="Vinicius Junior",
                status="imported",
                match_action="matched_existing",
                import_action="updated",
                identity_confidence_score=0.98,
                gtex_player_id=player.id,
                normalized_full_name="vinicius junior",
                normalized_display_name="vinicius junior",
                name_token_signature="junior|vinicius",
                exact_identity_key="vinicius junior|2000-07-12",
                normalized_nationality="brazil",
                nationality_code="BR",
                primary_position_key="winger",
                secondary_position_keys_json=[],
                position_family="forward",
                review_status="resolved",
            )
        )
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "provider-b",
                "source_player_key": "vinicius-001",
                "canonical_name": "Vinicius Junior",
                "nationality": "Brazil",
                "date_of_birth": "2000-07-12",
                "primary_position": "Winger",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id
        assert result.confidence_score == 0.98


def test_identity_matcher_matches_birthyear_club_key_before_fuzzy_merge(session_factory) -> None:
    matcher = RealPlayerIdentityMatcher()
    with session_factory() as session:
        country = Country(
            source_provider="test-source",
            provider_external_id="CI",
            name="Ivory Coast",
            alpha2_code="CI",
        )
        club = Club(
            source_provider="test-source",
            provider_external_id="al-ahli",
            name="Al Ahli",
            slug="al-ahli",
        )
        player = Player(
            source_provider="legacy-source",
            provider_external_id="kessie-main",
            full_name="Franck Kessie",
            canonical_display_name="Franck Kessie",
            country=country,
            current_club=club,
            position="Central Midfielder",
            normalized_position="midfielder",
            date_of_birth=date(1996, 12, 19),
            is_real_player=True,
        )
        session.add_all([country, club, player])
        session.commit()

        payload = RealPlayerSeedInput.model_validate(
            {
                "source_name": "provider-a",
                "source_player_key": "kessie-001",
                "canonical_name": "Franck Kessie",
                "nationality": "Ivory Coast",
                "birth_year": 1996,
                "primary_position": "CM",
                "current_real_world_club": "Al Ahli",
            }
        )

        result = matcher.match(session, payload)

        assert result.action == "matched_existing"
        assert result.player_id == player.id
        assert result.confidence_score >= 0.88
