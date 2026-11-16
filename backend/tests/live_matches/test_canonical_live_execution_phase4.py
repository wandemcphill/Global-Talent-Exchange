from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_match_user, get_current_user
from app.broadcast.match_room_manager import adapt_match_stream_message, sanitize_public_spectator_payload
from app.broadcast.spectator_gateway import BroadcastRuntime, router as spectator_gateway_router
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.core.config import reset_settings_cache
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import LiveMatchHub
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.player_contract import PlayerContract
from app.models.user import User, UserRole
from app.owner_console.models import OwnerClubState
from app.realtime.match_stream_service import MatchStreamService
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_phase4_app_and_db() -> tuple[FastAPI, sessionmaker[Session], object]:
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
    app.include_router(spectator_gateway_router)
    app.state.session_factory = session_factory
    app.state.broadcast_runtime = BroadcastRuntime(
        redis_url=None,
        delay_seconds=0,
        viewer_ttl_seconds=60,
        heartbeat_interval_seconds=60,
        max_queue_size=64,
        require_redis_tickets=False,
    )
    app.state.broadcast = app.state.broadcast_runtime
    return app, session_factory, engine


def _seed_club_players(session: Session, club: ClubProfile, *, match_date: date, count: int = 18) -> list[Player]:
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
            first_name=f"P{idx + 1}",
            last_name=club.short_name or "FC",
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


def _seed_phase4_fixture(
    session: Session,
    *,
    is_knockout: bool = False,
) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    home_owner = User(
        id=f"u4-ho-{suffix}",
        email=f"u4-ho-{suffix}@gtex.test",
        username=f"u4_ho_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    away_owner = User(
        id=f"u4-ao-{suffix}",
        email=f"u4-ao-{suffix}@gtex.test",
        username=f"u4_ao_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    home_ftm = User(
        id=f"u4-hftm-{suffix}",
        email=f"u4-hftm-{suffix}@gtex.test",
        username=f"u4_hftm_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    spec_one = User(
        id=f"u4-sp1-{suffix}",
        email=f"u4-sp1-{suffix}@gtex.test",
        username=f"u4_sp1_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    spec_two = User(
        id=f"u4-sp2-{suffix}",
        email=f"u4-sp2-{suffix}@gtex.test",
        username=f"u4_sp2_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    session.add_all([home_owner, away_owner, home_ftm, spec_one, spec_two])
    session.flush()

    club_home = ClubProfile(
        id=f"c4h-{suffix}",
        owner_user_id=home_owner.id,
        club_name=f"Sunburst Athletic {suffix}",
        short_name="SUN",
        slug=f"sunburst-{suffix}",
        primary_color="#114422",
        secondary_color="#ffffff",
        accent_color="#f59e0b",
    )
    club_away = ClubProfile(
        id=f"c4a-{suffix}",
        owner_user_id=away_owner.id,
        club_name=f"Silvercrest United {suffix}",
        short_name="SIL",
        slug=f"silvercrest-{suffix}",
        primary_color="#1e293b",
        secondary_color="#e2e8f0",
        accent_color="#38bdf8",
    )
    session.add_all([club_home, club_away])
    session.flush()

    match_date = date(2026, 7, 1)
    _seed_club_players(session, club_home, match_date=match_date)
    _seed_club_players(session, club_away, match_date=match_date)

    session.add_all(
        [
            OwnerClubState(
                club_id=club_home.id,
                club_name=club_home.club_name,
                owner_user_id=home_owner.id,
                manager_json={"user_id": home_ftm.id},
                facilities_json={},
            ),
            OwnerClubState(
                club_id=club_away.id,
                club_name=club_away.club_name,
                owner_user_id=away_owner.id,
                manager_json={},
                facilities_json={},
            ),
        ]
    )

    comp = Competition(
        id=f"comp4-{suffix}",
        host_user_id=home_owner.id,
        name=f"Canonical Showcase {suffix}",
        format=CompetitionFormat.CUP.value if is_knockout else CompetitionFormat.LEAGUE.value,
        source_type="gtex_platform",
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        stage="final" if is_knockout else "league",
        currency="coin",
        metadata_json={"is_cup": is_knockout},
    )
    session.add(comp)
    session.flush()

    session.add(
        CompetitionRuleSet(
            id=f"rules4-{suffix}",
            competition_id=comp.id,
            format=CompetitionFormat.CUP.value if is_knockout else CompetitionFormat.LEAGUE.value,
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
        )
    )
    session.add_all(
        [
            CompetitionParticipant(id=f"p4h-{suffix}", competition_id=comp.id, club_id=club_home.id),
            CompetitionParticipant(id=f"p4a-{suffix}", competition_id=comp.id, club_id=club_away.id),
        ]
    )
    comp_round = CompetitionRound(
        id=f"r4-{suffix}",
        competition_id=comp.id,
        round_number=1,
        stage="final" if is_knockout else "league",
        status="active",
    )
    session.add(comp_round)
    session.flush()

    match = CompetitionMatch(
        id=f"m4-{suffix}",
        competition_id=comp.id,
        round_id=comp_round.id,
        round_number=1,
        stage="final" if is_knockout else "league",
        home_club_id=club_home.id,
        away_club_id=club_away.id,
        match_date=match_date,
        scheduled_at=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
        status=MatchStatus.SCHEDULED.value,
        requires_winner=is_knockout,
        metadata_json={},
    )
    session.add(match)
    session.commit()
    return {
        "competition": comp,
        "match": match,
        "home_ftm": home_ftm,
        "spec_one": spec_one,
        "spec_two": spec_two,
    }


def test_broadcast_spectator_parity_duration_caps_and_reconnect_cursor() -> None:
    app, session_factory, engine = _build_phase4_app_and_db()
    hub = LiveMatchHub(session_factory=session_factory)
    app.state.live_match_hub = hub
    try:
        with session_factory() as session:
            league_seed = _seed_phase4_fixture(session, is_knockout=False)
            knockout_seed = _seed_phase4_fixture(session, is_knockout=True)

            league_match_id = league_seed["match"].id
            knockout_match_id = knockout_seed["match"].id

            svc = CanonicalLiveExecutionService(session, hub=hub)
            svc.start_live_execution(league_match_id)
            svc.start_live_execution(knockout_match_id)

            # Force oversized values onto execution rows to verify hub view clamping.
            exec_league = svc.get_execution(league_match_id)
            exec_knockout = svc.get_execution(knockout_match_id)
            assert exec_league is not None and exec_knockout is not None
            exec_league.assigned_duration_seconds = 1400
            exec_knockout.assigned_duration_seconds = 1400
            session.commit()

            # Advance league match to halftime, apply live tactical mutation (revision -> 2), then step to minute 60.
            svc.step_execution(league_match_id, target_minute=45, stop_at_halftime=True)
            svc.apply_live_tactical_command(
                league_match_id,
                side="home",
                actor_user_id=league_seed["home_ftm"].id,
                mentality="attacking",
                tempo=78,
                press_intensity=74,
                expected_revision=1,
                idempotency_key="phase4-ht-tac",
            )
            svc.step_execution(
                league_match_id,
                target_minute=60,
                stop_at_halftime=False,
                resume_halftime=True,
                settle_on_completion=False,
            )
            session.commit()

            state_league = hub.get_state(league_match_id)
            state_knockout = hub.get_state(knockout_match_id)
            assert state_league is not None and state_knockout is not None
            assert state_league.assigned_duration_seconds == 600
            assert state_knockout.assigned_duration_seconds == 900
            assert state_league.pause_replay_enabled is False
            assert state_league.execution_revision == 2
            assert state_league.commit_cursor == state_league.event_count

        spec_one = league_seed["spec_one"]
        spec_two = league_seed["spec_two"]
        active_user = {"user": spec_one}
        app.dependency_overrides[get_current_match_user] = lambda: active_user["user"]
        app.dependency_overrides[get_current_user] = lambda: active_user["user"]

        with TestClient(app) as client:
            # Two different spectators join and read state + events: strict parity.
            active_user["user"] = spec_one
            s1_res = client.post(f"/api/matches/{league_match_id}/spectate")
            assert s1_res.status_code == 200, s1_res.text
            s1_session = s1_res.json()
            assert s1_session["sync_strategy"] == "canonical_live_execution"
            assert s1_session["pause_replay_enabled"] is False
            assert s1_session["speed_modes"] == []
            assert s1_session["execution_revision"] == 2

            state_1 = client.get(f"/api/matches/{league_match_id}/state").json()
            events_1 = client.get(f"/api/matches/{league_match_id}/events").json()

            active_user["user"] = spec_two
            s2_res = client.post(f"/api/matches/{league_match_id}/spectate")
            assert s2_res.status_code == 200, s2_res.text
            s2_session = s2_res.json()
            assert s2_session["execution_revision"] == 2

            state_2 = client.get(f"/api/matches/{league_match_id}/state").json()
            events_2 = client.get(f"/api/matches/{league_match_id}/events").json()

            assert state_1["execution_revision"] == state_2["execution_revision"] == 2
            assert state_1["pause_replay_enabled"] is False
            assert state_1["commit_cursor"] == state_2["commit_cursor"]
            assert state_1["home"]["score"] == state_2["home"]["score"]
            assert state_1["away"]["score"] == state_2["away"]["score"]
            assert events_1["events"] == events_2["events"]
            assert state_1["broadcast_session"]["assigned_duration_seconds"] <= 600
            assert state_1["broadcast_session"]["pause_replay_enabled"] is False

            # Legacy WS /stream supports cursor resume and carries execution_revision + commit_cursor.
            all_events, full_cursor = hub.get_events_since(league_match_id, 0)
            assert full_cursor >= 4
            mid_cursor = full_cursor // 2
            with client.websocket_connect(
                f"/api/matches/{league_match_id}/stream?session_id={s1_session['id']}&cursor={mid_cursor}"
            ) as ws_resume:
                snapshot_msg = ws_resume.receive_json()
                assert snapshot_msg["kind"] == "snapshot"
                assert snapshot_msg["execution_revision"] == 2
                assert snapshot_msg["commit_cursor"] == mid_cursor

                events_msg = ws_resume.receive_json()
                assert events_msg["kind"] == "events"
                assert events_msg["execution_revision"] == 2
                assert events_msg["commit_cursor"] == full_cursor
                resumed_sequences = [ev["sequence"] for ev in events_msg["payload"]]
                expected_tail_sequences = [ev.sequence for ev in all_events[mid_cursor:]]
                assert resumed_sequences == expected_tail_sequences

            # Public /ws/spectate exposes canonical clock/revision metadata without leaking confidential tactics.
            with client.websocket_connect(f"/ws/spectate/{league_match_id}") as ws_public:
                pub_snap = ws_public.receive_json()
                assert pub_snap["type"] == "snapshot"
                canonical_meta = pub_snap["snapshot"]["metadata"]["canonical_execution"]
                assert canonical_meta["execution_revision"] == 2
                assert canonical_meta["clock_phase"] == "second_half"
                assert canonical_meta["pause_replay_enabled"] is False
                assert "tactics" not in pub_snap["snapshot"]["metadata"]
                assert "manager" not in pub_snap["snapshot"]["metadata"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


class _FailingHotCache:
    def get_match_state(self, match_id: str):
        raise RuntimeError("Simulated Redis outage on get_match_state")

    def set_match_state(self, match_id: str, state: dict, ttl_seconds: int = 3600):
        raise RuntimeError("Simulated Redis outage on set_match_state")

    def get_match_events(self, match_id: str, cursor: int = 0):
        raise RuntimeError("Simulated Redis outage on get_match_events")

    def append_match_events(self, match_id: str, events: list, ttl_seconds: int = 3600):
        raise RuntimeError("Simulated Redis outage on append_match_events")

    def clear_match_events(self, match_id: str):
        raise RuntimeError("Simulated Redis outage on clear_match_events")

    def clear_match_state(self, match_id: str):
        raise RuntimeError("Simulated Redis outage on clear_match_state")

    def list_active_matches(self):
        raise RuntimeError("Simulated Redis outage on list_active_matches")

    def publish_match_channel(self, channel: str, payload: dict):
        raise RuntimeError("Simulated Redis outage on publish_match_channel")

    def get(self, key: str):
        raise RuntimeError("Simulated Redis outage on get")

    def set(self, key: str, value, ttl_seconds: int = 3600):
        raise RuntimeError("Simulated Redis outage on set")


def test_redis_outage_degrades_gracefully_without_breaking_canonical_broadcast() -> None:
    app, session_factory, engine = _build_phase4_app_and_db()
    hub = LiveMatchHub(session_factory=session_factory)
    hub._hot_cache = _FailingHotCache()  # type: ignore[assignment]
    app.state.live_match_hub = hub
    try:
        with session_factory() as session:
            seed = _seed_phase4_fixture(session, is_knockout=False)
            match_id = seed["match"].id
            svc = CanonicalLiveExecutionService(session, hub=hub)
            svc.start_live_execution(match_id)
            svc.step_execution(match_id, target_minute=30, stop_at_halftime=False)
            res = svc.apply_live_tactical_command(
                match_id,
                side="home",
                actor_user_id=seed["home_ftm"].id,
                mentality="attacking",
                tempo=80,
                expected_revision=1,
                idempotency_key="redis-outage-tac-1",
            )
            session.commit()
            assert res["execution_revision"] == 2

        state = hub.get_state(match_id)
        assert state is not None
        assert state.is_live is True
        assert state.execution_revision == 2
        events, cursor = hub.get_events_since(match_id, 0)
        assert cursor == len(events) > 0
        assert match_id in hub.list_active_matches()
    finally:
        engine.dispose()


def test_canonical_stream_publishing_calls_match_stream_service_and_adapter_cleanly() -> None:
    _app, session_factory, engine = _build_phase4_app_and_db()
    stream_svc = MatchStreamService(redis_url=None)
    captured_envelopes: list[dict[str, object]] = []
    original_publish = stream_svc.publish_event

    def _recording_publish(match_id: str, event, *, style=None):
        envelope = original_publish(match_id, event, style=style)
        captured_envelopes.append(envelope)
        return envelope

    stream_svc.publish_event = _recording_publish  # type: ignore[method-assign]
    try:
        with session_factory() as session:
            seed = _seed_phase4_fixture(session, is_knockout=False)
            match_id = seed["match"].id
            svc = CanonicalLiveExecutionService(session, match_stream_service=stream_svc)
            svc.start_live_execution(match_id)
            svc.step_execution(match_id, target_minute=20, stop_at_halftime=False)
            session.commit()

        assert len(captured_envelopes) > 0
        sample = captured_envelopes[-1]
        assert sample["message_type"] == "match_event"
        assert sample["metadata"]["execution_revision"] == 1
        assert sample["metadata"]["commit_cursor"] is not None

        adapted = adapt_match_stream_message(match_id, sample)
        assert adapted is not None
        assert adapted["type"] == "match_event"
        assert adapted["payload"]["execution_revision"] == 1
        assert adapted["payload"]["commit_cursor"] is not None

        sanitized = sanitize_public_spectator_payload(adapted)
        assert sanitized["payload"]["execution_revision"] == 1
        assert sanitized["payload"]["commit_cursor"] is not None
    finally:
        engine.dispose()
