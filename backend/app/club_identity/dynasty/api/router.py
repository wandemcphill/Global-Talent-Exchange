from __future__ import annotations

# legacy compatibility route - canonical router provides base /dynasty endpoint
# this router provides additional dynasty-related endpoints that complement the canonical endpoint

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.club_identity.dynasty.api.schemas import (
    ClubDynastyHistoryView,
    DynastyEraView,
    DynastyLeaderboardEntryView,
)
from backend.app.club_identity.dynasty.dependencies import get_dynasty_repository
from backend.app.club_identity.dynasty.repository import DynastyReadRepository
from backend.app.club_identity.dynasty.services.dynasty_detector import DynastyQueryService

router = APIRouter(prefix="/api", tags=["club-identity-dynasty"])


# /clubs/{club_id}/dynasty is provided by canonical_clubs router
# additional endpoints below:

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
