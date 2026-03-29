from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.global_memory.schemas import (
    CompetitionEntryResultView,
    CompetitionEnterRequest,
    CompetitionListItemView,
    DynastyLeaderboardEntryView,
    HallOfFamePlayerView,
    NationalPoolPlayerView,
    PlayerHistoryResponseView,
    PlayerRentRequest,
    PlayerRentResultView,
    UserDynastyView,
)
from app.global_memory.service import GlobalMemoryError, GlobalMemoryNotFoundError, GlobalMemoryService

router = APIRouter(tags=["global-memory"])


def _service(request: Request, session: Session = Depends(get_session)) -> GlobalMemoryService:
    return GlobalMemoryService(session, event_publisher=getattr(request.app.state, "event_publisher", None))


def _raise_http(exc: GlobalMemoryError) -> None:
    if isinstance(exc, GlobalMemoryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/competitions", response_model=tuple[CompetitionListItemView, ...])
def list_competitions(
    limit: int = Query(default=50, ge=1, le=200),
    country_code: str | None = Query(default=None),
    age_bracket: str | None = Query(default=None),
    service: GlobalMemoryService = Depends(_service),
) -> tuple[CompetitionListItemView, ...]:
    return service.list_competitions(limit=limit, country_code=country_code, age_bracket=age_bracket)


@router.post("/enter", response_model=CompetitionEntryResultView)
def enter_competition(
    payload: CompetitionEnterRequest,
    service: GlobalMemoryService = Depends(_service),
) -> CompetitionEntryResultView:
    try:
        result = service.enter_competition(payload)
    except GlobalMemoryError as exc:
        _raise_http(exc)
    service.session.commit()
    return result


@router.post("/rent", response_model=PlayerRentResultView)
def rent_player(
    payload: PlayerRentRequest,
    service: GlobalMemoryService = Depends(_service),
) -> PlayerRentResultView:
    try:
        result = service.rent_player(payload)
    except GlobalMemoryError as exc:
        _raise_http(exc)
    service.session.commit()
    return result


@router.get("/national-pool", response_model=tuple[NationalPoolPlayerView, ...])
def get_national_pool(
    country_code: str | None = Query(default=None),
    competition_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: GlobalMemoryService = Depends(_service),
) -> tuple[NationalPoolPlayerView, ...]:
    return service.list_national_pool(country_code=country_code, competition_id=competition_id, limit=limit)


@router.get("/player-history", response_model=PlayerHistoryResponseView)
def get_player_history(
    player_id: str = Query(...),
    service: GlobalMemoryService = Depends(_service),
) -> PlayerHistoryResponseView:
    try:
        return service.get_player_history(player_id)
    except GlobalMemoryError as exc:
        _raise_http(exc)
    raise AssertionError("unreachable")


@router.get("/player-history/{player_id}", response_model=PlayerHistoryResponseView)
def get_player_history_by_path(
    player_id: str,
    service: GlobalMemoryService = Depends(_service),
) -> PlayerHistoryResponseView:
    try:
        return service.get_player_history(player_id)
    except GlobalMemoryError as exc:
        _raise_http(exc)
    raise AssertionError("unreachable")


@router.get("/dynasty", response_model=UserDynastyView)
def get_dynasty(
    user_id: str = Query(...),
    service: GlobalMemoryService = Depends(_service),
) -> UserDynastyView:
    try:
        return service.get_dynasty(user_id)
    except GlobalMemoryError as exc:
        _raise_http(exc)
    raise AssertionError("unreachable")


@router.get("/dynasty/leaderboard", response_model=tuple[DynastyLeaderboardEntryView, ...])
def get_dynasty_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    service: GlobalMemoryService = Depends(_service),
) -> tuple[DynastyLeaderboardEntryView, ...]:
    return service.list_dynasty_leaderboard(limit=limit)


@router.get("/hall-of-fame", response_model=tuple[HallOfFamePlayerView, ...])
def get_hall_of_fame(
    limit: int = Query(default=50, ge=1, le=200),
    service: GlobalMemoryService = Depends(_service),
) -> tuple[HallOfFamePlayerView, ...]:
    return service.list_hall_of_fame(limit=limit)
