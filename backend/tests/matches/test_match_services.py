from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType as SimulationEventType
from app.matches.service import AnalysisService, MatchEventLoggerService
from app.models.match_event import MatchEvent, MatchEventTeam, MatchEventType
from backend.tests.match_engine.helpers import build_request


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MatchEvent.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _payload_with_goal() -> object:
    service = MatchSimulationService()
    for seed in range(1, 60):
        payload = service.build_replay_payload(build_request(seed=seed))
        if any(event.event_type is SimulationEventType.GOAL for event in payload.timeline.events):
            return payload
    raise AssertionError("Expected at least one replay payload with a goal in the search window.")


def test_match_event_logger_persists_replay_and_builds_summary() -> None:
    session = _build_session()
    try:
        payload = _payload_with_goal()
        insights = MatchEventLoggerService(session).persist_official_match(
            match_id=payload.match_id,
            replay_payload=payload,
        )

        stored = list(session.scalars(select(MatchEvent).where(MatchEvent.match_id == payload.match_id)).all())
        assert stored
        assert stored == sorted(stored, key=lambda item: (item.minute, item.created_at, item.sequence, item.id))
        assert any(event.type is MatchEventType.GOAL for event in insights.replay.timeline)
        assert insights.replay.summary.stats.home.total_shots + insights.replay.summary.stats.away.total_shots > 0
        assert insights.replay.summary.key_moments
    finally:
        session.close()


def test_analysis_service_surfaces_expected_problems_and_suggestions() -> None:
    session = _build_session()
    try:
        session.add_all(
            [
                MatchEvent(
                    match_id="analysis-match",
                    sequence=1,
                    minute=12,
                    event_type=MatchEventType.PASS,
                    team=MatchEventTeam.HOME,
                    player_id="home-creator",
                    metadata_json={"team_name": "Home FC", "player_name": "Home Creator", "completed": True},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=2,
                    minute=18,
                    event_type=MatchEventType.SHOT,
                    team=MatchEventTeam.HOME,
                    player_id="home-striker",
                    metadata_json={"team_name": "Home FC", "player_name": "Home Striker", "on_target": False, "outcome": "missed"},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=3,
                    minute=72,
                    event_type=MatchEventType.CHANCE_CREATED,
                    team=MatchEventTeam.AWAY,
                    player_id="away-10",
                    metadata_json={"team_name": "Away FC", "player_name": "Away Ten", "big_chance": True},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=4,
                    minute=74,
                    event_type=MatchEventType.SHOT,
                    team=MatchEventTeam.AWAY,
                    player_id="away-9",
                    metadata_json={"team_name": "Away FC", "player_name": "Away Nine", "on_target": True, "big_chance": True},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=5,
                    minute=81,
                    event_type=MatchEventType.GOAL,
                    team=MatchEventTeam.AWAY,
                    player_id="away-9",
                    metadata_json={"team_name": "Away FC", "player_name": "Away Nine"},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=6,
                    minute=84,
                    event_type=MatchEventType.CHANCE_CREATED,
                    team=MatchEventTeam.AWAY,
                    player_id="away-8",
                    metadata_json={"team_name": "Away FC", "player_name": "Away Eight", "big_chance": True},
                ),
                MatchEvent(
                    match_id="analysis-match",
                    sequence=7,
                    minute=86,
                    event_type=MatchEventType.SHOT,
                    team=MatchEventTeam.AWAY,
                    player_id="away-11",
                    metadata_json={"team_name": "Away FC", "player_name": "Away Eleven", "on_target": True},
                ),
            ]
        )
        session.commit()

        analysis = AnalysisService(session).analyze_match("analysis-match", MatchEventTeam.HOME)

        assert "Low attacking output" in analysis.problems
        assert "Defensive structure weak" in analysis.problems
        assert "Fitness issues affected performance" in analysis.problems
        assert "No tactical adjustments made" in analysis.problems
        assert "Late-game concentration drop" in analysis.problems
        assert any("attacking formation" in suggestion for suggestion in analysis.suggestions)
        assert any("Lower the defensive line" in suggestion for suggestion in analysis.suggestions)
    finally:
        session.close()
