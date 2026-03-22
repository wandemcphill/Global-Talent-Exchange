from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.players.real_player_schemas import RealPlayerUniverseDetailView, RealPlayerUniverseListView
from app.players.real_player_service import (
    RealPlayerUniverseError,
    RealPlayerUniverseNotFoundError,
    RealPlayerUniverseQueryService,
    RealPlayerUniverseValidationError,
)
from app.players.schemas import PlayerSummaryView
from app.players.service import PlayerSummaryQueryService

router = APIRouter(prefix="/players", tags=["players"])


def get_real_player_universe_query_service(
    session: Session = Depends(get_session),
) -> RealPlayerUniverseQueryService:
    return RealPlayerUniverseQueryService(session=session)


def raise_real_player_http_exception(exc: RealPlayerUniverseError) -> Never:
    if isinstance(exc, RealPlayerUniverseNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RealPlayerUniverseValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/summaries/recent", response_model=list[PlayerSummaryView])
def list_recent_player_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[PlayerSummaryView]:
    service = PlayerSummaryQueryService(session)
    return service.list_recent_views(limit)


@router.get("/{player_id}/summary", response_model=PlayerSummaryView)
def get_player_summary(
    player_id: str,
    session: Session = Depends(get_session),
) -> PlayerSummaryView:
    summary = PlayerSummaryQueryService(session).get_summary_view(player_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player summary for {player_id} was not found")
    return summary


@router.get("/real-universe", response_model=RealPlayerUniverseListView)
def list_real_player_universe(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    position: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniverseListView:
    try:
        result = service.list_players(
            limit=limit,
            offset=offset,
            position=position,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            search=search,
            sort=sort,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniverseListView.model_validate(result)


@router.get("/real-universe/search", response_model=RealPlayerUniverseListView)
def search_real_player_universe(
    search: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    position: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    sort: str = Query(default="current_value"),
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniverseListView:
    try:
        result = service.list_players(
            limit=limit,
            offset=offset,
            position=position,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            search=search,
            sort=sort,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniverseListView.model_validate(result)


@router.get("/real-universe/{player_id}", response_model=RealPlayerUniverseDetailView)
def get_real_player_universe_detail(
    player_id: str,
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniverseDetailView:
    try:
        result = service.get_player_detail(player_id)
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniverseDetailView.model_validate(result)
