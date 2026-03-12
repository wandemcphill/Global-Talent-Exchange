from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.club_identity.trophies.schemas import (
    HonorsTimelineView,
    SeasonHonorsArchiveView,
    SeasonHonorsRecordView,
    TrophyCabinetView,
    TrophyCategoryCountView,
    TrophyLeaderboardEntryView,
    TrophyLeaderboardView,
    TrophySeasonCountView,
    TrophyWinView,
)
from backend.app.club_identity.trophies.service import ClubHonorsNotFoundError, TrophyCabinetService

router = APIRouter(tags=["club-identity-trophies"])


def get_trophy_cabinet_service() -> TrophyCabinetService:
    return TrophyCabinetService()


@router.get("/api/clubs/{club_id}/trophy-cabinet", response_model=TrophyCabinetView)
def get_trophy_cabinet(
    club_id: str,
    team_scope: str | None = Query(default=None),
    recent_limit: int = Query(default=5, ge=1, le=20),
    service: TrophyCabinetService = Depends(get_trophy_cabinet_service),
) -> TrophyCabinetView:
    try:
        cabinet = service.get_trophy_cabinet(
            club_id,
            team_scope=team_scope,
            recent_limit=recent_limit,
        )
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TrophyCabinetView(
        club_id=cabinet.club_id,
        club_name=cabinet.club_name,
        total_honors_count=cabinet.total_honors_count,
        major_honors_count=cabinet.major_honors_count,
        elite_honors_count=cabinet.elite_honors_count,
        senior_honors_count=cabinet.senior_honors_count,
        academy_honors_count=cabinet.academy_honors_count,
        trophies_by_category=[TrophyCategoryCountView.model_validate(item) for item in cabinet.trophies_by_category],
        trophies_by_season=[TrophySeasonCountView.model_validate(item) for item in cabinet.trophies_by_season],
        recent_honors=[TrophyWinView.model_validate(item) for item in cabinet.recent_honors],
        historic_honors_timeline=[TrophyWinView.model_validate(item) for item in cabinet.historic_honors_timeline],
        summary_outputs=list(cabinet.summary_outputs),
    )


@router.get("/api/clubs/{club_id}/honors-timeline", response_model=HonorsTimelineView)
def get_honors_timeline(
    club_id: str,
    team_scope: str | None = Query(default=None),
    service: TrophyCabinetService = Depends(get_trophy_cabinet_service),
) -> HonorsTimelineView:
    try:
        timeline = service.get_honors_timeline(club_id, team_scope=team_scope)
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return HonorsTimelineView(
        club_id=timeline.club_id,
        club_name=timeline.club_name,
        honors=[TrophyWinView.model_validate(item) for item in timeline.honors],
    )


@router.get("/api/clubs/{club_id}/season-honors", response_model=SeasonHonorsArchiveView)
def get_season_honors(
    club_id: str,
    season_label: str | None = Query(default=None),
    team_scope: str | None = Query(default=None),
    service: TrophyCabinetService = Depends(get_trophy_cabinet_service),
) -> SeasonHonorsArchiveView:
    try:
        archive = service.get_season_honors(
            club_id,
            season_label=season_label,
            team_scope=team_scope,
        )
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SeasonHonorsArchiveView(
        club_id=archive.club_id,
        club_name=archive.club_name,
        season_records=[SeasonHonorsRecordView.model_validate(item) for item in archive.season_records],
    )


@router.get("/api/leaderboards/trophies", response_model=TrophyLeaderboardView)
def get_trophy_leaderboard(
    team_scope: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: TrophyCabinetService = Depends(get_trophy_cabinet_service),
) -> TrophyLeaderboardView:
    leaderboard = service.get_trophy_leaderboard(team_scope=team_scope, limit=limit)
    return TrophyLeaderboardView(
        entries=[TrophyLeaderboardEntryView.model_validate(item) for item in leaderboard.entries]
    )


__all__ = ["get_trophy_cabinet_service", "router"]
