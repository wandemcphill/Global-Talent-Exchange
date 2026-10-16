from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.football_universe.router import router as football_universe_router
from app.football_universe.service import FootballUniverseService
from app.ingestion.models import Player
from app.match_engine.schemas import MatchClubContextInput, MatchTeamIdentityInput
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models import Base
from app.models.club_profile import ClubProfile
from app.models.football_universe import BroadcastSession, ClubIdentity, FanBase, FanSentiment, MediaEvent
from app.models.notification_record import NotificationRecord
from app.models.player_agency_state import PlayerAgencyState
from app.models.user import User
from backend.tests.match_engine.helpers import build_request, build_team


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            Player.__table__,
            PlayerAgencyState.__table__,
            BroadcastSession.__table__,
            FanBase.__table__,
            ClubIdentity.__table__,
            MediaEvent.__table__,
            NotificationRecord.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def client(session_factory) -> TestClient:
    app = FastAPI()
    app.include_router(football_universe_router)

    def _override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as test_client:
        yield test_client


def _seed_user_and_club(session: Session, *, club_id: str, owner_user_id: str, club_name: str, slug: str) -> None:
    session.add(
        User(
            id=owner_user_id,
            email=f"{owner_user_id}@example.com",
            username=owner_user_id,
            full_name=club_name,
            password_hash="not-used",
        )
    )
    session.add(
        ClubProfile(
            id=club_id,
            owner_user_id=owner_user_id,
            club_name=club_name,
            short_name=club_name[:3].upper(),
            slug=slug,
            primary_color="#112233",
            secondary_color="#f8fafc",
            accent_color="#f59e0b",
            visibility="public",
        )
    )


def _seed_player_state(session: Session, *, player_id: str, club_id: str, player_name: str) -> None:
    session.add(
        Player(
            id=player_id,
            source_provider="test",
            provider_external_id=player_id,
            full_name=player_name,
            position="ST",
            normalized_position="st",
            date_of_birth=date(2001, 1, 1),
            current_club_profile_id=club_id,
            is_real_player=False,
        )
    )
    session.add(
        PlayerAgencyState(
            player_id=player_id,
            current_club_id=club_id,
            morale=50.0,
            happiness=50.0,
            development_satisfaction=50.0,
            club_project_belief=50.0,
        )
    )


def _seed_match_universe(session: Session):
    _seed_user_and_club(session, club_id="home", owner_user_id="owner-home", club_name="North City", slug="north-city")
    _seed_user_and_club(session, club_id="away", owner_user_id="owner-away", club_name="South Town", slug="south-town")
    _seed_player_state(session, player_id="home-player-1", club_id="home", player_name="North City Star")
    _seed_player_state(session, player_id="away-player-1", club_id="away", player_name="South Town Star")
    session.flush()

    home_team = build_team("home", "North City", 82).model_copy(
        update={
            "identity": MatchTeamIdentityInput(
                club_name="North City",
                short_club_code="NCI",
                philosophy="youth_development",
                culture_score=78,
                tactical_consistency=82,
                brand_strength=74,
            ),
            "club_context": MatchClubContextInput(
                expectation_level=79,
                fan_pressure=76,
                media_pressure=71,
                rivalry_intensity=82,
                culture_score=78,
                brand_strength=74,
            ),
        }
    )
    away_team = build_team("away", "South Town", 78).model_copy(
        update={
            "identity": MatchTeamIdentityInput(
                club_name="South Town",
                short_club_code="STW",
                philosophy="counter_attack",
                culture_score=63,
                tactical_consistency=66,
                brand_strength=61,
            ),
            "club_context": MatchClubContextInput(
                expectation_level=61,
                fan_pressure=57,
                media_pressure=54,
                rivalry_intensity=82,
                culture_score=63,
                brand_strength=61,
            ),
        }
    )
    request = build_request(seed=21, match_id="router-match", home_team=home_team, away_team=away_team)
    replay = MatchSimulationService().build_replay_payload(request)
    bundle = FootballUniverseService(session).persist_match_universe(request=request, replay_payload=replay)
    session.commit()
    return bundle


def test_router_returns_broadcast_fan_identity_and_media_views(session_factory, client: TestClient) -> None:
    with session_factory() as session:
        bundle = _seed_match_universe(session)

    broadcast_response = client.get("/broadcast/router-match")
    assert broadcast_response.status_code == 200, broadcast_response.text
    broadcast_payload = broadcast_response.json()
    assert broadcast_payload["match_id"] == "router-match"
    assert broadcast_payload["overlay_state"]["scoreboard"]["home_team_name"] == "North City"
    assert broadcast_payload["overlay_state"]["scoreboard"]["away_team_name"] == "South Town"
    assert len(broadcast_payload["dual_commentary"]) == len(bundle.broadcast_session.dual_commentary)
    assert broadcast_payload["fulltime_wrap"]["player_of_the_match"] is not None

    fan_response = client.get("/fans/home")
    assert fan_response.status_code == 200, fan_response.text
    fan_payload = fan_response.json()
    assert fan_payload["club_id"] == "home"
    assert fan_payload["sentiment"] in {"happy", "neutral", "negative", "very_negative"}

    identity_response = client.get("/club/identity", params={"club_id": "home"})
    assert identity_response.status_code == 200, identity_response.text
    identity_payload = identity_response.json()
    assert identity_payload["club_id"] == "home"
    assert identity_payload["philosophy"] == "youth_development"
    assert identity_payload["average_identity_fit"] > 0

    media_response = client.get("/media", params={"match_id": "router-match", "limit": 10})
    assert media_response.status_code == 200, media_response.text
    media_payload = media_response.json()
    assert len(media_payload) == len(bundle.media_events)
    assert any(item["type"] == "headline" for item in media_payload)
    assert any(item["type"] == "interview" for item in media_payload)


def test_service_persists_universe_effects_and_runs_background_cycles(session_factory) -> None:
    with session_factory() as session:
        bundle = _seed_match_universe(session)

        assert session.scalar(select(BroadcastSession).where(BroadcastSession.match_id == "router-match")) is not None
        assert session.scalar(select(FanBase).where(FanBase.club_id == "home")) is not None
        assert session.scalar(select(ClubIdentity).where(ClubIdentity.club_id == "home")) is not None
        assert len(session.scalars(select(NotificationRecord)).all()) == len(bundle.notifications)

        home_state = session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == "home-player-1"))
        assert home_state is not None
        assert float(home_state.morale) != 50.0
        assert home_state.metadata_json.get("last_pressure_reason") in {"fan_pressure", "media_tone"}

        media_before = len(session.scalars(select(MediaEvent)).all())
        away_fan_base = session.scalar(select(FanBase).where(FanBase.club_id == "away"))
        assert away_fan_base is not None
        away_fan_base.sentiment = FanSentiment.VERY_NEGATIVE
        away_fan_base.loyalty_score = 78.0

        home_identity = session.scalar(select(ClubIdentity).where(ClubIdentity.club_id == "home"))
        assert home_identity is not None
        previous_culture = float(home_identity.culture_score)

        service = FootballUniverseService(session)
        fan_result = service.run_fan_update_cycle()
        media_result = service.run_media_generation_cycle()
        identity_result = service.run_identity_evolution_cycle()
        session.commit()

        updated_away_fan_base = session.scalar(select(FanBase).where(FanBase.club_id == "away"))
        updated_home_identity = session.scalar(select(ClubIdentity).where(ClubIdentity.club_id == "home"))
        media_after = len(session.scalars(select(MediaEvent)).all())

        assert fan_result == {"fan_bases_updated": 2}
        assert media_result["media_events_generated"] >= 1
        assert identity_result == {"club_identities_evolved": 2}
        assert updated_away_fan_base is not None
        assert float(updated_away_fan_base.loyalty_score) < 78.0
        assert "last_fan_update_cycle_at" in dict(updated_away_fan_base.metadata_json or {})
        assert updated_home_identity is not None
        assert float(updated_home_identity.culture_score) > previous_culture
        assert media_after > media_before
