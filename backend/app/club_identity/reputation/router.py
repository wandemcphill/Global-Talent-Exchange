from __future__ import annotations

# legacy compatibility route - canonical router provides base /reputation endpoint
# this router provides additional reputation-related endpoints that complement the canonical endpoint

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.club_identity.reputation.schemas import (
    ClubPrestigeView,
    ClubReputationView,
    ClubReputationHistoryView,
    PrestigeLeaderboardView,
)
from app.club_identity.reputation.service import ClubReputationQueryService
from app.db import get_session

router = APIRouter(prefix="/api", tags=["club-reputation"])


@router.get("/clubs/{club_id}/reputation", response_model=ClubReputationView)
def get_club_reputation(
    club_id: str,
    session: Session = Depends(get_session),
) -> ClubReputationView:
    return ClubReputationQueryService(session).get_reputation(club_id)


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
