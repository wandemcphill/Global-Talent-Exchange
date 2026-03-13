from __future__ import annotations

# legacy compatibility route - canonical router provides base /dynasty endpoint
# this router provides additional dynasty-related endpoints that complement the canonical endpoint

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.club_identity.dynasty.api.schemas import (
    ClubDynastyProfileView,
    ClubDynastyHistoryView,
    DynastyEraView,
    DynastyStreaksView,
    DynastyLeaderboardEntryView,
)
from backend.app.club_identity.dynasty.dependencies import get_dynasty_repository
from backend.app.club_identity.dynasty.repository import DynastyReadRepository
from backend.app.club_identity.dynasty.services.dynasty_detector import DynastyQueryService
from backend.app.club_identity.models.dynasty_models import DynastyStatus, EraLabel
from backend.app.db import get_session
from backend.app.models.club_profile import ClubProfile

router = APIRouter(prefix="/api", tags=["club-identity-dynasty"])


@router.get("/clubs/{club_id}/dynasty", response_model=ClubDynastyProfileView)
def get_club_dynasty_profile(
    club_id: str,
    repository: DynastyReadRepository = Depends(get_dynasty_repository),
    session: Session = Depends(get_session),
) -> ClubDynastyProfileView:
    profile = DynastyQueryService(repository).get_profile(club_id)
    if profile is None:
        club = session.get(ClubProfile, club_id)
        if club is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dynasty profile for club {club_id} was not found",
            )
        return ClubDynastyProfileView(
            club_id=club.id,
            club_name=club.club_name,
            dynasty_status=DynastyStatus.NONE,
            current_era_label=EraLabel.NONE,
            active_dynasty_flag=False,
            dynasty_score=0,
            active_streaks=DynastyStreaksView(
                top_four=0,
                trophy_seasons=0,
                world_super_cup_qualification=0,
                positive_reputation=0,
            ),
            last_four_season_summary=(),
            reasons=(),
            current_snapshot=None,
            dynasty_timeline=(),
            eras=(),
            events=(),
        )
    return ClubDynastyProfileView.model_validate(profile)

@router.get("/clubs/{club_id}/dynasty/history", response_model=ClubDynastyHistoryView)
def get_club_dynasty_history(
    club_id: str,
    repository: DynastyReadRepository = Depends(get_dynasty_repository),
) -> ClubDynastyHistoryView:
    history = DynastyQueryService(repository).get_history(club_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynasty history for club {club_id} was not found",
        )
    return ClubDynastyHistoryView.model_validate(history)


@router.get("/leaderboards/dynasties", response_model=list[DynastyLeaderboardEntryView])
def get_dynasty_leaderboard(
    limit: int = Query(default=25, ge=1, le=100),
    repository: DynastyReadRepository = Depends(get_dynasty_repository),
) -> list[DynastyLeaderboardEntryView]:
    leaderboard = DynastyQueryService(repository).get_leaderboard(limit=limit)
    return [DynastyLeaderboardEntryView.model_validate(entry) for entry in leaderboard]


@router.get("/clubs/{club_id}/eras", response_model=list[DynastyEraView])
def get_club_eras(
    club_id: str,
    repository: DynastyReadRepository = Depends(get_dynasty_repository),
) -> list[DynastyEraView]:
    eras = DynastyQueryService(repository).get_eras(club_id)
    if eras is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynasty eras for club {club_id} were not found",
        )
    return [DynastyEraView.model_validate(era) for era in eras]


__all__ = ["router"]
