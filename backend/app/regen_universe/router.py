from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.regen_universe.service import RegenUniverseError, RegenUniverseService
from app.schemas.regen_universe import (
    RegenAwardResultView,
    RegenHallOfFameView,
    RegenRankingLeaderboardView,
    RegenSeasonCloseRequest,
    RegenSeasonCreateRequest,
    RegenSeasonView,
    RegenUniverseCloseResultView,
)


router = APIRouter(prefix="/regen-universe", tags=["regen-universe"])
admin_router = APIRouter(prefix="/admin/regen-universe", tags=["regen-universe-admin"])


@router.get("/seasons", response_model=list[RegenSeasonView])
def list_regen_seasons(
    active_only: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[RegenSeasonView]:
    service = RegenUniverseService(session)
    return [
        RegenSeasonView.model_validate(service._season_payload(item))
        for item in service.list_seasons(active_only=active_only)
    ]


@router.get("/awards", response_model=list[RegenAwardResultView])
def list_regen_awards(
    season_id: str | None = Query(default=None),
    award_code: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[RegenAwardResultView]:
    return [
        RegenAwardResultView.model_validate(item)
        for item in RegenUniverseService(session).list_awards(season_id=season_id, award_code=award_code)
    ]


@router.get("/rankings", response_model=RegenRankingLeaderboardView)
def list_regen_rankings(
    season_id: str | None = Query(default=None),
    category: str = Query(default="overall"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> RegenRankingLeaderboardView:
    return RegenRankingLeaderboardView.model_validate(
        RegenUniverseService(session).list_rankings(season_id=season_id, category=category, limit=limit)
    )


@router.get("/hall-of-fame", response_model=RegenHallOfFameView)
def list_regen_hall_of_fame(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> RegenHallOfFameView:
    return RegenHallOfFameView.model_validate(RegenUniverseService(session).list_hall_of_fame(limit=limit))


@admin_router.post("/seasons", response_model=RegenSeasonView)
def create_regen_season(
    payload: RegenSeasonCreateRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenSeasonView:
    service = RegenUniverseService(session)
    try:
        season = service.create_season(
            season_number=payload.season_number,
            start_date=payload.start_date,
            end_date=payload.end_date,
            source_ingestion_season_ids=payload.source_ingestion_season_ids,
            is_active=payload.is_active,
        )
    except RegenUniverseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return RegenSeasonView.model_validate(service._season_payload(season))


@admin_router.post("/seasons/{season_id}/close", response_model=RegenUniverseCloseResultView)
def close_regen_season(
    season_id: str,
    payload: RegenSeasonCloseRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseCloseResultView:
    service = RegenUniverseService(session)
    try:
        result = service.close_season(
            season_id=season_id,
            close_date=payload.close_date,
            start_next_season=payload.start_next_season,
        )
    except RegenUniverseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return RegenUniverseCloseResultView.model_validate(result)
