from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import reset_settings_cache
from app.auth.dependencies import get_current_match_user
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import LiveMatchHub
from app.live_matches.unity_access import issue_unity_live_access_token, issue_unity_live_refresh_token
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.broadcast_rights import BroadcastAccessGrant, BroadcastRight, ViewSession
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.spectator_session import SpectatorSession
from app.models.user import User, UserRole
from backend.tests.match_engine.helpers import build_request
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET
from backend.tests.support.economic_policy import seed_economic_policy
from app.reward_engine.service import RewardEngineService


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()
    app = FastAPI()
    app.include_router(live_matches_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    return app, session_factory


def _insert_match(session_factory: sessionmaker[Session], replay_payload, *, simulation_request=None) -> None:
    with session_factory() as session:
        home_id = replay_payload.summary.home_stats.team_id
        away_id = replay_payload.summary.away_stats.team_id
        metadata = {"replay_payload": replay_payload.model_dump(mode="json")}
        if simulation_request is not None:
            metadata["simulation_request"] = (
                simulation_request
                if isinstance(simulation_request, dict)
                else simulation_request.model_dump(mode="json")
            )
        session.add(
            CompetitionMatch(
                id=replay_payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=home_id,
                away_club_id=away_id,
                status="completed",
                metadata_json=metadata,
            )
        )
        if not session.get(User, "home-manager-user"):
            session.add(
                User(
                    id="home-manager-user",
                    email="home-mgr@example.com",
                    username="homemgr",
                    password_hash="hashed-password",  # pragma: allowlist secret
                    is_active=True,
                )
            )
        if not session.get(User, "away-manager-user"):
            session.add(
                User(
                    id="away-manager-user",
                    email="away-mgr@example.com",
                    username="awaymgr",
                    password_hash="hashed-password",  # pragma: allowlist secret
                    is_active=True,
                )
            )
        if not session.get(ClubProfile, home_id):
            session.add(
                ClubProfile(
                    id=home_id,
                    club_name=replay_payload.summary.home_stats.team_name,
                    slug=f"club-home-{home_id}",
                    owner_user_id="home-manager-user",
                    primary_color="#00E87A",
                    secondary_color="#0F172A",
                    accent_color="#FFFFFF",
                )
            )
        if not session.get(ClubProfile, away_id):
            session.add(
                ClubProfile(
                    id=away_id,
                    club_name=replay_payload.summary.away_stats.team_name,
                    slug=f"club-away-{away_id}",
                    owner_user_id="away-manager-user",
                    primary_color="#FFB800",
                    secondary_color="#0F172A",
                    accent_color="#FFFFFF",
                )
            )
        session.commit()


def _issue_live_access_token(session_factory: sessionmaker[Session], match_id: str) -> str:
    with session_factory() as session:
        user = User(
            email="viewer@example.com",
            username="viewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        spectator_session = SpectatorSession(match_id=match_id, user_id=user.id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        token, _ = issue_unity_live_access_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=user.id,
        )
        return token


def _issue_live_refresh_token(session_factory: sessionmaker[Session], match_id: str) -> tuple[str, str]:
    with session_factory() as session:
        user = User(
            email="refresh-viewer@example.com",
            username="refreshviewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        spectator_session = SpectatorSession(match_id=match_id, user_id=user.id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        token, _ = issue_unity_live_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=user.id,
        )
        return token, spectator_session.id


def test_match_live_route_requires_unity_access_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/match/{replay_payload.match_id}/live")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unity live access token is required."


def test_active_live_matches_route_lists_current_live_matches() -> None:
    app, _session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    hub = LiveMatchHub(step_interval_seconds=0.01)
    app.state.live_match_hub = hub
    hub.start_stream(replay_payload.match_id, replay_payload)
    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.get("/api/matches/live/active")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["match_id"] == replay_payload.match_id
    assert body["items"][0]["home_team_name"] == replay_payload.summary.home_stats.team_name
    assert body["items"][0]["away_team_name"] == replay_payload.summary.away_stats.team_name


def test_match_live_route_returns_frames_from_db_when_live_cache_is_empty() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    access_token = _issue_live_access_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.get(
            f"/match/{replay_payload.match_id}/live",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["matchId"] == replay_payload.match_id
    assert body["status"] == "completed"
    assert body["isLive"] is False
    assert body["frames"]
    assert body["timelineEvents"]
    assert body["payloadMode"] == "live_compact"
    assert len(body["frames"]) == 1
    assert len(body["timelineEvents"]) <= 24
    assert len(body["viewer"]["frames"]) == 1
    assert body["viewer"]["match_id"] == replay_payload.match_id
    assert body["score"]["home"] == replay_payload.summary.home_score
    assert body["score"]["away"] == replay_payload.summary.away_score


def test_match_live_route_can_opt_into_full_timeline_payload() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    access_token = _issue_live_access_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.get(
            f"/match/{replay_payload.match_id}/live",
            params={"include_full_timeline": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["payloadMode"] == "full"
    assert len(body["frames"]) > 1
    assert len(body["viewer"]["frames"]) == len(body["frames"])


def test_unity_live_refresh_route_issues_new_live_credentials() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    refresh_token, spectator_session_id = _issue_live_refresh_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/unity-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == replay_payload.match_id
    assert body["spectator_session_id"] == spectator_session_id
    assert body["access_token"]
    assert body["refresh_token"]


def test_unity_live_refresh_route_rejects_invalid_refresh_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/unity-access/refresh",
            json={"refresh_token": "not-a-real-unity-refresh-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"]


def test_unity_live_access_requires_session_backed_rights_for_non_generated_matches() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    reset_settings_cache()

    app = FastAPI()
    app.include_router(live_matches_router)
    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.post("/match/restricted-match-001/unity-access")

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Unity live access requires session-backed rights validation for non-generated matches."
    )


def test_unity_live_refresh_route_revalidates_restricted_match_access() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()

    app = FastAPI()
    app.include_router(live_matches_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CompetitionMatch.__table__,
            User.__table__,
            SpectatorSession.__table__,
            BroadcastAccessGrant.__table__,
            BroadcastRight.__table__,
            ViewSession.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    match_id = "restricted-match-002"
    today = date.today()

    with session_factory() as session:
        viewer = User(
            email="restricted-viewer@example.com",
            username="restrictedviewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(viewer)
        session.commit()
        session.refresh(viewer)

        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-locked-001",
                round_id="round-locked-001",
                round_number=1,
                home_club_id="home-club-001",
                away_club_id="away-club-001",
                match_date=today,
                status="live",
                metadata_json={},
            )
        )
        session.add(
            BroadcastRight(
                competition_id="competition-locked-001",
                owner_id="rights-owner-001",
                acquisition_price="10.0000",
                revenue_share_percentage="50.00",
                exclusivity=True,
                start_date=today,
                end_date=today,
                metadata_json={"viewing_fee_coin": "5.0000"},
            )
        )
        spectator_session = SpectatorSession(match_id=match_id, user_id=viewer.id, joined_at=datetime.now(UTC))
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        refresh_token, _ = issue_unity_live_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=viewer.id,
        )

    with TestClient(app) as client:
        response = client.post(
            f"/match/{match_id}/unity-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["message"] == "Broadcast rights access is restricted for this match."
    assert body["detail"]["access"]["has_access"] is False
    assert body["detail"]["access"]["requires_payment"] is True


def test_update_and_read_match_tactics_auth_and_ownership() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=42))
    _insert_match(session_factory, replay_payload)
    match_id = replay_payload.match_id
    hub = LiveMatchHub(session_factory=session_factory)
    app.state.live_match_hub = hub

    with TestClient(app) as client:
        # 1. Anonymous request without auth token is rejected with 401
        anon_res = client.post(
            f"/api/matches/{match_id}/tactics",
            json={"side": "home", "formation": "4-2-3-1"},
        )
        assert anon_res.status_code == 401, anon_res.text

        # 2. Both opponent and club owner are rejected with 403; First-Team Manager holds exclusive control
        app.dependency_overrides[get_current_match_user] = lambda: User(
            id="away-manager-user",
            email="away@example.com",
            username="awaymgr",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        opp_res = client.post(
            f"/api/matches/{match_id}/tactics",
            json={"side": "home", "formation": "4-2-3-1"},
        )
        assert opp_res.status_code == 403, opp_res.text

        app.dependency_overrides[get_current_match_user] = lambda: User(
            id="home-manager-user",
            email="home@example.com",
            username="homemgr",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        owner_res = client.post(
            f"/api/matches/{match_id}/tactics",
            json={
                "press_intensity": 78,
                "defensive_line": 64,
                "tempo": 82,
                "risk_level": 70,
                "formation": "4-2-3-1",
                "side": "home",
            },
        )
        assert owner_res.status_code == 403, owner_res.text
        assert "First-Team Manager" in owner_res.json()["detail"]

        # 3. Internal simulation/manager engine update remains durably persisted & readable via GET tactics
        applied = hub.set_tactics(
            match_id,
            side="home",
            press_intensity=78,
            defensive_line=64,
            tempo=82,
            risk_level=70,
            formation="4-2-3-1",
        )
        assert applied["press_intensity"] == 78
        assert applied["formation"] == "4-2-3-1"

        # 4. GET tactics verifies the manager updates are reflected read-only
        refreshed = client.get(f"/api/matches/{match_id}/tactics")
        assert refreshed.status_code == 200
        refreshed_body = refreshed.json()
        assert refreshed_body["home"]["press_intensity"] == 78
        assert refreshed_body["home"]["formation"] == "4-2-3-1"

        # 5. Process restart simulation: clear in-memory _tactics; GET recovers from database metadata_json
        hub._tactics.clear()
        restarted = client.get(f"/api/matches/{match_id}/tactics")
        assert restarted.status_code == 200
        restarted_body = restarted.json()
        assert restarted_body["home"]["press_intensity"] == 78
        assert restarted_body["home"]["formation"] == "4-2-3-1"


def test_tactical_validation_and_substitutions() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=42))
    _insert_match(session_factory, replay_payload)
    match_id = replay_payload.match_id
    hub = LiveMatchHub(session_factory=session_factory)
    app.state.live_match_hub = hub
    hub.start_stream(match_id, replay_payload)

    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="home-manager-user",
        email="home@example.com",
        username="homemgr",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        # Non-existent match returns 404
        missing = client.post(
            "/api/matches/non-existent-match-xyz/tactics",
            json={"side": "home"},
        )
        assert missing.status_code == 404

        # Existing match rejects live owner POST with 403
        owner_block = client.post(
            f"/api/matches/{match_id}/tactics",
            json={"side": "home", "formation": "4-2-3-1"},
        )
        assert owner_block.status_code == 403

        # Read live state to get active pitch player IDs
        state_res = client.get(f"/api/matches/{match_id}/state")
        assert state_res.status_code == 200
        pitch_players = state_res.json()["pitch_players"]
        home_pitch_players = [p for p in pitch_players if p["is_home"]]
        assert len(home_pitch_players) > 0
        outgoing_id = home_pitch_players[0]["player_id"]
        outgoing_name = home_pitch_players[0]["name"]

        # Valid substitution applied internally by match manager/engine updates persisted viewer state
        bench_players = replay_payload.visual_identity.home_team.player_visuals[11:]
        assert bench_players, "test fixture requires a home bench"
        incoming_player = bench_players[0]
        incoming_id = incoming_player.player_id
        incoming_name = incoming_player.display_name
        sub_body = hub.set_tactics(
            match_id,
            side="home",
            substitutions=[
                {
                    "out_player_id": outgoing_id,
                    "in_player_id": incoming_id,
                    "out_player_name": outgoing_name,
                    "in_player_name": incoming_name,
                    "shirt_number": incoming_player.shirt_number or 14,
                }
            ],
        )
        assert sub_body["applied_substitutions"]

        # Check subsequent frame reflects the new substitute
        new_state = client.get(f"/api/matches/{match_id}/state").json()
        current_home_ids = [p["player_id"] for p in new_state["pitch_players"] if p["is_home"]]
        assert incoming_id in current_home_ids
        assert outgoing_id not in current_home_ids

        # Simulate a worker restart: the persisted viewer state must retain the
        # active substitute rather than rebuilding the original XI from replay data.
        app.state.live_match_hub = LiveMatchHub(session_factory=session_factory)
        restored = client.get(f"/api/matches/{match_id}/state")
        assert restored.status_code == 200, restored.text
        restored_home_ids = [p["player_id"] for p in restored.json()["pitch_players"] if p["is_home"]]
        assert incoming_id in restored_home_ids
        assert outgoing_id not in restored_home_ids


def test_live_tactics_without_stored_simulation_request_are_rejected() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=42))
    _insert_match(session_factory, replay_payload)
    match_id = replay_payload.match_id
    hub = LiveMatchHub(session_factory=session_factory)
    app.state.live_match_hub = hub
    hub.start_stream(match_id, replay_payload)

    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="home-manager-user",
        email="home@example.com",
        username="homemgr",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/api/matches/{match_id}/tactics",
            json={"side": "home", "formation": "4-2-3-1", "mentality": "attacking"},
        )
    assert response.status_code == 403, response.text
    assert "First-Team Manager" in response.json()["detail"]


def test_zero_zero_match_data_integrity() -> None:
    app, session_factory = _build_app()
    replay = MatchSimulationService().build_replay_payload(build_request(seed=42, match_id="zero-match-001"))
    replay.summary.home_score = 0
    replay.summary.away_score = 0
    replay.media_events = []
    replay.timeline.events = [
        e
        for e in replay.timeline.events
        if not any(
            k in str(getattr(e.event_type, "value", e.event_type)).lower()
            for k in ("goal", "shot", "miss", "save", "woodwork", "penalty", "chance", "attack")
        )
    ]
    _insert_match(session_factory, replay)
    client = TestClient(app)
    post_res = client.get(f"/api/matches/{replay.match_id}/post-match")
    assert post_res.status_code == 200
    post = post_res.json()["post_match"]
    assert post["shot_map"] == []
    assert post["motm"]["goals"] == 0
    assert "recorded xG: N/A - N/A" in post["share_summary"]


def test_read_match_pre_match_package() -> None:
    app, session_factory = _build_app()
    replay = MatchSimulationService().build_replay_payload(build_request(seed=42, match_id="pre-match-check-001"))
    _insert_match(session_factory, replay)
    client = TestClient(app)

    response = client.get(f"/api/matches/{replay.match_id}/pre-match")
    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == replay.match_id
    assert "pre_match" in body
    pre = body["pre_match"]
    assert "home_form" in pre
    assert "away_form" in pre
    assert "key_duel" in pre
    assert "storyline" in pre


def test_fan_predictions_persistence_and_deduplication() -> None:
    app, session_factory = _build_app()
    replay = MatchSimulationService().build_replay_payload(build_request(seed=42, match_id="prediction-check-001"))
    _insert_match(session_factory, replay)
    client = TestClient(app)

    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="voter-user-001",
        email="voter@example.com",
        username="voter",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    # 1. First vote is recorded
    vote_res = client.post(
        f"/api/matches/{replay.match_id}/predictions",
        json={"choice": "home"},
    )
    assert vote_res.status_code == 200, vote_res.text
    vote_body = vote_res.json()
    assert vote_body["choice"] == "home"
    assert vote_body["home_votes"] == 1
    assert vote_body["total_votes"] == 1

    # 2. Duplicate vote with same user is rejected with 409 Conflict
    dup_res = client.post(
        f"/api/matches/{replay.match_id}/predictions",
        json={"choice": "away"},
    )
    assert dup_res.status_code == 409, dup_res.text

    # 3. GET retrieves persisted vote counts
    read_res = client.get(f"/api/matches/{replay.match_id}/predictions")
    assert read_res.status_code == 200
    read_body = read_res.json()
    assert read_body["total_votes"] == 1
    assert read_body["home_votes"] == 1
    assert read_body["home_win_pct"] == 100


def test_rewards_claim_idempotency() -> None:
    app, session_factory = _build_app()
    replay = MatchSimulationService().build_replay_payload(build_request(seed=42, match_id="reward-check-001"))
    _insert_match(session_factory, replay)
    client = TestClient(app)

    reward_claimer = User(
        id="reward-claimer-001",
        email="claimer@example.com",
        username="claimer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )
    reward_admin = User(
        id="reward-admin-001",
        email="reward-admin@example.com",
        username="reward-admin",
        password_hash="hashed-password",  # pragma: allowlist secret
        role=UserRole.ADMIN,
        is_active=True,
    )
    with session_factory() as session:
        session.add_all([reward_claimer, reward_admin])
        seed_economic_policy(session)
        RewardEngineService(session).credit_promo_pool(
            actor=reward_admin,
            amount=Decimal("100.0000"),
            reference="match-reward-test-pool",
        )
        session.commit()
    app.dependency_overrides[get_current_match_user] = lambda: reward_claimer

    # 1. First claim succeeds
    claim_res = client.post(f"/api/matches/{replay.match_id}/rewards/claim")
    assert claim_res.status_code == 200, claim_res.text
    claim_body = claim_res.json()
    assert claim_body["claimed"] is True
    assert claim_body["status"] in {"claimed", "already_claimed"}
    assert "xp" not in claim_body
    assert claim_body["talent_coin"] == claim_body["net_amount"]

    # 2. Repeated claim is idempotent (returns already_claimed)
    claim_again = client.post(f"/api/matches/{replay.match_id}/rewards/claim")
    assert claim_again.status_code == 200
    again_body = claim_again.json()
    assert again_body["claimed"] is True
    assert again_body["status"] == "already_claimed"
    assert "xp" not in again_body
    assert again_body["talent_coin"] == again_body["net_amount"]


def test_live_match_appointed_first_team_manager_e2e_authority_and_mutations() -> None:
    from app.auth.dependencies import get_optional_current_user
    from app.owner_console.models import OwnerClubState

    app, session_factory = _build_app()
    sim_request = build_request(seed=101)
    sim_service = MatchSimulationService()
    replay_payload = sim_service.build_replay_payload(sim_request)
    match_id = replay_payload.match_id
    home_club_id = replay_payload.summary.home_stats.team_id
    away_club_id = replay_payload.summary.away_stats.team_id

    # Create users
    home_ftm = User(
        id="user-home-ftm",
        email="homeftm@test.com",
        username="homeftm",
        password_hash="hash",  # pragma: allowlist secret
        is_active=True,
    )
    away_ftm = User(
        id="user-away-ftm",
        email="awayftm@test.com",
        username="awayftm",
        password_hash="hash",  # pragma: allowlist secret
        is_active=True,
    )
    plain_owner = User(
        id="user-plain-owner",
        email="owner@test.com",
        username="owner",
        password_hash="hash",  # pragma: allowlist secret
        is_active=True,
    )
    spectator = User(
        id="user-spectator",
        email="spec@test.com",
        username="spec",
        password_hash="hash",  # pragma: allowlist secret
        is_active=True,
    )

    with session_factory() as session:
        session.add_all([home_ftm, away_ftm, plain_owner, spectator])

        # Home club state with manager_json pointing to home_ftm
        session.add(
            OwnerClubState(
                club_id=home_club_id,
                club_name="Home Club",
                owner_user_id=plain_owner.id,
                manager_json={"user_id": home_ftm.id, "delegate_user_id": None},
                facilities_json={},
            )
        )

        # Away club state with executive_staff first_team_manager pointing to away_ftm
        session.add(
            OwnerClubState(
                club_id=away_club_id,
                club_name="Away Club",
                owner_user_id=plain_owner.id,
                manager_json={},
                facilities_json={"_executive_staff": {"first_team_manager": {"user_id": away_ftm.id}}},
            )
        )

        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="comp-e2e-1",
                round_id="round-e2e-1",
                round_number=1,
                home_club_id=home_club_id,
                away_club_id=away_club_id,
                status="live",
                metadata_json={
                    "replay_payload": replay_payload.model_dump(mode="json"),
                    "simulation_request": sim_request.model_dump(mode="json"),
                },
            )
        )
        session.commit()

    hub = LiveMatchHub(session_factory=session_factory)
    app.state.live_match_hub = hub
    hub.start_stream(
        match_id,
        replay_payload,
        simulation_request=sim_request.model_dump(mode="json"),
    )

    try:
        with TestClient(app) as client:
            # 1. Anonymous GET tactics -> can_edit_tactics is False
            res = client.get(f"/api/matches/{match_id}/tactics")
            assert res.status_code == 200
            data = res.json()
            assert data["can_edit_tactics"] is False
            assert data["authorized_tactical_side"] is None

            # 2. Plain owner GET tactics -> can_edit_tactics is False
            app.dependency_overrides[get_optional_current_user] = lambda: plain_owner
            res = client.get(f"/api/matches/{match_id}/tactics")
            assert res.status_code == 200
            data = res.json()
            assert data["can_edit_tactics"] is False
            assert data["authorized_tactical_side"] is None

            # 3. Home FTM GET tactics -> can_edit_tactics is True, side is "home"
            app.dependency_overrides[get_optional_current_user] = lambda: home_ftm
            res = client.get(f"/api/matches/{match_id}/tactics")
            assert res.status_code == 200
            data = res.json()
            assert data["can_edit_tactics"] is True
            assert data["authorized_tactical_side"] == "home"

            # 4. Away FTM GET tactics -> can_edit_tactics is True, side is "away"
            app.dependency_overrides[get_optional_current_user] = lambda: away_ftm
            res = client.get(f"/api/matches/{match_id}/tactics")
            assert res.status_code == 200
            data = res.json()
            assert data["can_edit_tactics"] is True
            assert data["authorized_tactical_side"] == "away"

            # 5. Anonymous POST tactics -> 401
            app.dependency_overrides.pop(get_optional_current_user, None)
            res = client.post(f"/api/matches/{match_id}/tactics", json={"side": "home", "formation": "4-4-2"})
            assert res.status_code == 401

            # 6. Spectator POST tactics -> 403
            app.dependency_overrides[get_current_match_user] = lambda: spectator
            res = client.post(f"/api/matches/{match_id}/tactics", json={"side": "home", "formation": "4-4-2"})
            assert res.status_code == 403
            assert "First-Team Manager" in res.json()["detail"]

            # 7. Plain owner POST tactics -> 403
            app.dependency_overrides[get_current_match_user] = lambda: plain_owner
            res = client.post(f"/api/matches/{match_id}/tactics", json={"side": "home", "formation": "4-4-2"})
            assert res.status_code == 403
            assert "First-Team Manager" in res.json()["detail"]

            # 8. Home FTM targeting away side -> 403
            app.dependency_overrides[get_current_match_user] = lambda: home_ftm
            res = client.post(f"/api/matches/{match_id}/tactics", json={"side": "away", "formation": "4-4-2"})
            assert res.status_code == 403

            # 9. Home FTM targeting home side with valid mutation -> 200
            res = client.post(
                f"/api/matches/{match_id}/tactics",
                json={
                    "side": "home",
                    "formation": "4-3-3",
                    "press_intensity": 70,
                    "defensive_line": 55,
                    "tempo": 75,
                    "risk_level": 60,
                },
            )
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["home"]["formation"] == "4-3-3"
            assert body["home"]["press_intensity"] == 70

            # 10. Substitution rejection with invalid player ids -> 400
            res = client.post(
                f"/api/matches/{match_id}/tactics",
                json={"side": "home", "substitutions": [{"in_player_id": "ghost-in", "out_player_id": "ghost-out"}]},
            )
            assert res.status_code == 400, res.text

            # 11. Valid substitution by the appointed manager -> 200, applied
            state = client.get(f"/api/matches/{match_id}/state").json()
            outgoing = [p for p in state["pitch_players"] if p["is_home"]][0]
            incoming = replay_payload.visual_identity.home_team.player_visuals[11]
            res = client.post(
                f"/api/matches/{match_id}/tactics",
                json={
                    "side": "home",
                    "substitutions": [
                        {
                            "out_player_id": outgoing["player_id"],
                            "in_player_id": incoming.player_id,
                            "out_player_name": outgoing["name"],
                            "in_player_name": incoming.display_name,
                            "shirt_number": incoming.shirt_number or 14,
                        }
                    ],
                },
            )
            assert res.status_code == 200, res.text
            after = client.get(f"/api/matches/{match_id}/state").json()
            home_ids = [p["player_id"] for p in after["pitch_players"] if p["is_home"]]
            assert incoming.player_id in home_ids
            assert outgoing["player_id"] not in home_ids

            # 12. Match without a live runtime (e.g. completed) rejects mutations -> 400
            with session_factory() as session:
                cm = session.get(CompetitionMatch, match_id)
                cm.status = "completed"
                session.commit()
            app.state.live_match_hub = LiveMatchHub(session_factory=session_factory)
            res = client.post(f"/api/matches/{match_id}/tactics", json={"side": "home", "formation": "5-3-2"})
            assert res.status_code == 400, res.text
    finally:
        pass
