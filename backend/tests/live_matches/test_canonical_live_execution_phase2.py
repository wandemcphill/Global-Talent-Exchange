from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_match_user, get_optional_current_user
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.core.cache import NullCacheBackend
from app.core.config import reset_settings_cache
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import LiveMatchHub
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_match_execution import (
    CompetitionMatchExecution,
    CompetitionMatchTacticalCommand,
)
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.player_contract import PlayerContract
from app.models.player_match_performance import PlayerMatchPerformance
from app.models.user import User, UserRole
from app.owner_console.models import OwnerClubState
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_phase2_app() -> tuple[FastAPI, sessionmaker[Session], object]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(live_matches_router)
    app.state.session_factory = session_factory
    app.state.live_match_hub = LiveMatchHub(session_factory=session_factory, cache_backend=NullCacheBackend())
    return app, session_factory, engine


def _seed_club_squad(session: Session, club: ClubProfile, *, match_date: date, count: int = 18) -> list[Player]:
    roles = [
        "goalkeeper",
        "defender",
        "defender",
        "defender",
        "defender",
        "midfielder",
        "midfielder",
        "midfielder",
        "forward",
        "forward",
        "forward",
        "goalkeeper",
        "defender",
        "midfielder",
        "forward",
        "midfielder",
        "defender",
        "forward",
    ]
    players: list[Player] = []
    for idx in range(count):
        pos = roles[idx % len(roles)]
        player_id = str(uuid4())
        player = Player(
            id=player_id,
            source_provider="test_provider",
            provider_external_id=f"ext_{player_id[:12]}",
            full_name=f"{club.club_name} Player {idx + 1}",
            first_name=f"Player{idx + 1}",
            last_name=club.club_name,
            position=pos,
            normalized_position=pos,
            date_of_birth=date(2000, 1, 1),
            is_real_player=False,
            is_tradable=True,
            current_club_profile_id=club.id,
        )
        session.add(player)
        session.add(
            PlayerContract(
                id=str(uuid4()),
                player_id=player_id,
                club_id=club.id,
                status="active",
                signed_on=match_date - timedelta(days=30),
                starts_on=match_date - timedelta(days=30),
                ends_on=match_date + timedelta(days=730),
                wage_amount=Decimal("1000.00"),
            )
        )
        players.append(player)
    session.flush()
    return players


def _seed_canonical_fixture(session: Session) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    home_owner = User(
        id=f"user-home-owner-{suffix}",
        email=f"home-owner-{suffix}@gtex.test",
        username=f"homeowner_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    away_owner = User(
        id=f"user-away-owner-{suffix}",
        email=f"away-owner-{suffix}@gtex.test",
        username=f"awayowner_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    home_ftm = User(
        id=f"user-home-ftm-{suffix}",
        email=f"home-ftm-{suffix}@gtex.test",
        username=f"homeftm_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    away_ftm = User(
        id=f"user-away-ftm-{suffix}",
        email=f"away-ftm-{suffix}@gtex.test",
        username=f"awayftm_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    spectator = User(
        id=f"user-spec-{suffix}",
        email=f"spec-{suffix}@gtex.test",
        username=f"spec_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    session.add_all([home_owner, away_owner, home_ftm, away_ftm, spectator])
    session.flush()

    club_home = ClubProfile(
        id=f"club-home-{suffix}",
        owner_user_id=home_owner.id,
        club_name=f"Home FC {suffix}",
        short_name="HOM",
        slug=f"home-fc-{suffix}",
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#22cc88",
    )
    club_away = ClubProfile(
        id=f"club-away-{suffix}",
        owner_user_id=away_owner.id,
        club_name=f"Away FC {suffix}",
        short_name="AWY",
        slug=f"away-fc-{suffix}",
        primary_color="#332211",
        secondary_color="#eeeeee",
        accent_color="#cc8822",
    )
    session.add_all([club_home, club_away])
    session.flush()

    match_date = date(2026, 6, 15)
    _seed_club_squad(session, club_home, match_date=match_date)
    _seed_club_squad(session, club_away, match_date=match_date)

    session.add(
        OwnerClubState(
            club_id=club_home.id,
            club_name=club_home.club_name,
            owner_user_id=home_owner.id,
            manager_json={"user_id": home_ftm.id},
            facilities_json={},
        )
    )
    session.add(
        OwnerClubState(
            club_id=club_away.id,
            club_name=club_away.club_name,
            owner_user_id=away_owner.id,
            manager_json={},
            facilities_json={"_executive_staff": {"first_team_manager": {"user_id": away_ftm.id}}},
        )
    )

    comp = Competition(
        id=f"comp-{suffix}",
        host_user_id=home_owner.id,
        name=f"Canonical Phase 2 Cup {suffix}",
        format=CompetitionFormat.LEAGUE.value,
        source_type="gtex_platform",
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        stage="league",
        currency="coin",
        metadata_json={},
    )
    session.add(comp)
    session.flush()

    session.add(
        CompetitionRuleSet(
            id=f"rules-{suffix}",
            competition_id=comp.id,
            format=CompetitionFormat.LEAGUE.value,
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
        )
    )
    p_home = CompetitionParticipant(id=f"part-h-{suffix}", competition_id=comp.id, club_id=club_home.id)
    p_away = CompetitionParticipant(id=f"part-a-{suffix}", competition_id=comp.id, club_id=club_away.id)
    comp_round = CompetitionRound(
        id=f"round-{suffix}",
        competition_id=comp.id,
        round_number=1,
        stage="league",
        status="active",
    )
    session.add_all([p_home, p_away, comp_round])
    session.flush()

    match = CompetitionMatch(
        id=f"match-{suffix}",
        competition_id=comp.id,
        round_id=comp_round.id,
        round_number=1,
        stage="league",
        home_club_id=club_home.id,
        away_club_id=club_away.id,
        match_date=match_date,
        scheduled_at=datetime(2026, 6, 15, 15, 0, tzinfo=UTC),
        status=MatchStatus.SCHEDULED.value,
        requires_winner=False,
        metadata_json={},
    )
    session.add(match)
    session.commit()
    return {
        "match": match,
        "home_owner": home_owner,
        "away_owner": away_owner,
        "home_ftm": home_ftm,
        "away_ftm": away_ftm,
        "spectator": spectator,
        "p_home": p_home,
        "p_away": p_away,
    }


def test_canonical_live_tactical_revision_preserves_history_and_reconciles_settlement() -> None:
    app, session_factory, engine = _build_phase2_app()
    try:
        with session_factory() as session:
            bundle = _seed_canonical_fixture(session)
            match: CompetitionMatch = bundle["match"]  # type: ignore[assignment]
            home_ftm: User = bundle["home_ftm"]  # type: ignore[assignment]
            service = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            service.start_live_execution(match.id)
            _, ex, _ = service.step_execution(match.id, target_minute=25, stop_at_halftime=True)
            session.commit()
            assert ex.execution_revision == 1
            assert ex.current_minute == 25
            committed_before = [dict(ev) for ev in ex.committed_events_json]
            base_request_dump = dict(ex.simulation_request_json)

        # Shadow baseline with identical seed to confirm revision 2 diverges future events after tactical shift
        with session_factory() as session:
            bundle2 = _seed_canonical_fixture(session)
            baseline_match: CompetitionMatch = bundle2["match"]  # type: ignore[assignment]
            from app.match_engine.schemas import MatchSimulationRequest

            base_req = MatchSimulationRequest.model_validate(
                {
                    **base_request_dump,
                    "match_id": baseline_match.id,
                }
            )
            base_service = CanonicalLiveExecutionService(session)
            base_service.start_live_execution(baseline_match.id, request=base_req)
            base_service.step_execution(baseline_match.id, target_minute=25, stop_at_halftime=True)
            _, base_exec_final, _, _ = base_service.execute_to_completion(baseline_match.id)
            session.commit()

        app.dependency_overrides[get_current_match_user] = lambda: home_ftm
        app.dependency_overrides[get_optional_current_user] = lambda: home_ftm

        with TestClient(app) as client:
            res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "formation": "3-5-2",
                    "mentality": "attacking",
                    "press_intensity": 88,
                    "defensive_line": 74,
                    "tempo": 86,
                    "risk_level": 80,
                    "instructions": ["high_press", "overlap_wings"],
                    "expected_revision": 1,
                    "idempotency_key": "home-min25-shift",
                },
            )
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["execution_revision"] == 2
            assert body["effective_minute"] == 26
            assert body["idempotent_replay"] is False
            assert body["home"]["formation"] == "3-5-2"
            assert body["home"]["press_intensity"] == 88
            assert body["home"]["pending_effective_minute"] == 26

            # Idempotent retry with old expected_revision=1 returns cached revision=2 cleanly
            replay_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "formation": "3-5-2",
                    "mentality": "attacking",
                    "press_intensity": 88,
                    "defensive_line": 74,
                    "tempo": 86,
                    "risk_level": 80,
                    "instructions": ["high_press", "overlap_wings"],
                    "expected_revision": 1,
                    "idempotency_key": "home-min25-shift",
                },
            )
            assert replay_res.status_code == 200, replay_res.text
            replay_body = replay_res.json()
            assert replay_body["idempotent_replay"] is True
            assert replay_body["execution_revision"] == 2

            # Idempotency conflict with different payload -> 409
            conflict_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "formation": "5-3-2",
                    "expected_revision": 2,
                    "idempotency_key": "home-min25-shift",
                },
            )
            assert conflict_res.status_code == 409, conflict_res.text

            # Stale expected_revision with new key -> 409
            stale_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "formation": "4-4-2",
                    "expected_revision": 1,
                    "idempotency_key": "home-min25-stale",
                },
            )
            assert stale_res.status_code == 409, stale_res.text

            tactics_read = client.get(f"/api/matches/{match.id}/tactics")
            assert tactics_read.status_code == 200
            tactics_data = tactics_read.json()
            assert tactics_data["execution_revision"] == 2
            assert tactics_data["can_edit_tactics"] is True
            assert tactics_data["home"]["formation"] == "3-5-2"
            assert tactics_data["home"]["instructions"] == ["high_press", "overlap_wings"]

            state_read = client.get(f"/api/matches/{match.id}/state")
            assert state_read.status_code == 200
            state_data = state_read.json()
            assert state_data["is_live"] is True
            assert state_data["execution_revision"] == 2

        with session_factory() as session:
            ex_mid = session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match.id)
            )
            assert ex_mid is not None
            assert ex_mid.execution_revision == 2
            # Past events <= 25 remain untouched
            assert ex_mid.committed_events_json == committed_before

            # Advance past minute 26 -> scheduled tactical_change executes and commits
            svc = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            svc.step_execution(match.id, target_minute=45, stop_at_halftime=True)
            svc.step_execution(match.id, target_minute=120, stop_at_halftime=False, resume_halftime=True)
            session.commit()

            settled_match = session.get(CompetitionMatch, match.id)
            settled_exec = session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match.id)
            )
            assert settled_match is not None and settled_exec is not None
            assert settled_match.status == MatchStatus.COMPLETED.value
            assert settled_match.stats_applied is True
            assert settled_exec.execution_revision == 2
            assert settled_exec.home_tactics_json["formation"] == "3-5-2"
            assert settled_exec.home_tactics_json["pressing"] == 88
            assert any(
                ev["event_type"] == "tactical_change" and ev["minute"] == 26
                for ev in settled_exec.committed_events_json
            )
            # First-half <=25 sequence matches baseline, second half diverges
            rev2_after_25 = [
                (ev["minute"], ev["event_type"], ev.get("team_id"))
                for ev in settled_exec.committed_events_json
                if ev["minute"] > 25
            ]
            base_after_25 = [
                (ev["minute"], ev["event_type"], ev.get("team_id"))
                for ev in base_exec_final.committed_events_json
                if ev["minute"] > 25
            ]
            assert rev2_after_25 != base_after_25

            cmd_rows = list(
                session.scalars(
                    select(CompetitionMatchTacticalCommand).where(
                        CompetitionMatchTacticalCommand.match_id == match.id
                    )
                ).all()
            )
            assert len(cmd_rows) == 1
            assert cmd_rows[0].status == "accepted"
            assert cmd_rows[0].resulting_revision == 2
            assert cmd_rows[0].effective_minute == 26
    finally:
        engine.dispose()


def test_halftime_pause_applies_tactics_and_substitutions_immediately_and_updates_performances() -> None:
    app, session_factory, engine = _build_phase2_app()
    try:
        with session_factory() as session:
            bundle = _seed_canonical_fixture(session)
            match: CompetitionMatch = bundle["match"]  # type: ignore[assignment]
            home_ftm: User = bundle["home_ftm"]  # type: ignore[assignment]
            service = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            service.start_live_execution(match.id)
            _, ex, _ = service.step_execution(match.id, target_minute=60, stop_at_halftime=True)
            session.commit()
            assert ex.execution_status == "paused"
            assert ex.paused_reason == "halftime"
            assert ex.current_minute == 45

            home_state_json = ex.checkpoint_json["home_state"]
            sim_req_json = ex.simulation_request_json
            home_starters = sim_req_json["home_team"]["starters"]
            home_bench = sim_req_json["home_team"]["bench"]
            out_player = next(
                p
                for p in home_starters
                if str(p["role"]).upper() not in {"GK", "GOALKEEPER"} and p["player_id"] in home_state_json["active_player_ids"]
            )
            in_player = next(
                p
                for p in home_bench
                if str(p["role"]).upper() not in {"GK", "GOALKEEPER"} and p["player_id"] in home_state_json["bench_player_ids"]
            )

        app.dependency_overrides[get_current_match_user] = lambda: home_ftm
        app.dependency_overrides[get_optional_current_user] = lambda: home_ftm

        with TestClient(app) as client:
            res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "formation": "4-2-3-1",
                    "mentality": "ultra_attacking",
                    "press_intensity": 82,
                    "substitutions": [
                        {
                            "out_player_id": out_player["player_id"],
                            "in_player_id": in_player["player_id"],
                            "reason": "halftime_tactical_change",
                        }
                    ],
                    "expected_revision": 1,
                    "idempotency_key": "ht-sub-1",
                },
            )
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["applied_immediately"] is True
            assert body["effective_minute"] == 45
            assert body["execution_revision"] == 2
            assert len(body["applied_substitutions"]) == 1

            state_res = client.get(f"/api/matches/{match.id}/state")
            assert state_res.status_code == 200
            state_payload = state_res.json()
            assert state_payload["is_live"] is True
            home_pitch_ids = {p["player_id"] for p in state_payload["pitch_players"] if p["is_home"]}
            assert in_player["player_id"] in home_pitch_ids
            assert out_player["player_id"] not in home_pitch_ids

        with session_factory() as session:
            ht_events = list(
                session.scalars(
                    select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)
                ).all()
            )
            assert any(ev.event_type == "substitution" and ev.minute == 45 for ev in ht_events)
            assert any(ev.event_type == "tactical_change" and ev.minute == 45 for ev in ht_events)

            # Complete match through FT
            svc = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            svc.step_execution(match.id, target_minute=120, stop_at_halftime=False, resume_halftime=True)
            session.commit()

            perf_out = session.scalar(
                select(PlayerMatchPerformance).where(
                    PlayerMatchPerformance.match_id == match.id,
                    PlayerMatchPerformance.player_id == out_player["player_id"],
                )
            )
            perf_in = session.scalar(
                select(PlayerMatchPerformance).where(
                    PlayerMatchPerformance.match_id == match.id,
                    PlayerMatchPerformance.player_id == in_player["player_id"],
                )
            )
            assert perf_out is not None and perf_in is not None
            assert perf_out.minutes_played == 45
            assert perf_in.minutes_played > 0
    finally:
        engine.dispose()


def test_canonical_substitution_eligibility_gk_protection_and_authority_rbac() -> None:
    app, session_factory, engine = _build_phase2_app()
    try:
        with session_factory() as session:
            bundle = _seed_canonical_fixture(session)
            match: CompetitionMatch = bundle["match"]  # type: ignore[assignment]
            home_owner: User = bundle["home_owner"]  # type: ignore[assignment]
            home_ftm: User = bundle["home_ftm"]  # type: ignore[assignment]
            away_ftm: User = bundle["away_ftm"]  # type: ignore[assignment]
            spectator: User = bundle["spectator"]  # type: ignore[assignment]

            service = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            service.start_live_execution(match.id)
            _, ex, _ = service.step_execution(match.id, target_minute=15, stop_at_halftime=True)
            session.commit()

            sim_req = ex.simulation_request_json
            home_starters = sim_req["home_team"]["starters"]
            home_bench = sim_req["home_team"]["bench"]
            home_gk = next(p for p in home_starters if str(p["role"]).upper() in {"GK", "GOALKEEPER"})
            outfield_starters = [p for p in home_starters if str(p["role"]).upper() not in {"GK", "GOALKEEPER"}]
            outfield_bench = [p for p in home_bench if str(p["role"]).upper() not in {"GK", "GOALKEEPER"}]

        with TestClient(app) as client:
            # 1. Anonymous user rejected (401)
            anon = client.post(
                f"/api/matches/{match.id}/tactics",
                json={"side": "home", "formation": "4-4-2"},
            )
            assert anon.status_code == 401

            # 2. Club owner rejected (403)
            app.dependency_overrides[get_current_match_user] = lambda: home_owner
            owner_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={"side": "home", "formation": "4-4-2"},
            )
            assert owner_res.status_code == 403

            # 3. Spectator rejected (403)
            app.dependency_overrides[get_current_match_user] = lambda: spectator
            spec_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={"side": "home", "formation": "4-4-2"},
            )
            assert spec_res.status_code == 403

            # 4. Away FTM targeting home side rejected (403)
            app.dependency_overrides[get_current_match_user] = lambda: away_ftm
            cross_res = client.post(
                f"/api/matches/{match.id}/tactics",
                json={"side": "home", "formation": "4-4-2"},
            )
            assert cross_res.status_code == 403

            # 5. Home FTM illegal substitution: taking off the only GK for an outfielder -> 400
            app.dependency_overrides[get_current_match_user] = lambda: home_ftm
            gk_err = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "substitutions": [
                        {
                            "out_player_id": home_gk["player_id"],
                            "in_player_id": outfield_bench[0]["player_id"],
                        }
                    ],
                },
            )
            assert gk_err.status_code == 400, gk_err.text
            assert "goalkeeper" in gk_err.json()["detail"].lower()

            # 6. Outgoing player not on pitch -> 400
            bad_out = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "substitutions": [
                        {
                            "out_player_id": outfield_bench[0]["player_id"],
                            "in_player_id": outfield_bench[1]["player_id"],
                        }
                    ],
                },
            )
            assert bad_out.status_code == 400

            # 7. More than 5 substitutions -> 400
            bad_many = client.post(
                f"/api/matches/{match.id}/tactics",
                json={
                    "side": "home",
                    "substitutions": [
                        {
                            "out_player_id": outfield_starters[i]["player_id"],
                            "in_player_id": outfield_bench[i]["player_id"],
                        }
                        for i in range(6)
                    ],
                },
            )
            assert bad_many.status_code == 400
            assert "allowable substitutions" in bad_many.json()["detail"].lower()

        # 8. Post-FT rejection -> 409
        with session_factory() as session:
            svc = CanonicalLiveExecutionService(session, hub=app.state.live_match_hub)
            svc.step_execution(match.id, target_minute=120, stop_at_halftime=False, resume_halftime=True)
            session.commit()

        with TestClient(app) as client:
            app.dependency_overrides[get_current_match_user] = lambda: home_ftm
            post_ft = client.post(
                f"/api/matches/{match.id}/tactics",
                json={"side": "home", "formation": "5-3-2"},
            )
            assert post_ft.status_code == 409, post_ft.text
    finally:
        engine.dispose()
