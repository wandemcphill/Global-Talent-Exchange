from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.football_universe.schemas import BroadcastSessionView, ClubIdentityView, FanBaseView, MediaEventView
from app.football_universe.service import FootballUniverseService

router = APIRouter(tags=["football-universe"])


def get_football_universe_service(session: Session = Depends(get_session)) -> FootballUniverseService:
    return FootballUniverseService(session)


@router.get("/broadcast/{match_id}", response_model=BroadcastSessionView)
def read_broadcast_session(
    match_id: str,
    service: FootballUniverseService = Depends(get_football_universe_service),
) -> BroadcastSessionView:
    payload = service.get_broadcast_session(match_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Broadcast session was not found.")
    return payload


@router.get("/fans/{club_id}", response_model=FanBaseView)
def read_fan_base(
    club_id: str,
    service: FootballUniverseService = Depends(get_football_universe_service),
) -> FanBaseView:
    payload = service.get_fan_base(club_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Fan base was not found.")
    return payload


@router.get("/club/identity", response_model=ClubIdentityView)
def read_club_identity(
    club_id: str = Query(..., min_length=1),
    service: FootballUniverseService = Depends(get_football_universe_service),
) -> ClubIdentityView:
    payload = service.get_club_identity(club_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Club identity was not found.")
    return payload


@router.get("/media", response_model=list[MediaEventView])
def list_media_events(
    club_id: str | None = Query(default=None),
    match_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    service: FootballUniverseService = Depends(get_football_universe_service),
) -> list[MediaEventView]:
    return service.list_media_events(club_id=club_id, match_id=match_id, limit=limit)


__all__ = ["router"]
