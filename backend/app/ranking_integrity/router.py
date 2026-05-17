from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.schemas.club_ranking_integrity import (
    ClubRankingAbuseFlagView,
    ClubRankingAbuseFlagsResponse,
    ClubRankingEventView,
    ClubRankingEventsResponse,
)
from app.services.club_ranking_integrity_service import ClubRankingIntegrityService

router = APIRouter(tags=["ranking-integrity"])


def _service(session: Session = Depends(get_session)) -> ClubRankingIntegrityService:
    return ClubRankingIntegrityService(session)


def _event_view(event) -> ClubRankingEventView:
    return ClubRankingEventView(
        id=event.id,
        event_key=event.event_key,
        event_kind=event.event_kind,
        club_id=event.club_id,
        competition_id=event.competition_id,
        match_id=event.match_id,
        opponent_club_id=event.opponent_club_id,
        result=event.result,
        base_points=event.base_points,
        opponent_strength_multiplier=event.opponent_strength_multiplier,
        competition_size_multiplier=event.competition_size_multiplier,
        competition_tier_multiplier=event.competition_tier_multiplier,
        stage_multiplier=event.stage_multiplier,
        anti_farm_multiplier=event.anti_farm_multiplier,
        placement_bonus=event.placement_bonus,
        raw_points_delta=event.raw_points_delta,
        final_points_delta=event.final_points_delta,
        integrity_status=event.integrity_status,
        reason=event.reason,
        metadata_json=event.metadata_json,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _flag_view(flag) -> ClubRankingAbuseFlagView:
    return ClubRankingAbuseFlagView(
        id=flag.id,
        flag_key=flag.flag_key,
        club_id=flag.club_id,
        user_id=flag.user_id,
        competition_id=flag.competition_id,
        match_id=flag.match_id,
        flag_type=flag.flag_type,
        severity=flag.severity,
        description=flag.description,
        status=flag.status,
        reviewed_at=flag.reviewed_at,
        metadata_json=flag.metadata_json,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@router.get("/api/clubs/{club_id}/ranking-events", response_model=ClubRankingEventsResponse)
def list_club_ranking_events(
    club_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: ClubRankingIntegrityService = Depends(_service),
) -> ClubRankingEventsResponse:
    return ClubRankingEventsResponse(
        events=tuple(_event_view(event) for event in service.list_events_for_club(club_id, limit=limit))
    )


@router.get("/api/admin/ranking/events", response_model=ClubRankingEventsResponse)
def list_admin_ranking_events(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    _: User = Depends(get_current_admin),
    service: ClubRankingIntegrityService = Depends(_service),
) -> ClubRankingEventsResponse:
    return ClubRankingEventsResponse(
        events=tuple(_event_view(event) for event in service.list_events(limit=limit, status=status))
    )


@router.get("/api/admin/ranking/flags", response_model=ClubRankingAbuseFlagsResponse)
def list_admin_ranking_flags(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    _: User = Depends(get_current_admin),
    service: ClubRankingIntegrityService = Depends(_service),
) -> ClubRankingAbuseFlagsResponse:
    return ClubRankingAbuseFlagsResponse(
        flags=tuple(_flag_view(flag) for flag in service.list_flags(limit=limit, status=status))
    )
