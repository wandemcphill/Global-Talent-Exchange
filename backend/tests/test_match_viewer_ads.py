from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.highlights.service import HighlightGenerationService
from app.match_engine.api.router import router as match_engine_router
from app.match_engine.services.highlight_manifest import MatchHighlightManifestBuilder
from app.models.base import Base
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.routes.match_viewer import router as match_viewer_router
from app.schemas.match_viewer import MatchViewerEventType
from app.services.ads.engine import AdDecisionEngine
from app.services.ads.injector import build_overlay_command
from app.services.ads.schemas import MatchAdPlacementType
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request
from app.match_engine.services.match_simulation_service import MatchSimulationService


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(match_viewer_router)
    app.include_router(match_viewer_router, prefix="/api")
    app.include_router(match_engine_router)
    app.state.highlight_generation_service = _PassthroughHighlightGenerationService()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[UserCompetition.__table__, CompetitionMatch.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return app, session_factory


class _PassthroughHighlightGenerationService(HighlightGenerationService):
    def __init__(self) -> None:
        pass

    def prepare_manifest(self, manifest):  # type: ignore[override]
        return manifest


def _insert_match(
    session_factory: sessionmaker[Session],
    *,
    match_id: str,
    metadata_json: dict[str, object],
) -> None:
    with session_factory() as session:
        session.add(
            UserCompetition(
                id="competition-1",
                host_user_id="host-user-1",
                name="Creator Match Night",
                format="league",
                currency="coin",
                metadata_json={},
            )
        )
        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id="home",
                away_club_id="away",
                metadata_json=metadata_json,
            )
        )
        session.commit()


def _payload_with_goal():
    simulation = MatchSimulationService()
    timeline = MatchTimelineService()
    for seed in range(1, 80):
        payload = simulation.build_replay_payload(build_request(seed=seed))
        view_state = timeline.build_from_replay_payload(payload)
        if any(event.event_type is MatchViewerEventType.GOAL for event in view_state.events):
            return payload, view_state
    raise AssertionError("Expected at least one replay payload with a goal event.")


def test_select_ad_prefers_goal_sponsorship_before_rewarded_offer() -> None:
    engine = AdDecisionEngine()

    placement = engine.select_ad(
        {"country": "NG", "coins": 10},
        {"home_team_name": "Lagos Stars", "away_team_name": "Abuja City"},
        {"event_id": "goal-1", "event_type": "goal"},
    )

    assert placement is not None
    assert placement["type"] == MatchAdPlacementType.SPONSORED_HIGHLIGHT.value
    assert placement["brand"] in {"MTN", "BetKing", "KoraPay"}
    assert "powered by" in placement["message"].lower()


def test_match_viewer_route_exposes_ad_placements_for_standard_profiles() -> None:
    app, session_factory = _build_app()
    payload, view_state = _payload_with_goal()
    _insert_match(
        session_factory,
        match_id=payload.match_id,
        metadata_json={
            "match_viewer": view_state.model_dump(mode="json"),
            "ad_profile": {"country": "NG", "coins": 12},
        },
    )

    with TestClient(app) as client:
        response = client.get(f"/api/match-viewer/{payload.match_id}")

    assert response.status_code == 200
    monetization = response.json()["monetization"]
    assert monetization["ads_enabled"] is True
    placement_types = {item["ad_type"] for item in monetization["placements"]}
    assert placement_types == {
        MatchAdPlacementType.SPONSORED_HIGHLIGHT.value,
        MatchAdPlacementType.PRE_ROLL.value,
        MatchAdPlacementType.LIVE_BANNER.value,
        MatchAdPlacementType.REWARDED_AD.value,
    }
    sponsored = next(
        item
        for item in monetization["placements"]
        if item["ad_type"] == MatchAdPlacementType.SPONSORED_HIGHLIGHT.value
    )
    visible_event_ids = {event["event_id"] for event in response.json()["events"]}
    assert sponsored["event_id"] in visible_event_ids


def test_match_viewer_route_hides_ads_for_premium_profiles() -> None:
    app, session_factory = _build_app()
    payload, view_state = _payload_with_goal()
    _insert_match(
        session_factory,
        match_id=payload.match_id,
        metadata_json={
            "match_viewer": view_state.model_dump(mode="json"),
            "ad_profile": {"country": "NG", "coins": 12, "is_premium_user": True},
        },
    )

    with TestClient(app) as client:
        response = client.get(f"/api/match-viewer/{payload.match_id}")

    assert response.status_code == 200
    monetization = response.json()["monetization"]
    assert monetization["ads_enabled"] is False
    assert monetization["premium_ad_free"] is True
    assert monetization["placements"] == []


def test_match_highlights_surface_sponsored_goal_clips() -> None:
    class _StubSettings:
        highlight_temp_prefix = "highlights/tmp"
        highlight_archive_prefix = "highlights/archive"
        cdn_base_url = "https://cdn.gtex.test"

    payload, _view_state = _payload_with_goal()
    manifest = MatchHighlightManifestBuilder(settings=_StubSettings()).build_from_replay_payload(payload)
    body = AdDecisionEngine().attach_highlight_ads(
        manifest,
        ad_profile={"country": "NG", "coins": 8},
        match_context={
            "home_team_name": payload.visual_identity.home_team.team_name if payload.visual_identity is not None else "",
            "away_team_name": payload.visual_identity.away_team.team_name if payload.visual_identity is not None else "",
            "competition_name": (
                f"{payload.visual_identity.home_team.team_name} vs {payload.visual_identity.away_team.team_name}"
                if payload.visual_identity is not None
                else payload.match_id
            ),
        },
    ).model_dump(mode="json")

    sponsored_clips = [
        item
        for item in body["highlights"]
        if item["event_type"] in {"goals", "penalties"} and item["ad_placement"] is not None
    ]
    assert sponsored_clips
    assert all(
        item["ad_placement"]["ad_type"] == MatchAdPlacementType.SPONSORED_HIGHLIGHT.value
        for item in sponsored_clips
    )
    assert any(
        placement["ad_type"] == MatchAdPlacementType.PRE_ROLL.value
        for placement in body["monetization"]["placements"]
    )


def test_overlay_injector_builds_drawtext_command_without_running_ffmpeg() -> None:
    command = build_overlay_command(
        "input.mp4",
        "Goal of the Match powered by MTN",
        output_path="sponsored.mp4",
    )

    assert command[0] == "ffmpeg"
    assert "drawtext" in command[5]
    assert command[-1].endswith("sponsored.mp4")
