from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.common.enums.match_status import MatchStatus
from app.match_engine.schemas import (
    MatchEventTimelineView,
    MatchFinalSummaryView,
    MatchHighlightItemView,
    MatchHighlightListView,
    MatchLiveFeedEventView,
    MatchLiveFeedView,
    MatchMediaAvailabilityView,
    MatchReplayPayloadView,
    MatchSimulationRequest,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.replay_archive.service import ensure_replay_archive

router = APIRouter(tags=["match-engine"])
legacy_router = APIRouter(prefix="/match-engine")
api_router = APIRouter(prefix="/api/match-engine")


def get_match_simulation_service() -> MatchSimulationService:
    return MatchSimulationService()


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


@legacy_router.post("/replay", response_model=MatchReplayPayloadView)
@api_router.post("/replay", response_model=MatchReplayPayloadView)
def create_match_replay(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchReplayPayloadView:
    return service.build_replay_payload(payload)


@legacy_router.post("/timeline", response_model=MatchEventTimelineView)
@api_router.post("/timeline", response_model=MatchEventTimelineView)
def create_match_timeline(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchEventTimelineView:
    return service.build_timeline(payload)


@legacy_router.post("/summary", response_model=MatchFinalSummaryView)
@api_router.post("/summary", response_model=MatchFinalSummaryView)
def create_match_summary(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchFinalSummaryView:
    return service.build_summary(payload)


@legacy_router.get("/live-feed/{match_key}", response_model=MatchLiveFeedView)
@api_router.get("/live-feed/{match_key}", response_model=MatchLiveFeedView)
def read_match_live_feed(match_key: str, request: Request) -> MatchLiveFeedView:
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


@legacy_router.get("/highlights/{match_key}", response_model=MatchHighlightListView)
@api_router.get("/highlights/{match_key}", response_model=MatchHighlightListView)
def read_match_highlights(match_key: str, request: Request) -> MatchHighlightListView:
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

    archive_available = True
    highlights = [_map_highlight(event, archive_available=archive_available) for event in record.timeline]
    return MatchHighlightListView(
        match_id=match_key,
        highlights=highlights,
        replay_available=True,
        archive_available=archive_available,
        download_available=False,
    )


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_match_simulation_service", "router"]
