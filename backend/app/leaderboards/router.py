from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session
from app.leaderboards.leaderboard_service import LeaderboardNotFoundError, LeaderboardService
from app.leaderboards.schemas import LeaderboardView, PlayerRanksView, SeasonHistoryView, SeasonView
from app.leaderboards.season_service import SeasonService

router = APIRouter(tags=["leaderboard"])


def get_leaderboard_service(
    request: Request,
    session: Session = Depends(get_session),
) -> LeaderboardService:
    settings = getattr(request.app.state, "settings", None)
    redis_url = getattr(settings, "redis_url", None) if settings is not None else None
    return LeaderboardService(session=session, redis_url=redis_url)


def get_season_service(
    request: Request,
    session: Session = Depends(get_session),
) -> SeasonService:
    settings = getattr(request.app.state, "settings", None)
    redis_url = getattr(settings, "redis_url", None) if settings is not None else None
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None and not isinstance(session_factory, sessionmaker):
        session_factory = None
    return SeasonService(
        session=session,
        event_publisher=getattr(request.app.state, "event_publisher", None),
        redis_url=redis_url,
        session_factory=session_factory,
    )


@router.get("/leaderboard/global", response_model=LeaderboardView)
def get_global_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
    season_service: SeasonService = Depends(get_season_service),
) -> LeaderboardView:
    season = season_service.get_current_season(auto_rollover=True)
    response = leaderboard_service.build_board_view(season_id=season.id, limit=limit)
    session.commit()
    return response


@router.get("/leaderboard/region/{region}", response_model=LeaderboardView)
def get_region_leaderboard(
    region: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
    season_service: SeasonService = Depends(get_season_service),
) -> LeaderboardView:
    season = season_service.get_current_season(auto_rollover=True)
    response = leaderboard_service.build_board_view(season_id=season.id, limit=limit, region=region)
    session.commit()
    return response


@router.get("/leaderboard/division/{division}", response_model=LeaderboardView)
def get_division_leaderboard(
    division: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
    season_service: SeasonService = Depends(get_season_service),
) -> LeaderboardView:
    season = season_service.get_current_season(auto_rollover=True)
    response = leaderboard_service.build_board_view(season_id=season.id, limit=limit, division=division)
    session.commit()
    return response


@router.get("/leaderboard/player/{player_id}", response_model=PlayerRanksView)
def get_player_rank(
    player_id: str,
    session: Session = Depends(get_session),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
    season_service: SeasonService = Depends(get_season_service),
) -> PlayerRanksView:
    season = season_service.get_current_season(auto_rollover=True)
    try:
        response = leaderboard_service.build_player_ranks(player_id, season_id=season.id)
    except LeaderboardNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    return response


@router.get("/season/current", response_model=SeasonView)
def get_current_season(
    session: Session = Depends(get_session),
    season_service: SeasonService = Depends(get_season_service),
) -> SeasonView:
    season = season_service.get_current_season(auto_rollover=True)
    session.commit()
    return SeasonView.model_validate(season, from_attributes=True)


@router.get("/season/history", response_model=SeasonHistoryView)
def get_season_history(
    limit: int = Query(default=20, ge=1, le=200),
    season_service: SeasonService = Depends(get_season_service),
) -> SeasonHistoryView:
    seasons = season_service.get_history(limit=limit)
    return SeasonHistoryView(
        seasons=[SeasonView.model_validate(season, from_attributes=True) for season in seasons]
    )
