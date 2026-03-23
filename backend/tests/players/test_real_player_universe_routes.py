from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.models.base import Base
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.router import router as players_router


def test_players_router_openapi_includes_real_player_universe_paths() -> None:
    app = FastAPI()
    app.include_router(players_router)

    paths = app.openapi()["paths"]

    assert "/players/real-universe" in paths
    assert "/players/real-universe/search" in paths
    assert "/players/real-universe/{player_id}" in paths


def _build_session() -> tuple[object, Session]:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory()


def _seed_real_player(
    *,
    session: Session,
    player_id: str,
    provider_external_id: str,
    full_name: str,
    nationality: str,
    nationality_code: str,
    date_of_birth: date,
    primary_position: str,
    club_name: str,
    league_name: str,
    competition_level: str,
    current_value_credits: float | None,
    market_reference_value: float,
    source_last_refreshed_at: datetime,
) -> None:
    country = session.scalar(select(Country).where(Country.alpha2_code == nationality_code))
    if country is None:
        country = Country(
            id=f"country-{nationality_code.lower()}",
            source_provider="curated-feed",
            provider_external_id=nationality_code,
            name=nationality,
            alpha2_code=nationality_code,
        )
        session.add(country)
        session.flush()

    player = Player(
        id=player_id,
        source_provider="curated-feed",
        provider_external_id=provider_external_id,
        country_id=country.id,
        full_name=full_name,
        first_name=full_name.split()[0],
        last_name=full_name.split()[-1],
        position=primary_position,
        normalized_position=primary_position.lower(),
        date_of_birth=date_of_birth,
        canonical_display_name=full_name,
        is_real_player=True,
        real_player_tier="featured" if market_reference_value >= 50_000_000 else "core",
        identity_confidence_score=0.97,
        source_last_refreshed_at=source_last_refreshed_at,
        real_world_club_name=club_name,
        real_world_league_name=league_name,
        current_market_reference_value=market_reference_value,
        market_reference_currency="EUR",
        normalization_profile_version="real_player_v1",
    )
    session.add(player)
    session.flush()

    source_link = RealPlayerSourceLink(
        id=f"source-link-{player_id}",
        gtex_player_id=player.id,
        source_name="curated-feed",
        source_player_key=provider_external_id,
        canonical_name=full_name,
        known_aliases_json=[full_name.split()[0]],
        nationality=nationality,
        date_of_birth=date_of_birth,
        birth_year=date_of_birth.year,
        primary_position=primary_position,
        current_real_world_club=club_name,
        identity_confidence_score=0.97,
        is_verified_real_player=True,
        verification_state="verified",
    )
    session.add(source_link)
    session.flush()

    profile = RealPlayerProfile(
        id=f"profile-{player_id}",
        gtex_player_id=player.id,
        source_link_id=source_link.id,
        source_name="curated-feed",
        source_player_key=provider_external_id,
        canonical_name=full_name,
        known_aliases_json=[full_name.split()[0]],
        nationality=nationality,
        date_of_birth=date_of_birth,
        birth_year=date_of_birth.year,
        dominant_foot="right",
        primary_position=primary_position,
        secondary_positions_json=["forward"] if primary_position != "Winger" else ["attacking midfield"],
        current_club_name=club_name,
        current_league_name=league_name,
        competition_level=competition_level,
        appearances=31,
        minutes_played=2410,
        goals=19 if "Victor" in full_name else 8,
        assists=4 if "Victor" in full_name else 12,
        clean_sheets=0,
        current_market_reference_value=market_reference_value,
        market_reference_currency="EUR",
        source_last_refreshed_at=source_last_refreshed_at,
        normalized_signals_json={"competition_level": competition_level, "club_name": club_name},
        ingestion_batch_id="launch-real-batch",
        ingestion_source_version="launch-pack-v1",
        pricing_snapshot_id=f"snapshot-{player_id}" if current_value_credits is not None else None,
        metadata_json={"thread": "G"},
    )
    session.add(profile)

    if current_value_credits is not None:
        session.add(
            PlayerSummaryReadModel(
                player_id=player.id,
                player_name=player.full_name,
                current_club_name=club_name,
                current_competition_name=league_name,
                last_snapshot_id=f"snapshot-{player_id}",
                last_snapshot_at=source_last_refreshed_at,
                current_value_credits=current_value_credits,
                previous_value_credits=max(current_value_credits - 25.0, 0.0),
                movement_pct=6.5,
                average_rating=7.7,
                market_interest_score=88,
                summary_json={
                    "position": primary_position,
                    "market_visibility": {"eligible": True, "status": "visible"},
                    "real_player_profile": {
                        "is_real_player": True,
                        "is_verified_real_player": True,
                        "real_player_tier": player.real_player_tier,
                        "canonical_display_name": full_name,
                        "source_name": "curated-feed",
                        "source_player_key": provider_external_id,
                        "source_last_refreshed_at": source_last_refreshed_at.isoformat(),
                        "real_world_club_name": club_name,
                        "real_world_league_name": league_name,
                        "current_market_reference_value": market_reference_value,
                        "market_reference_currency": "EUR",
                        "pricing_snapshot_id": f"snapshot-{player_id}",
                    },
                    "ingestion_metadata": {
                        "ingestion_batch_id": "launch-real-batch",
                        "ingestion_source_version": "launch-pack-v1",
                    },
                },
            )
        )


def _seed_non_real_player(session: Session) -> None:
    session.add(
        Player(
            id="player-prospect",
            source_provider="legacy-seed",
            provider_external_id="player-prospect",
            full_name="Victor Prospect",
            position="Striker",
            normalized_position="striker",
            date_of_birth=date(2007, 1, 17),
            is_real_player=False,
        )
    )
    session.add(
        PlayerSummaryReadModel(
            player_id="player-prospect",
            player_name="Victor Prospect",
            current_club_name="North London Reds",
            current_competition_name="Launch League Elite",
            last_snapshot_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            current_value_credits=140.0,
            previous_value_credits=130.0,
            movement_pct=7.5,
            average_rating=7.3,
            market_interest_score=75,
            summary_json={"position": "Striker"},
        )
    )


def test_real_player_universe_routes_support_list_search_filters_and_exclude_non_real_players() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-osimhen",
            provider_external_id="osimhen-001",
            full_name="Victor Osimhen",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(1998, 12, 29),
            primary_position="Striker",
            club_name="Istanbul Lions",
            league_name="Launch League Elite",
            competition_level="elite",
            current_value_credits=410.0,
            market_reference_value=60_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        )
        _seed_real_player(
            session=session,
            player_id="player-saka",
            provider_external_id="saka-001",
            full_name="Bukayo Saka",
            nationality="England",
            nationality_code="GB",
            date_of_birth=date(2001, 9, 5),
            primary_position="Winger",
            club_name="North London Reds",
            league_name="Launch League Premier",
            competition_level="elite",
            current_value_credits=390.0,
            market_reference_value=75_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 14, 0, tzinfo=timezone.utc),
        )
        _seed_real_player(
            session=session,
            player_id="player-saliba",
            provider_external_id="saliba-001",
            full_name="William Saliba",
            nationality="France",
            nationality_code="FR",
            date_of_birth=date(2001, 3, 24),
            primary_position="Centre-Back",
            club_name="North London Reds",
            league_name="Launch League Premier",
            competition_level="featured",
            current_value_credits=None,
            market_reference_value=55_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 10, 0, tzinfo=timezone.utc),
        )
        _seed_non_real_player(session)
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            list_response = client.get("/players/real-universe", params={"limit": 10})
            filtered_response = client.get(
                "/players/real-universe",
                params={
                    "nationality": "England",
                    "position": "Winger",
                    "club": "North London",
                    "max_age": 25,
                    "min_value": 300,
                },
            )
            search_response = client.get("/players/real-universe/search", params={"search": "Saliba"})

        assert list_response.status_code == 200
        assert filtered_response.status_code == 200
        assert search_response.status_code == 200

        list_payload = list_response.json()
        filtered_payload = filtered_response.json()
        search_payload = search_response.json()

        listed_ids = {item["player_id"] for item in list_payload["items"]}
        assert list_payload["total"] == 3
        assert listed_ids == {"player-osimhen", "player-saka", "player-saliba"}
        assert "player-prospect" not in listed_ids
        assert all(item["identity_rail"] == "real_player_universe" for item in list_payload["items"])
        assert any(item["current_value_credits"] is None for item in list_payload["items"])

        assert filtered_payload["total"] == 1
        assert filtered_payload["items"][0]["player_id"] == "player-saka"
        assert filtered_payload["items"][0]["nationality"] == "England"

        assert search_payload["total"] == 1
        assert search_payload["items"][0]["player_id"] == "player-saliba"
        assert search_payload["items"][0]["current_market_reference_value"] == 55_000_000
    finally:
        session.close()
        engine.dispose()


def test_real_player_universe_detail_exposes_serialized_profile_and_rejects_non_real_players() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-osimhen",
            provider_external_id="osimhen-001",
            full_name="Victor Osimhen",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(1998, 12, 29),
            primary_position="Striker",
            club_name="Istanbul Lions",
            league_name="Launch League Elite",
            competition_level="elite",
            current_value_credits=410.0,
            market_reference_value=60_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        )
        _seed_non_real_player(session)
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            detail_response = client.get("/players/real-universe/player-osimhen")
            non_real_response = client.get("/players/real-universe/player-prospect")

        assert detail_response.status_code == 200
        assert non_real_response.status_code == 404

        payload = detail_response.json()
        assert payload["identity_rail"] == "real_player_universe"
        assert payload["source_name"] == "curated-feed"
        assert payload["source_player_key"] == "osimhen-001"
        assert payload["is_verified_real_player"] is True
        assert payload["current_club_name"] == "Istanbul Lions"
        assert payload["normalized_signals"]["competition_level"] == "elite"
        assert payload["summary_json"]["market_visibility"]["eligible"] is True
        assert payload["summary_json"]["ingestion_metadata"]["ingestion_batch_id"] == "launch-real-batch"
        assert payload["pricing_snapshot_id"] == "snapshot-player-osimhen"
    finally:
        session.close()
        engine.dispose()


def test_real_player_universe_routes_deduplicate_multi_provider_profiles() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-saka",
            provider_external_id="saka-001",
            full_name="Bukayo Saka",
            nationality="England",
            nationality_code="GB",
            date_of_birth=date(2001, 9, 5),
            primary_position="Winger",
            club_name="North London Reds",
            league_name="Launch League Premier",
            competition_level="elite",
            current_value_credits=390.0,
            market_reference_value=75_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 14, 0, tzinfo=timezone.utc),
        )
        player = session.get(Player, "player-saka")
        assert player is not None

        source_link = RealPlayerSourceLink(
            id="source-link-player-saka-cache",
            gtex_player_id=player.id,
            source_name="footballsquads",
            source_player_key="engprem-2023-2024-arsenal-bukayo-saka-2001-09-05",
            canonical_name="Bukayo Saka",
            known_aliases_json=["Bukayo"],
            nationality="England",
            date_of_birth=date(2001, 9, 5),
            birth_year=2001,
            primary_position="Central Midfielder",
            current_real_world_club="North London Reds",
            identity_confidence_score=0.96,
            is_verified_real_player=True,
            verification_state="verified",
        )
        session.add(source_link)
        session.flush()

        session.add(
            RealPlayerProfile(
                id="profile-player-saka-cache",
                gtex_player_id=player.id,
                source_link_id=source_link.id,
                source_name="footballsquads",
                source_player_key="engprem-2023-2024-arsenal-bukayo-saka-2001-09-05",
                canonical_name="Bukayo Saka",
                known_aliases_json=["Bukayo"],
                nationality="England",
                date_of_birth=date(2001, 9, 5),
                birth_year=2001,
                dominant_foot="left",
                primary_position="Central Midfielder",
                secondary_positions_json=["winger"],
                current_club_name="North London Reds",
                current_league_name="Launch League Premier",
                competition_level="elite",
                appearances=34,
                minutes_played=2900,
                goals=11,
                assists=13,
                clean_sheets=0,
                current_market_reference_value=80_000_000,
                market_reference_currency="EUR",
                source_last_refreshed_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
                normalized_signals_json={"competition_level": "elite", "club_name": "North London Reds"},
                ingestion_batch_id="wave-2-batch",
                ingestion_source_version="wave-2-v1",
                pricing_snapshot_id="snapshot-player-saka",
                metadata_json={"thread": "wave2"},
            )
        )
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            list_response = client.get("/players/real-universe", params={"limit": 10})
            search_response = client.get("/players/real-universe/search", params={"search": "Bukayo Saka"})
            detail_response = client.get("/players/real-universe/player-saka")

        assert list_response.status_code == 200
        assert search_response.status_code == 200
        assert detail_response.status_code == 200

        list_payload = list_response.json()
        search_payload = search_response.json()
        detail_payload = detail_response.json()

        assert list_payload["total"] == 1
        assert search_payload["total"] == 1
        assert search_payload["items"][0]["player_id"] == "player-saka"
        assert search_payload["items"][0]["source_name"] == "footballsquads"
        assert search_payload["items"][0]["position"] == "Central Midfielder"
        assert detail_payload["player_id"] == "player-saka"
        assert detail_payload["source_name"] == "footballsquads"
        assert detail_payload["source_player_key"] == "engprem-2023-2024-arsenal-bukayo-saka-2001-09-05"
        assert detail_payload["primary_position"] == "Central Midfielder"
    finally:
        session.close()
        engine.dispose()
