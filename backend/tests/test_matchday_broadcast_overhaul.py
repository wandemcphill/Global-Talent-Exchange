from __future__ import annotations

import importlib
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_match_user, get_current_user
from app.db import get_session
from app.live_match.router import router as live_match_router
from app.live_match.service import LiveMatchEngine, LiveMatchStore
from app.live_matches.highlights import SmartHighlightService
from app.live_matches.router import api_router as live_matches_api_router, legacy_router as live_matches_legacy_router
from app.live_matches.service import LiveMatchHub
from app.match_engine.schemas import MatchCompetitionContextInput
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType
from app.match_engine.simulation.offside_var import (
    MatchBroadcastCategory,
    build_universal_broadcast_session,
    evaluate_law11_offside,
    evaluate_var_review_2026_27,
    resolve_assigned_broadcast_duration,
    resolve_match_broadcast_category,
)
from app.models.base import Base
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.user import User
from app.routes.match_viewer import router as match_viewer_router
from app.schemas.match_viewer import MatchMode
from app.services.match_timeline_service import MatchTimelineService
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from backend.tests.match_engine.helpers import build_request, build_team


def test_universal_broadcast_category_resolution_and_duration_caps() -> None:
    assert resolve_match_broadcast_category(stage="league", competition_type="league") == (
        MatchBroadcastCategory.ORDINARY_LEAGUE
    )
    assert resolve_match_broadcast_category(stage="Group Stage", competition_type="cup") == (
        MatchBroadcastCategory.GROUP_STAGE
    )
    assert (
        resolve_match_broadcast_category(
            stage="league",
            approved_shorter_presentation=True,
        )
        == MatchBroadcastCategory.APPROVED_SHORTER_PRESENTATION
    )
    assert (
        resolve_match_broadcast_category(
            stage="Quarter-Final",
            competition_type="cup",
            is_final=False,
            metadata={"designated_major_knockout": True},
        )
        == MatchBroadcastCategory.MAJOR_KNOCKOUT
    )
    assert resolve_match_broadcast_category(stage="Semi-Final", competition_type="cup") == (
        MatchBroadcastCategory.SEMI_FINAL
    )
    assert resolve_match_broadcast_category(stage="Final", is_final=True) == MatchBroadcastCategory.FINAL

    ordinary_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.ORDINARY_LEAGUE,
        event_count=80,
        high_impact_count=20,
        var_review_count=4,
    )
    group_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.GROUP_STAGE,
        event_count=65,
        high_impact_count=12,
        var_review_count=2,
    )
    shorter_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.APPROVED_SHORTER_PRESENTATION,
        event_count=70,
        high_impact_count=15,
        var_review_count=3,
    )
    knockout_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.MAJOR_KNOCKOUT,
        event_count=90,
        high_impact_count=24,
        var_review_count=5,
    )
    semi_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.SEMI_FINAL,
        event_count=85,
        high_impact_count=18,
        var_review_count=4,
    )
    final_dur = resolve_assigned_broadcast_duration(
        MatchBroadcastCategory.FINAL,
        event_count=95,
        high_impact_count=25,
        var_review_count=5,
    )

    assert 480 <= ordinary_dur <= 600
    assert 480 <= group_dur <= 600
    assert 180 <= shorter_dur <= 420
    assert 600 <= knockout_dur <= 900
    assert 600 <= semi_dur <= 900
    assert 600 <= final_dur <= 900

    session_view = build_universal_broadcast_session(
        match_id="match-cat-1",
        category=MatchBroadcastCategory.ORDINARY_LEAGUE,
        assigned_duration_seconds=ordinary_dur,
        server_start_timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        current_position_seconds=120.5,
        broadcast_status="live",
        events=[{"event_id": "e1", "minute": 10}],
    )
    assert session_view["assigned_duration_seconds"] == ordinary_dur
    assert session_view["match_id"] == "match-cat-1"
    assert session_view["broadcast_status"] == "live"
    assert len(session_view["ordered_presentation_events"]) == 1


def test_law_11_offside_body_part_exclusion_deliberate_play_and_gk_throw() -> None:
    defenders = [
        {
            "player_id": "gk",
            "player_name": "Keeper",
            "x": 96.0,
            "y": 50.0,
            "role": "goalkeeper",
            "body_part": "foot",
            "lean_offset_x": 0.3,
        },
        {
            "player_id": "cb",
            "player_name": "Stopper",
            "x": 78.0,
            "y": 48.0,
            "role": "defender",
            "body_part": "foot",
            "lean_offset_x": 0.4,
        },
    ]

    # Hand/arm ahead of second-last opponent when playable torso/foot is level (78.0 + 0.4 == 78.4) is NOT offside (Law 11)
    arm_only = evaluate_law11_offside(
        pass_contact_second=120.0,
        attacking_direction=1,
        ball_x=70.0,
        ball_y=50.0,
        attacker_id="att-1",
        attacker_name="Striker One",
        attacker_x=78.0,
        attacker_y=45.0,
        attacker_body_part="hand",
        attacker_lean_offset_x=0.35,
        opponents=defenders,
        passer_id="mid-1",
        passer_name="Creator",
    )
    assert arm_only.attacker_body_part == "torso"
    assert arm_only.is_offside_position is False
    assert arm_only.is_penalised is False

    # Active head lean ahead of second-last opponent IS offside and penalised
    head_offside = evaluate_law11_offside(
        pass_contact_second=121.0,
        attacking_direction=1,
        ball_x=70.0,
        ball_y=50.0,
        attacker_id="att-1",
        attacker_name="Striker One",
        attacker_x=79.5,
        attacker_y=45.0,
        attacker_body_part="head",
        attacker_lean_offset_x=0.6,
        opponents=defenders,
        active_involvement=True,
    )
    assert head_offside.is_offside_position is True
    assert head_offside.is_penalised is True
    assert head_offside.offside_line_x < head_offside.attacker_line_x

    # Passive offside position (no active involvement) is NOT penalised
    passive = evaluate_law11_offside(
        pass_contact_second=122.0,
        attacking_direction=1,
        ball_x=70.0,
        ball_y=50.0,
        attacker_id="att-2",
        attacker_name="Winger",
        attacker_x=82.0,
        attacker_y=12.0,
        attacker_body_part="foot",
        opponents=defenders,
        active_involvement=False,
        involvement_type="non_interfering",
    )
    assert passive.is_offside_position is True
    assert passive.is_penalised is False

    # Deliberate play by defender resets offside phase; GK deliberate save does not
    deliberate_play = evaluate_law11_offside(
        pass_contact_second=123.0,
        attacking_direction=1,
        ball_x=70.0,
        ball_y=50.0,
        attacker_id="att-1",
        attacker_name="Striker One",
        attacker_x=81.0,
        attacker_y=50.0,
        attacker_body_part="torso",
        opponents=defenders,
        deliberate_play_by_defender=True,
    )
    assert deliberate_play.is_offside_position is True
    assert deliberate_play.is_penalised is False

    gk_save = evaluate_law11_offside(
        pass_contact_second=124.0,
        attacking_direction=1,
        ball_x=70.0,
        ball_y=50.0,
        attacker_id="att-1",
        attacker_name="Striker One",
        attacker_x=81.0,
        attacker_y=50.0,
        attacker_body_part="foot",
        opponents=defenders,
        deflection_or_save="save",
    )
    assert gk_save.is_offside_position is True
    assert gk_save.is_penalised is True

    # Law 11 restart exception: corner/goal_kick/throw_in and GK throw distribution exception
    gk_throw = evaluate_law11_offside(
        pass_contact_second=125.0,
        attacking_direction=1,
        ball_x=25.0,
        ball_y=50.0,
        attacker_id="att-1",
        attacker_name="Striker One",
        attacker_x=83.0,
        attacker_y=50.0,
        attacker_body_part="foot",
        opponents=defenders,
        restart_context="gk_throw",
    )
    assert gk_throw.goalkeeper_throw_exception is True
    assert gk_throw.is_penalised is False


def test_ifab_2026_27_var_protocol_all_five_categories_and_authority() -> None:
    # Category 1: goal_no_goal formal OFR overturns goal
    goal_review = evaluate_var_review_2026_27(
        review_id="var-goal-1",
        category="goal_no_goal",
        original_decision="goal_awarded",
        clear_and_obvious_error=True,
        reason="Attacker offside at pass contact.",
        factual_incident=True,
    )
    assert goal_review is not None
    assert goal_review.referee_final_authority is True
    assert goal_review.final_decision == "overturned"
    assert goal_review.decision_outcome == "goal_disallowed"

    # Category 2: penalty_no_penalty
    pen_review = evaluate_var_review_2026_27(
        review_id="var-pen-1",
        category="penalty_no_penalty",
        original_decision="play_on",
        clear_and_obvious_error=True,
        reason="Clear trip inside penalty area.",
    )
    assert pen_review is not None
    assert pen_review.formal_review_initiated is True
    assert pen_review.final_decision == "overturned"
    assert pen_review.decision_outcome == "penalty_awarded"

    # Category 3: red_card including clearly incorrect second yellow review (2026/27 expansion)
    second_yellow_review = evaluate_var_review_2026_27(
        review_id="var-red-2y",
        category="red_card",
        original_decision="second_yellow_red_card",
        clear_and_obvious_error=True,
        reason="No contact made; second caution clearly incorrect.",
        is_second_yellow_review=True,
        offending_player_id="p-8",
        offending_player_name="Midfielder Eight",
    )
    assert second_yellow_review is not None
    assert second_yellow_review.formal_review_initiated is True
    assert second_yellow_review.final_decision == "overturned"
    assert second_yellow_review.decision_outcome == "second_yellow_rescinded"

    # Category 4: mistaken_identity
    mistaken = evaluate_var_review_2026_27(
        review_id="var-id-1",
        category="mistaken_identity",
        original_decision="red_card_wrong_player",
        clear_and_obvious_error=True,
        reason="Card issued to wrong defender.",
        offending_player_id="p-4",
        offending_player_name="Wrong Defender",
        corrected_player_id="p-5",
        corrected_player_name="Actual Offender",
    )
    assert mistaken is not None
    assert mistaken.corrected_player_id == "p-5"
    assert mistaken.final_decision == "overturned"
    assert mistaken.decision_outcome == "card_transferred_mistaken_identity"

    # Category 5: optional corner_kick VAR only active when competition opts in & restart not delayed
    corner_disabled = evaluate_var_review_2026_27(
        review_id="var-ck-off",
        category="corner_kick",
        original_decision="corner_awarded",
        clear_and_obvious_error=True,
        reason="Deflected last off attacker.",
        competition_allows_corner_var=False,
    )
    assert corner_disabled is None

    corner_delayed = evaluate_var_review_2026_27(
        review_id="var-ck-late",
        category="corner_kick",
        original_decision="corner_awarded",
        clear_and_obvious_error=True,
        reason="Restart already taken.",
        competition_allows_corner_var=True,
        restart_already_taken_or_delayed=True,
    )
    assert corner_delayed is None

    corner_enabled = evaluate_var_review_2026_27(
        review_id="var-ck-on",
        category="corner_kick",
        original_decision="corner_awarded",
        clear_and_obvious_error=True,
        reason="Factual deflection off attacker.",
        factual_incident=True,
        competition_allows_corner_var=True,
        restart_already_taken_or_delayed=False,
    )
    assert corner_enabled is not None
    assert corner_enabled.final_decision == "overturned"
    assert corner_enabled.decision_outcome == "corner_overturned_to_goal_kick"


def test_multi_spectator_sync_and_red_card_player_remains_dismissed() -> None:
    sim = MatchSimulationService()
    found_red_card_view = None
    aggressive_home = build_team("home", "North City", 82, aggression=98, discipline=15, pressing=95)
    aggressive_away = build_team("away", "South Town", 78, aggression=98, discipline=15, pressing=95)
    for seed in range(1, 150):
        req = build_request(seed=seed, home_team=aggressive_home, away_team=aggressive_away)
        replay = sim.build_replay_payload(req)
        if not any(ev.event_type == MatchEventType.RED_CARD for ev in replay.timeline.events):
            continue
        view = MatchTimelineService().build_from_replay_payload(replay)
        red_events = [
            ev
            for ev in view.events
            if ev.event_type == MatchEventType.RED_CARD
            and not ((ev.var_review or {}).get("final_decision") == "overturned")
        ]
        if red_events:
            found_red_card_view = (replay, view, red_events[0])
            break

    assert (
        found_red_card_view is not None
    ), "Expected at least one non-rescinded red card within aggressive seeds 1..149"
    replay, view, red_event = found_red_card_view
    assert red_event.primary_player_id is not None
    dismissed_id = red_event.primary_player_id

    subsequent_frames = [frame for frame in view.frames if frame.time_seconds > red_event.time_seconds + 2.0]
    assert subsequent_frames
    for frame in subsequent_frames:
        matching = [p for p in frame.players if p.player_id == dismissed_id]
        assert matching == [] or matching[0].active is False

    # Viewer endpoints must ignore query overrides and return identical duration & ordered timeline to all spectators
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add(
            UserCompetition(
                id="comp-overhaul",
                host_user_id="host-overhaul",
                name="Overhaul League",
                format="league",
                currency="coin",
                metadata_json={},
            )
        )
        session.add(
            CompetitionMatch(
                id=replay.match_id,
                competition_id="comp-overhaul",
                round_id="round-1",
                round_number=1,
                stage="league",
                home_club_id=replay.summary.home_stats.team_id,
                away_club_id=replay.summary.away_stats.team_id,
                metadata_json={"match_viewer": view.model_dump(mode="json")},
            )
        )
        session.commit()

    def override_session():
        with SessionLocal() as session:
            yield session

    app = FastAPI()
    app.state.session_factory = SessionLocal
    app.include_router(match_viewer_router, prefix="/api")
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: User(
        id="viewer-1",
        email="viewer@example.com",
        username="viewer1",
        password_hash="x",
        is_active=True,
    )
    with TestClient(app) as client:
        s1 = client.get(
            f"/api/match-viewer/{replay.match_id}",
            params={"mode": MatchMode.QUICK.value, "target_duration_seconds": 60},
        )
        s2 = client.get(
            f"/api/match-viewer/{replay.match_id}",
            params={"mode": MatchMode.CINEMATIC.value, "target_duration_seconds": 900},
        )
        sess = client.get(f"/api/match-viewer/{replay.match_id}/session", params={"mode": MatchMode.QUICK.value})

    assert s1.status_code == 200 and s2.status_code == 200 and sess.status_code == 200
    d1, d2 = s1.json(), s2.json()
    sess_json = sess.json()
    assert d1["duration_seconds"] == d2["duration_seconds"] <= 600
    assert [e["event_id"] for e in d1["events"]] == [e["event_id"] for e in d2["events"]]
    assert sess_json["segment_end_seconds"] <= d1["duration_seconds"]
    assert d1["broadcast_session"]["assigned_duration_seconds"] == d1["duration_seconds"]
    assert sess_json["broadcast_session"]["assigned_duration_seconds"] == d1["duration_seconds"]


def test_major_knockout_category_respects_15_minute_cap_and_owner_tactics_locked() -> None:
    sim = MatchSimulationService()
    req = build_request(seed=14)
    req = req.model_copy(
        update={
            "competition": MatchCompetitionContextInput(
                competition_type="cup",
                stage="Final",
                is_final=True,
                designated_major_knockout=True,
                competition_allows_corner_var=True,
            )
        }
    )
    replay = sim.build_replay_payload(req)
    view = MatchTimelineService().build_from_replay_payload(replay)
    assert view.competition_category == "final"
    assert 600 <= view.duration_seconds <= 900

    scaled = MatchViewerScalingService().transform(view, MatchMode.QUICK)
    assert scaled.duration_seconds == view.duration_seconds
    assert scaled.broadcast_session is not None
    assert scaled.broadcast_session["assigned_duration_seconds"] == view.duration_seconds

    highlights = SmartHighlightService().persist_from_replay_payload(replay.match_id, replay)
    assert highlights
    assert [item.minute for item in highlights] == sorted(item.minute for item in highlights)
    assert any(item.type != "goal" for item in highlights)

    # Both tactics POST routes reject club owner / spectator interventions with 403 while read-only GET works
    app = FastAPI()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add(
            UserCompetition(
                id="comp-final",
                host_user_id="host-final",
                name="Final Cup",
                format="cup",
                currency="coin",
                metadata_json={},
            )
        )
        session.add(
            CompetitionMatch(
                id=replay.match_id,
                competition_id="comp-final",
                round_id="round-final",
                round_number=1,
                stage="Final",
                home_club_id=replay.summary.home_stats.team_id,
                away_club_id=replay.summary.away_stats.team_id,
                metadata_json={"match_viewer": view.model_dump(mode="json")},
            )
        )
        session.commit()

    def override_session():
        with SessionLocal() as session:
            yield session

    app.state.session_factory = SessionLocal
    hub = LiveMatchHub(session_factory=SessionLocal, step_interval_seconds=0.2)
    hub.start_stream(replay.match_id, replay, target_runtime_seconds=15.0)
    app.state.live_match_hub = hub
    live_engine = LiveMatchEngine(LiveMatchStore())
    live_engine.create(
        match_id="lm-lock-1",
        home_id="h1",
        away_id="a1",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=82,
        away_overall=78,
        home_user_id="owner-1",
        away_user_id="owner-2",
    )
    app.include_router(live_matches_api_router)
    app.include_router(live_matches_legacy_router)
    app.include_router(live_match_router)
    owner = User(id="owner-1", email="owner@example.com", username="owner", password_hash="x", is_active=True)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_match_user] = lambda: owner
    app.dependency_overrides[get_current_user] = lambda: owner

    lm_router_mod = importlib.import_module("app.live_match.router")

    app.dependency_overrides[lm_router_mod._engine] = lambda: live_engine

    with TestClient(app) as client:
        spectate_res = client.post(f"/api/matches/{replay.match_id}/spectate")
        assert spectate_res.status_code == 200
        assert spectate_res.json()["speed_modes"] == []

        get_tactics = client.get(f"/api/matches/{replay.match_id}/tactics")
        assert get_tactics.status_code == 200

        post_v2_tactics = client.post(
            f"/api/matches/{replay.match_id}/tactics",
            json={"side": "home", "formation": "4-2-3-1"},
        )
        assert post_v2_tactics.status_code == 403

        post_session_tactics = client.post(
            "/live-match/sessions/lm-lock-1/tactics",
            json={"side": "home", "mentality": "attacking"},
        )
        assert post_session_tactics.status_code == 403
