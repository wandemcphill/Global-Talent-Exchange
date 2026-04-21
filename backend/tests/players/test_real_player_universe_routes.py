from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.router import admin_router as analytics_admin_router
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.auth.service import AuthService
from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.models.base import Base
from app.models.player_match_learning import PlayerFeatureSnapshot, UserPlayerEvent
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.models.user import UserRole
from app.players.read_models import PlayerSummaryReadModel
from app.players.router import router as players_router


def test_players_router_openapi_includes_real_player_universe_paths() -> None:
    app = FastAPI()
    app.include_router(players_router)

    paths = app.openapi()["paths"]

    assert "/players" in paths
    assert "/players/events" in paths
    assert "/players/match" in paths
    assert "/players/me/match-profile" in paths
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


def _create_user(
    session: Session,
    *,
    email: str,
    username: str,
    role: UserRole = UserRole.USER,
):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
        role=role,
    )
    session.commit()
    return user


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
    dominant_foot: str = "right",
    height_cm: int | None = None,
    secondary_positions: list[str] | None = None,
    injury_status: str | None = None,
    photo_url: str | None = None,
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
        height_cm=height_cm,
        preferred_foot=dominant_foot,
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
        dominant_foot=dominant_foot,
        primary_position=primary_position,
        secondary_positions_json=secondary_positions
        or (["forward"] if primary_position != "Winger" else ["attacking midfield"]),
        height_cm=height_cm,
        current_club_name=club_name,
        current_league_name=league_name,
        competition_level=competition_level,
        appearances=31,
        minutes_played=2410,
        goals=19 if "Victor" in full_name else 8,
        assists=4 if "Victor" in full_name else 12,
        clean_sheets=0,
        injury_status=injury_status,
        current_market_reference_value=market_reference_value,
        market_reference_currency="EUR",
        source_last_refreshed_at=source_last_refreshed_at,
        normalized_signals_json={"competition_level": competition_level, "club_name": club_name},
        ingestion_batch_id="launch-real-batch",
        ingestion_source_version="launch-pack-v1",
        pricing_snapshot_id=f"snapshot-{player_id}" if current_value_credits is not None else None,
        metadata_json={
            "thread": "G",
            **({"photo_url": photo_url} if photo_url is not None else {}),
        },
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


def test_players_match_route_returns_v2_ranked_matches_with_breakdowns() -> None:
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
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=410.0,
            market_reference_value=60_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=186,
        )
        _seed_real_player(
            session=session,
            player_id="player-gyokeres",
            provider_external_id="gyokeres-001",
            full_name="Viktor Gyokeres",
            nationality="Sweden",
            nationality_code="SE",
            date_of_birth=date(1998, 6, 4),
            primary_position="Striker",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=360.0,
            market_reference_value=55_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 13, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=187,
        )
        _seed_real_player(
            session=session,
            player_id="player-signed",
            provider_external_id="signed-001",
            full_name="Tolu Signed",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(2000, 5, 16),
            primary_position="Striker",
            club_name="Lagos Stars",
            league_name="Launch League",
            competition_level="elite",
            current_value_credits=250.0,
            market_reference_value=7_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 10, 0, tzinfo=timezone.utc),
            dominant_foot="left",
            height_cm=178,
        )
        _seed_real_player(
            session=session,
            player_id="player-midfielder",
            provider_external_id="midfielder-001",
            full_name="Mina Midfield",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(2001, 1, 9),
            primary_position="Midfielder",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=240.0,
            market_reference_value=5_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 9, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=182,
        )
        _seed_non_real_player(session)
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            response = client.post(
                "/players/match",
                json={
                    "brief": {
                        "positions": ["ST"],
                        "age": {"min": 24, "max": 29, "target": 26},
                        "height_cm": {"min": 183, "max": 190, "target": 186},
                        "countries": ["NG"],
                        "preferred_foot": ["right"],
                        "availability": ["free_agent"],
                    },
                    "pagination": {"limit": 3},
                    "constraints": {
                        "strict_position": True,
                        "exclude_injured": False,
                        "min_match_score": 0.0,
                    },
                },
            )

        assert response.status_code == 200
        payload = response.json()

        assert [entry["player_id"] for entry in payload["matches"]] == [
            "player-osimhen",
            "player-gyokeres",
            "player-signed",
        ]
        assert payload["matches"][0]["score"] == 0.96
        assert payload["matches"][0]["score_breakdown"] == {
            "position": 1.0,
            "age": 0.8,
            "country": 1.0,
            "height": 1.0,
            "foot": 1.0,
            "availability": 1.0,
        }
        assert payload["matches"][0]["reasons"][0] == {
            "type": "position",
            "label": "Primary position match",
            "impact": "+0.40",
        }
        assert payload["matches"][0]["flags"] == {
            "is_free_agent": True,
            "is_exact_position": True,
            "is_high_potential": False,
        }
        assert payload["matches"][0]["player"] == {
            "name": "Victor Osimhen",
            "age": 27,
            "position": "ST",
            "country": "NG",
            "height_cm": 186,
            "preferred_foot": "right",
            "club": None,
        }
        assert payload["matches"][1]["score"] == 0.8457
        assert payload["matches"][1]["flags"]["is_free_agent"] is True
        assert payload["matches"][2]["score"] == 0.66
        assert payload["matches"][2]["player"]["club"] == "Lagos Stars"
        assert payload["meta"] == {
            "total_candidates": 4,
            "scored_candidates": 4,
            "returned": 3,
            "next_cursor": payload["meta"]["next_cursor"],
            "has_more": True,
        }
        assert payload["meta"]["next_cursor"] is not None
        assert payload["summary"] == {
            "average_score": 0.7764,
            "top_score": 0.96,
            "distribution": {
                "90_100": 1,
                "80_89": 1,
                "70_79": 0,
                "below_70": 2,
            },
        }
        assert payload["applied_config"]["weights"] == {
            "position": 0.4,
            "age": 0.2,
            "country": 0.1,
            "height": 0.1,
            "foot": 0.1,
            "availability": 0.1,
        }
        matched_ids = {entry["player_id"] for entry in payload["matches"]}
        assert "player-midfielder" not in matched_ids
        assert "player-prospect" not in matched_ids
    finally:
        session.close()
        engine.dispose()


def test_players_match_route_returns_empty_matches_when_prefilter_finds_nothing() -> None:
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
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=410.0,
            market_reference_value=60_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            photo_url="https://cdn.sportmonks.com/images/soccer/players/1/osimhen-001.png",
        )
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            response = client.post(
                "/players/match",
                json={
                    "brief": {
                        "positions": ["GK"],
                        "countries": ["ES"],
                    },
                    "pagination": {"limit": 5},
                    "constraints": {
                        "strict_position": True,
                        "min_match_score": 0.0,
                    },
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "matches": [],
            "meta": {
                "total_candidates": 0,
                "scored_candidates": 0,
                "returned": 0,
                "next_cursor": None,
                "has_more": False,
            },
            "summary": {
                "average_score": 0.0,
                "top_score": 0.0,
                "distribution": {
                    "90_100": 0,
                    "80_89": 0,
                    "70_79": 0,
                    "below_70": 0,
                },
            },
            "applied_config": {
                "weights": {
                    "position": 0.4,
                    "age": 0.2,
                    "country": 0.1,
                    "height": 0.1,
                    "foot": 0.1,
                    "availability": 0.1,
                },
                "constraints": {
                    "strict_position": True,
                    "exclude_injured": False,
                    "min_match_score": 0.0,
                },
            },
            "debug": None,
        }
    finally:
        session.close()
        engine.dispose()


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
            photo_url="https://cdn.sportmonks.com/images/soccer/players/1/osimhen-001.png",
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
            unified_response = client.get("/players", params={"limit": 2})
            list_response = client.get("/players/real-universe", params={"limit": 10})
            filtered_response = client.get(
                "/players",
                params={
                    "country": "England",
                    "position": "Winger",
                    "max_age": 25,
                    "min_value": 300,
                },
            )
            search_response = client.get("/players", params={"search": "Saliba"})

        assert unified_response.status_code == 200
        assert list_response.status_code == 200
        assert filtered_response.status_code == 200
        assert search_response.status_code == 200

        unified_payload = unified_response.json()
        list_payload = list_response.json()
        filtered_payload = filtered_response.json()
        search_payload = search_response.json()

        listed_ids = {item["player_id"] for item in list_payload["items"]}
        assert list_payload["total"] == 3
        assert listed_ids == {"player-osimhen", "player-saka", "player-saliba"}
        assert "player-prospect" not in listed_ids
        assert all(item["identity_rail"] == "real_player_universe" for item in list_payload["items"])
        assert any(item["current_value_credits"] is None for item in list_payload["items"])

        assert unified_payload["total"] == 3
        assert len(unified_payload["players"]) == 2
        assert unified_payload["has_more"] is True
        assert unified_payload["next_cursor"] is not None

        with TestClient(app) as client:
            second_page_response = client.get(
                "/players",
                params={
                    "limit": 2,
                    "cursor": unified_payload["next_cursor"],
                },
            )

        assert second_page_response.status_code == 200
        second_page_payload = second_page_response.json()

        assert filtered_payload["total"] == 1
        assert filtered_payload["players"][0]["player_id"] == "player-saka"
        assert filtered_payload["players"][0]["nationality"] == "England"

        assert search_payload["total"] == 1
        assert search_payload["players"][0]["player_id"] == "player-saliba"
        assert search_payload["players"][0]["current_market_reference_value"] == 55_000_000

        assert second_page_payload["has_more"] is False
        assert second_page_payload["next_cursor"] is None
        first_page_ids = {item["player_id"] for item in unified_payload["players"]}
        second_page_ids = {item["player_id"] for item in second_page_payload["players"]}
        assert first_page_ids.isdisjoint(second_page_ids)
        assert first_page_ids | second_page_ids == {"player-osimhen", "player-saka", "player-saliba"}
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
            photo_url="https://cdn.sportmonks.com/images/soccer/players/1/osimhen-001.png",
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
        assert payload["image_url"] == "https://cdn.sportmonks.com/images/soccer/players/1/osimhen-001.png"
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
            list_response = client.get("/players", params={"limit": 10})
            search_response = client.get("/players", params={"search": "Bukayo Saka"})
            detail_response = client.get("/players/real-universe/player-saka")

        assert list_response.status_code == 200
        assert search_response.status_code == 200
        assert detail_response.status_code == 200

        list_payload = list_response.json()
        search_payload = search_response.json()
        detail_payload = detail_response.json()

        assert list_payload["total"] == 1
        assert search_payload["total"] == 1
        assert search_payload["players"][0]["player_id"] == "player-saka"
        assert search_payload["players"][0]["source_name"] == "footballsquads"
        assert search_payload["players"][0]["position"] == "Central Midfielder"
        assert detail_payload["player_id"] == "player-saka"
        assert detail_payload["source_name"] == "footballsquads"
        assert detail_payload["source_player_key"] == "engprem-2023-2024-arsenal-bukayo-saka-2001-09-05"
        assert detail_payload["primary_position"] == "Central Midfielder"
    finally:
        session.close()
        engine.dispose()


def test_unified_players_route_supports_availability_filter_and_rejects_stale_cursor() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-free-agent",
            provider_external_id="free-agent-001",
            full_name="Ayo Freeagent",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(2000, 6, 11),
            primary_position="Striker",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=210.0,
            market_reference_value=5_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 9, 0, tzinfo=timezone.utc),
        )
        _seed_real_player(
            session=session,
            player_id="player-signed",
            provider_external_id="signed-001",
            full_name="Mina Signed",
            nationality="Ghana",
            nationality_code="GH",
            date_of_birth=date(1999, 8, 4),
            primary_position="Midfielder",
            club_name="Accra Stars",
            league_name="Launch League",
            competition_level="elite",
            current_value_credits=280.0,
            market_reference_value=7_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 11, 0, tzinfo=timezone.utc),
        )
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            first_response = client.get("/players", params={"limit": 1})
            availability_response = client.get(
                "/players",
                params={"availability": "free_agent"},
            )
            stale_cursor_response = client.get(
                "/players",
                params={
                    "limit": 1,
                    "country": "Nigeria",
                    "cursor": first_response.json()["next_cursor"],
                },
            )

        assert first_response.status_code == 200
        assert availability_response.status_code == 200
        assert stale_cursor_response.status_code == 400

        availability_payload = availability_response.json()
        assert availability_payload["total"] == 1
        assert availability_payload["players"][0]["player_id"] == "player-free-agent"
        assert stale_cursor_response.json()["detail"] == "cursor does not match the current player query"
    finally:
        session.close()
        engine.dispose()


def test_player_match_event_route_persists_learning_signal_and_profile() -> None:
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
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=410.0,
            market_reference_value=60_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=186,
        )
        current_user = _create_user(
            session,
            email="learning-user@example.com",
            username="learninguser",
        )

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override
        app.dependency_overrides[get_current_user] = lambda: current_user
        app.dependency_overrides[get_optional_current_user] = lambda: current_user

        with TestClient(app) as client:
            event_response = client.post(
                "/players/events",
                json={
                    "player_id": "player-osimhen",
                    "event": "player_contacted",
                    "filters": {"position": "Striker", "country": "Nigeria"},
                    "match_score": 1.0,
                    "reasons": ["Perfect position match"],
                },
            )
            profile_response = client.get("/players/me/match-profile")

        assert event_response.status_code == 201
        assert profile_response.status_code == 200

        stored_event = session.scalar(select(UserPlayerEvent).where(UserPlayerEvent.player_id == "player-osimhen"))
        stored_snapshot = session.get(PlayerFeatureSnapshot, "player-osimhen")
        assert stored_event is not None
        assert stored_snapshot is not None
        assert stored_event.event_type == "player_contacted"
        assert stored_event.weight == 8
        assert stored_event.filters_json["country"] == "Nigeria"
        assert stored_event.match_score == 1.0
        assert stored_snapshot.position == "striker"
        assert stored_snapshot.country == "nigeria"
        assert stored_snapshot.is_free_agent is True

        profile_payload = profile_response.json()
        assert profile_payload["total_signal"] == 8.0
        assert profile_payload["event_count"] == 1
        assert profile_payload["position_preferences"]["striker"] == 8.0
        assert profile_payload["country_preferences"]["nigeria"] == 8.0
        assert any(weight["factor"] == "history_position_bonus" for weight in profile_payload["weights"])
    finally:
        session.close()
        engine.dispose()


def test_players_match_route_fills_defaults_and_uses_score_cursor_pagination() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-first-striker",
            provider_external_id="first-striker-001",
            full_name="Ayo First",
            nationality="Nigeria",
            nationality_code="NG",
            date_of_birth=date(2001, 7, 13),
            primary_position="Striker",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=320.0,
            market_reference_value=18_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=184,
        )
        _seed_real_player(
            session=session,
            player_id="player-second-striker",
            provider_external_id="second-striker-001",
            full_name="Beto Second",
            nationality="Ghana",
            nationality_code="GH",
            date_of_birth=date(2002, 9, 4),
            primary_position="Striker",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=280.0,
            market_reference_value=16_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 11, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=181,
        )
        _seed_real_player(
            session=session,
            player_id="player-injured-striker",
            provider_external_id="injured-striker-001",
            full_name="Injured Third",
            nationality="France",
            nationality_code="FR",
            date_of_birth=date(2000, 1, 4),
            primary_position="Striker",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=400.0,
            market_reference_value=20_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 13, 0, tzinfo=timezone.utc),
            dominant_foot="left",
            height_cm=187,
            injury_status="hamstring",
        )

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            first_page = client.post(
                "/players/match",
                json={
                    "brief": {
                        "positions": ["ST"],
                        "age": {"max": 29},
                        "availability": ["free_agent"],
                    },
                    "pagination": {"limit": 1},
                    "constraints": {
                        "strict_position": True,
                        "exclude_injured": True,
                        "min_match_score": 0.0,
                    },
                },
            )
            second_page = client.post(
                "/players/match",
                json={
                    "brief": {
                        "positions": ["ST"],
                        "age": {"max": 29},
                        "availability": ["free_agent"],
                    },
                    "pagination": {
                        "limit": 1,
                        "cursor": first_page.json()["meta"]["next_cursor"],
                    },
                    "constraints": {
                        "strict_position": True,
                        "exclude_injured": True,
                        "min_match_score": 0.0,
                    },
                },
            )

        assert first_page.status_code == 200
        assert second_page.status_code == 200

        first_payload = first_page.json()
        second_payload = second_page.json()

        assert first_payload["meta"]["total_candidates"] == 2
        assert first_payload["meta"]["scored_candidates"] == 2
        assert first_payload["meta"]["returned"] == 1
        assert first_payload["meta"]["has_more"] is True
        assert first_payload["meta"]["next_cursor"] is not None
        assert first_payload["matches"][0]["player_id"] == "player-first-striker"
        assert first_payload["matches"][0]["score_breakdown"] == {
            "position": 1.0,
            "age": 1.0,
            "country": 1.0,
            "height": 1.0,
            "foot": 1.0,
            "availability": 1.0,
        }
        assert second_payload["meta"]["total_candidates"] == 2
        assert second_payload["meta"]["returned"] == 1
        assert second_payload["meta"]["has_more"] is False
        assert second_payload["meta"]["next_cursor"] is None
        assert second_payload["matches"][0]["player_id"] == "player-second-striker"
        assert second_payload["summary"]["distribution"] == {
            "90_100": 2,
            "80_89": 0,
            "70_79": 0,
            "below_70": 0,
        }
    finally:
        session.close()
        engine.dispose()


def test_admin_player_matching_summary_and_weight_refresh() -> None:
    engine, session = _build_session()
    try:
        _seed_real_player(
            session=session,
            player_id="player-summary-winger",
            provider_external_id="summary-winger-001",
            full_name="Summary Winger",
            nationality="England",
            nationality_code="GB",
            date_of_birth=date(2001, 7, 13),
            primary_position="Winger",
            club_name="Free Agent",
            league_name="Independent",
            competition_level="open_market",
            current_value_credits=150.0,
            market_reference_value=18_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
            dominant_foot="left",
            height_cm=175,
        )
        _seed_real_player(
            session=session,
            player_id="player-summary-midfielder",
            provider_external_id="summary-midfielder-001",
            full_name="Summary Midfielder",
            nationality="Brazil",
            nationality_code="BR",
            date_of_birth=date(2000, 4, 2),
            primary_position="Midfielder",
            club_name="Rio Stars",
            league_name="Launch League",
            competition_level="elite",
            current_value_credits=210.0,
            market_reference_value=22_000_000,
            source_last_refreshed_at=datetime(2026, 3, 22, 11, 0, tzinfo=timezone.utc),
            dominant_foot="right",
            height_cm=181,
        )
        normal_user = _create_user(
            session,
            email="analytics-user@example.com",
            username="analyticsuser",
        )
        admin_user = _create_user(
            session,
            email="analytics-admin@example.com",
            username="analyticsadmin",
            role=UserRole.ADMIN,
        )

        session.add_all(
            [
                PlayerFeatureSnapshot(
                    player_id="player-summary-winger",
                    position="winger",
                    country="england",
                    age=24,
                    height_cm=175,
                    dominant_foot="left",
                    is_free_agent=True,
                    current_club_name="Free Agent",
                    secondary_positions_json=["attacking midfield"],
                ),
                PlayerFeatureSnapshot(
                    player_id="player-summary-midfielder",
                    position="midfielder",
                    country="brazil",
                    age=25,
                    height_cm=181,
                    dominant_foot="right",
                    is_free_agent=False,
                    current_club_name="Rio Stars",
                    secondary_positions_json=["winger"],
                ),
            ]
        )
        session.add_all(
            [
                *[
                    UserPlayerEvent(
                        user_id=normal_user.id,
                        player_id="player-summary-winger" if index % 2 == 0 else "player-summary-midfielder",
                        event_type="player_viewed",
                        weight=1,
                        match_score=0.5,
                    )
                    for index in range(6)
                ],
                *[
                    UserPlayerEvent(
                        user_id=normal_user.id,
                        player_id="player-summary-winger",
                        event_type="player_contacted",
                        weight=8,
                        match_score=0.72,
                    )
                    for _ in range(6)
                ],
            ]
        )
        session.commit()

        app = FastAPI()
        app.include_router(analytics_admin_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override
        app.dependency_overrides[get_current_admin] = lambda: admin_user

        with TestClient(app) as client:
            summary_response = client.get("/api/admin/analytics/player-matching")
            refresh_response = client.post("/api/admin/analytics/player-matching/recompute-weights")

        assert summary_response.status_code == 200
        assert refresh_response.status_code == 200

        summary_payload = summary_response.json()
        refresh_payload = refresh_response.json()

        assert summary_payload["funnel"] == [
            {"event": "player_viewed", "count": 6},
            {"event": "player_shortlisted", "count": 0},
            {"event": "player_scouted", "count": 0},
            {"event": "player_contacted", "count": 6},
        ]
        assert summary_payload["top_positions"][0] == {"label": "winger", "count": 6}
        assert summary_payload["top_countries"][0] == {"label": "england", "count": 6}
        assert any(weight["factor"] == "history_position_bonus" for weight in summary_payload["weights"])

        refreshed_weights = {item["factor"]: item["weight"] for item in refresh_payload["weights"]}
        assert refreshed_weights["history_position_bonus"] > 0.1
        assert refreshed_weights["history_country_bonus"] > 0.05
    finally:
        session.close()
        engine.dispose()
