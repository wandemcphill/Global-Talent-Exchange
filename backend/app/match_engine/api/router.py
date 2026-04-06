from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.cache import HotPathCache
from app.common.enums.match_status import MatchStatus
from app.core.config import Settings, get_settings
from app.db import get_session
from app.fairness.fairness_guard import FairnessGuard, FairnessViolation
from app.highlights.service import HighlightGenerationService
from app.match_engine.schemas import (
    MatchEventTimelineView,
    MatchFinalSummaryView,
    MatchHighlightItemView,
    MatchHighlightListView,
    MatchLiveFeedEventView,
    MatchLiveFeedView,
    MatchMediaAvailabilityView,
    MatchPostMatchAnalyticsView,
    MatchReplayPayloadView,
    MatchRenderSyncPayloadView,
    MatchSimulationRequest,
    MatchSimulationResponseView,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.highlight_manifest import MatchHighlightManifestBuilder
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.replay_archive.service import ensure_replay_archive
from app.services.ads.engine import AdDecisionEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["match-engine"])
legacy_router = APIRouter(prefix="/match-engine")
api_router = APIRouter(prefix="/api/match-engine")


def get_match_simulation_service() -> MatchSimulationService:
    return MatchSimulationService()


def get_fairness_guard() -> FairnessGuard:
    return FairnessGuard()


def _settings_from_request(request: Request) -> Settings:
    state_settings = getattr(request.app.state, "settings", None)
    return state_settings if isinstance(state_settings, Settings) else get_settings()


def _highlight_generation_service(request: Request) -> HighlightGenerationService:
    existing = getattr(request.app.state, "highlight_generation_service", None)
    if isinstance(existing, HighlightGenerationService):
        return existing
    settings = _settings_from_request(request)
    return HighlightGenerationService(settings=settings)


def get_ad_decision_engine() -> AdDecisionEngine:
    return AdDecisionEngine()


def _resolve_status_from_record(record) -> MatchStatus:
    if record.live:
        return MatchStatus.IN_PROGRESS
    if record.final_whistle_at is not None:
        return MatchStatus.COMPLETED
    if record.started_at is not None:
        return MatchStatus.IN_PROGRESS
    return MatchStatus.SCHEDULED


def _resolve_status_from_countdown(countdown) -> MatchStatus:
    state = getattr(countdown, "state", "scheduled")
    if state == "live":
        return MatchStatus.IN_PROGRESS
    if state == "complete":
        return MatchStatus.COMPLETED
    return MatchStatus.SCHEDULED


def _resolve_phase(status: MatchStatus) -> str:
    if status is MatchStatus.SCHEDULED:
        return "scheduled"
    if status is MatchStatus.IN_PROGRESS:
        return "live"
    if status is MatchStatus.COMPLETED:
        return "fulltime"
    if status is MatchStatus.PAUSED:
        return "paused"
    return getattr(status, "value", str(status))


def _resolve_minute_from_record(record, status: MatchStatus) -> int | None:
    if record.timeline:
        return max(event.minute for event in record.timeline)
    if status is MatchStatus.COMPLETED:
        return 90
    if status is MatchStatus.IN_PROGRESS:
        return 0
    return None


def _resolve_minute_from_countdown(countdown) -> int | None:
    state = getattr(countdown, "state", "scheduled")
    if state == "live":
        return max(0, int((-countdown.seconds_until_start) // 60))
    if state == "complete":
        return 90
    return None


def _map_live_event(event) -> MatchLiveFeedEventView:
    return MatchLiveFeedEventView(
        event_id=event.event_id,
        minute=event.minute,
        event_type=event.event_type,
        team_id=event.club_id,
        team_name=event.club_name,
        player_name=event.player_name,
        secondary_player_name=event.secondary_player_name,
        description=event.description,
        home_score=event.home_score,
        away_score=event.away_score,
        is_penalty=event.is_penalty,
    )


def _highlight_title(event) -> str:
    mapping = {
        "goals": "Goal",
        "assists": "Assist",
        "missed_chances": "Chance",
        "yellow_cards": "Yellow card",
        "red_cards": "Red card",
        "substitutions": "Substitution",
        "injuries": "Injury",
        "penalties": "Penalty",
    }
    base = mapping.get(event.event_type, "Highlight")
    if event.player_name:
        return f"{base}: {event.player_name}"
    if event.club_name:
        return f"{base}: {event.club_name}"
    return base


def _highlight_label(event) -> str | None:
    if event.club_name and event.player_name:
        return f"{event.club_name} - {event.player_name}"
    if event.club_name:
        return event.club_name
    if event.player_name:
        return event.player_name
    return None


def _map_highlight(event, *, archive_available: bool) -> MatchHighlightItemView:
    return MatchHighlightItemView(
        highlight_id=event.event_id,
        title=_highlight_title(event),
        label=_highlight_label(event),
        minute=event.minute,
        event_type=event.event_type,
        team_name=event.club_name,
        player_name=event.player_name,
        access_state="available" if archive_available else "unavailable",
        archive_available=archive_available,
        download_available=False,
    )


def _build_availability(record, timeline_events: list[MatchLiveFeedEventView]) -> MatchMediaAvailabilityView:
    replay_available = record is not None
    highlights_available = bool(timeline_events)
    return MatchMediaAvailabilityView(
        halftime_analytics_available=False,
        key_moments_available=highlights_available,
        highlights_available=highlights_available,
        replay_available=replay_available,
        archive_available=replay_available,
        download_available=False,
    )


def _load_stored_replay_payload(match_key: str, session: Session) -> MatchReplayPayloadView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        payload = (match.metadata_json or {}).get("replay_payload")
        if isinstance(payload, dict):
            return MatchReplayPayloadView.model_validate(payload)

    duel = session.get(ManagerDuel, match_key)
    if duel is not None:
        payload = (duel.metadata_json or {}).get("replay_payload")
        if isinstance(payload, dict):
            return MatchReplayPayloadView.model_validate(payload)

    raise HTTPException(status_code=404, detail=f"Replay payload for {match_key} was not found.")


def _timeline_position(render_event) -> tuple[float, float]:
    if render_event is not None and render_event.position is not None:
        return float(render_event.position.x), float(render_event.position.y)
    if render_event is not None and render_event.target_position is not None:
        return float(render_event.target_position.x), float(render_event.target_position.y)
    return 50.0, 50.0


def _build_simulation_response(replay_payload: MatchReplayPayloadView) -> MatchSimulationResponseView:
    render_sync_by_event_id = {
        item.event_id: item
        for item in (replay_payload.render_sync.events if replay_payload.render_sync is not None else [])
    }
    timeline_events = []
    for event in replay_payload.timeline.events:
        position_x, position_y = _timeline_position(render_sync_by_event_id.get(event.event_id))
        timeline_events.append(
            {
                "minute": event.minute,
                "type": getattr(event.event_type, "value", str(event.event_type)),
                "player": None if event.primary_player is None else event.primary_player.player_name,
                "team": event.team_name,
                "position_x": round(position_x, 3),
                "position_y": round(position_y, 3),
            }
        )
    return MatchSimulationResponseView(
        match_id=replay_payload.match_id,
        timeline_events=timeline_events,
        score={
            "home": replay_payload.summary.home_score,
            "away": replay_payload.summary.away_score,
        },
        stats={
            "home": replay_payload.summary.home_stats.model_dump(mode="json"),
            "away": replay_payload.summary.away_stats.model_dump(mode="json"),
        },
    )


@legacy_router.post("/replay", response_model=MatchReplayPayloadView)
@api_router.post("/replay", response_model=MatchReplayPayloadView)
def create_match_replay(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchReplayPayloadView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    return service.build_replay_payload(payload)


@legacy_router.post("/simulate", response_model=MatchSimulationResponseView)
@api_router.post("/simulate", response_model=MatchSimulationResponseView)
def simulate_match(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchSimulationResponseView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    try:
        replay_payload = service.build_replay_payload(payload)
        return _build_simulation_response(replay_payload)
    except Exception as exc:
        logger.exception("Failed to build Unity simulation payload for match %s", payload.match_id)
        raise HTTPException(status_code=503, detail="Match simulation is temporarily unavailable.") from exc


@legacy_router.post("/timeline", response_model=MatchEventTimelineView)
@api_router.post("/timeline", response_model=MatchEventTimelineView)
def create_match_timeline(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchEventTimelineView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    return service.build_timeline(payload)


@legacy_router.post("/summary", response_model=MatchFinalSummaryView)
@api_router.post("/summary", response_model=MatchFinalSummaryView)
def create_match_summary(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchFinalSummaryView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    return service.build_summary(payload)


@legacy_router.post("/render-sync", response_model=MatchRenderSyncPayloadView)
@api_router.post("/render-sync", response_model=MatchRenderSyncPayloadView)
def create_match_render_sync(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchRenderSyncPayloadView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    replay_payload = service.build_replay_payload(payload)
    if replay_payload.render_sync is None:
        raise HTTPException(status_code=500, detail="Render sync contract could not be built.")
    return replay_payload.render_sync


@legacy_router.post("/analytics", response_model=MatchPostMatchAnalyticsView)
@api_router.post("/analytics", response_model=MatchPostMatchAnalyticsView)
def create_post_match_analytics(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
    fairness_guard: FairnessGuard = Depends(get_fairness_guard),
) -> MatchPostMatchAnalyticsView:
    try:
        fairness_guard.validate_public_request(payload)
    except FairnessViolation as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    replay_payload = service.build_replay_payload(payload)
    if replay_payload.post_match_analytics is None:
        raise HTTPException(status_code=500, detail="Post-match analytics could not be built.")
    return replay_payload.post_match_analytics


@legacy_router.get("/render-sync/{match_key}", response_model=MatchRenderSyncPayloadView)
@api_router.get("/render-sync/{match_key}", response_model=MatchRenderSyncPayloadView)
def read_match_render_sync(
    match_key: str,
    session: Session = Depends(get_session),
) -> MatchRenderSyncPayloadView:
    payload = _load_stored_replay_payload(match_key, session)
    if payload.render_sync is None:
        raise HTTPException(status_code=404, detail=f"Render sync payload for {match_key} was not found.")
    return payload.render_sync


@legacy_router.get("/analytics/{match_key}", response_model=MatchPostMatchAnalyticsView)
@api_router.get("/analytics/{match_key}", response_model=MatchPostMatchAnalyticsView)
def read_post_match_analytics(
    match_key: str,
    session: Session = Depends(get_session),
) -> MatchPostMatchAnalyticsView:
    payload = _load_stored_replay_payload(match_key, session)
    if payload.post_match_analytics is None:
        raise HTTPException(status_code=404, detail=f"Post-match analytics for {match_key} was not found.")
    return payload.post_match_analytics


@legacy_router.get("/live-feed/{match_key}", response_model=MatchLiveFeedView)
@api_router.get("/live-feed/{match_key}", response_model=MatchLiveFeedView)
def read_match_live_feed(match_key: str, request: Request) -> MatchLiveFeedView:
    cached_feed = _read_cached_live_feed(request, match_key)
    if cached_feed is not None:
        return cached_feed

    archive = ensure_replay_archive(request.app)
    record = archive.repository.get_latest_record(f"replay:{match_key}")
    countdown = None
    if record is None:
        countdown = archive.repository.get_countdown(match_key)
        if countdown is None:
            raise HTTPException(status_code=404, detail=f"Match {match_key} was not found.")

    if record is not None:
        status = _resolve_status_from_record(record)
        timeline_events = [_map_live_event(event) for event in record.timeline]
        return MatchLiveFeedView(
            match_id=match_key,
            home_team_name=record.home_club.club_name,
            away_team_name=record.away_club.club_name,
            home_score=record.scoreline.home_goals,
            away_score=record.scoreline.away_goals,
            status=status,
            minute=_resolve_minute_from_record(record, status),
            phase=_resolve_phase(status),
            timeline_events=timeline_events,
            availability=_build_availability(record, timeline_events),
        )

    status = _resolve_status_from_countdown(countdown)
    timeline_events: list[MatchLiveFeedEventView] = []
    return MatchLiveFeedView(
        match_id=match_key,
        home_team_name=countdown.home_club.club_name,
        away_team_name=countdown.away_club.club_name,
        home_score=0,
        away_score=0,
        status=status,
        minute=_resolve_minute_from_countdown(countdown),
        phase=_resolve_phase(status),
        timeline_events=timeline_events,
        availability=_build_availability(record, timeline_events),
    )


def _read_cached_live_feed(request: Request, match_key: str) -> MatchLiveFeedView | None:
    cache_backend = getattr(request.app.state, "cache_backend", None)
    if cache_backend is None:
        return None

    hot_cache = HotPathCache(cache_backend)
    state = hot_cache.get_match_state(match_key)
    if not isinstance(state, dict):
        return None

    events = hot_cache.get_match_events(match_key)
    timeline_events = []
    for item in events:
        if not isinstance(item, dict):
            continue
        timeline_events.append(
            MatchLiveFeedEventView(
                event_id=str(item.get("event_id") or ""),
                minute=int(item.get("minute") or 0),
                event_type=str(item.get("event_type") or ""),
                team_id=item.get("team_id"),
                team_name=item.get("team"),
                player_name=item.get("player"),
                secondary_player_name=item.get("secondary_player"),
                description=item.get("commentary"),
                home_score=int(item.get("home_score") or 0),
                away_score=int(item.get("away_score") or 0),
                is_penalty=bool(item.get("is_penalty")),
            )
        )
    snapshot = state.get("snapshot") if isinstance(state.get("snapshot"), dict) else {}
    score = snapshot.get("score") if isinstance(snapshot.get("score"), dict) else {}
    status_raw = str(snapshot.get("status") or "in_progress").strip().lower()
    status = MatchStatus.COMPLETED if status_raw == "completed" else MatchStatus.IN_PROGRESS
    return MatchLiveFeedView(
        match_id=str(state.get("match_id") or match_key),
        home_team_name=str(state.get("home_team_name") or _resolve_cached_team_name(events, key="home_team_name", fallback="Home Club")),
        away_team_name=str(state.get("away_team_name") or _resolve_cached_team_name(events, key="away_team_name", fallback="Away Club")),
        home_score=int(score.get("home") or 0),
        away_score=int(score.get("away") or 0),
        status=status,
        minute=int(snapshot.get("current_minute") or 0),
        phase=_phase_from_cached_status(status=status, minute=int(snapshot.get("current_minute") or 0)),
        timeline_events=timeline_events,
        availability=MatchMediaAvailabilityView(
            halftime_analytics_available=False,
            key_moments_available=bool(timeline_events),
            highlights_available=bool(timeline_events),
            replay_available=status is MatchStatus.COMPLETED,
            archive_available=status is MatchStatus.COMPLETED,
            download_available=False,
        ),
    )


def _resolve_cached_team_name(
    events: list[dict[str, object]],
    *,
    key: str,
    fallback: str,
) -> str:
    for item in events:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


def _phase_from_cached_status(*, status: MatchStatus, minute: int) -> str:
    if status is MatchStatus.COMPLETED:
        return "full_time"
    if minute == 45:
        return "halftime"
    if minute >= 46:
        return "second_half"
    return "first_half"


@legacy_router.get("/highlights/{match_key}", response_model=MatchHighlightListView)
@api_router.get("/highlights/{match_key}", response_model=MatchHighlightListView)
def read_match_highlights(
    match_key: str,
    request: Request,
    session: Session = Depends(get_session),
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
) -> MatchHighlightListView:
    manifest_builder = MatchHighlightManifestBuilder(settings=_settings_from_request(request))
    generation_service = _highlight_generation_service(request)
    match = session.get(CompetitionMatch, match_key)
    match_metadata = match.metadata_json if match is not None and isinstance(match.metadata_json, dict) else {}
    ad_profile = match_metadata.get("ad_profile") if isinstance(match_metadata.get("ad_profile"), dict) else None
    try:
        payload = _load_stored_replay_payload(match_key, session)
    except HTTPException:
        payload = None
    if payload is not None:
        manifest = ad_engine.attach_highlight_ads(
            manifest_builder.build_from_replay_payload(payload),
            ad_profile=ad_profile,
            match_context={
                "home_team_name": payload.visual_identity.home_team.team_name if payload.visual_identity is not None else "",
                "away_team_name": payload.visual_identity.away_team.team_name if payload.visual_identity is not None else "",
                "competition_name": (
                    f"{payload.visual_identity.home_team.team_name} vs {payload.visual_identity.away_team.team_name}"
                    if payload.visual_identity is not None
                    else match_key
                ),
            },
        )
        return generation_service.prepare_manifest(manifest)

    archive = ensure_replay_archive(request.app)
    record = archive.repository.get_latest_record(f"replay:{match_key}")
    if record is None:
        countdown = archive.repository.get_countdown(match_key)
        if countdown is None:
            raise HTTPException(status_code=404, detail=f"Match {match_key} was not found.")
        return MatchHighlightListView(
            match_id=match_key,
            highlights=[],
            replay_available=False,
            archive_available=False,
            download_available=False,
        )

    manifest = ad_engine.attach_highlight_ads(
        manifest_builder.build_from_archive_record(match_key, record),
        ad_profile=ad_profile,
        match_context={
            "home_team_name": record.home_club.club_name,
            "away_team_name": record.away_club.club_name,
            "competition_name": record.competition_context.competition_label,
        },
    )
    return generation_service.prepare_manifest(manifest)


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_ad_decision_engine", "get_match_simulation_service", "router"]
