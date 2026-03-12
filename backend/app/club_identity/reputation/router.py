from __future__ import annotations

# legacy compatibility route - canonical router provides base /reputation endpoint
# this router provides additional reputation-related endpoints that complement the canonical endpoint

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.club_identity.reputation.schemas import (
    ClubPrestigeView,
    ClubReputationHistoryView,
    PrestigeLeaderboardView,
)
from backend.app.club_identity.reputation.service import ClubReputationQueryService
from backend.app.db import get_session

router = APIRouter(prefix="/api", tags=["club-reputation"])


# /clubs/{club_id}/reputation is provided by canonical_clubs router
# additional endpoints below:

@router.get("/clubs/{club_id}/reputation/history", response_model=ClubReputationHistoryView)
def get_club_reputation_history(
    club_id: str,
    session: Session = Depends(get_session),
) -> ClubReputationHistoryView:
    return ClubReputationQueryService(session).get_history(club_id)


@router.get("/clubs/{club_id}/prestige", response_model=ClubPrestigeView)
def get_club_prestige(
    club_id: str,
    session: Session = Depends(get_session),
) -> ClubPrestigeView:
    return ClubReputationQueryService(session).get_prestige(club_id)


@router.get("/leaderboards/prestige", response_model=PrestigeLeaderboardView)
def get_prestige_leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> PrestigeLeaderboardView:
    return ClubReputationQueryService(session).get_leaderboard(limit=limit)
