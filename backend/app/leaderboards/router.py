from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_current_admin
from app.db import get_session
from app.leaderboards.leaderboard_service import LeaderboardNotFoundError, LeaderboardService
from app.leaderboards.schemas import (
    LeaderboardView,
    PlayerRanksView,
    SeasonHistoryView,
    SeasonLifecycleView,
    SeasonRewardTierView,
    SeasonRewardView,
    SeasonView,
)
from app.leaderboards.season_service import SeasonLifecycleResult, SeasonService
from app.models.user import User

router = APIRouter(tags=["leaderboard"])
admin_router = APIRouter(prefix="/admin/leaderboard", tags=["leaderboard-admin"])


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

def _season_view(season) -> SeasonView:
    metadata = dict(getattr(season, "metadata_json", {}) or {})
    duration_days = int(metadata.get("duration_days", 30) or 30)
    days_remaining = 0
    if getattr(season, "status", None) and str(season.status) == "active":
        delta = season.end_date - SeasonService._now()
        days_remaining = max(0, int(delta.total_seconds() // 86400))
    return SeasonView(
        id=season.id,
        start_date=season.start_date,
        end_date=season.end_date,
        status=season.status,
        default_rating=season.default_rating,
        k_factor=season.k_factor,
        reset_strategy=season.reset_strategy,
        soft_reset_factor=season.soft_reset_factor,
        duration_days=duration_days,
        days_remaining=days_remaining,
        rank_tiers=[
            {"key": str(item.get("key") or ""), "label": str(item.get("label") or ""), "min_rating": int(item.get("min_rating") or 0)}
            for item in (metadata.get("rank_tiers") or [])
            if isinstance(item, dict)
        ],
        reward_tiers=[
            SeasonRewardTierView(
                rank_position=int(item.get("rank_position") or 0),
                title=str(item.get("title") or f"Top {item.get('rank_position') or ''}").strip(),
                coins=item.get("coins") or "0.0000",
                trophies=int(item.get("trophies") or 0),
                badges=[str(badge) for badge in (item.get("badges") or [])],
                visibility_boost=int(item.get("visibility_boost") or 0),
                exclusive_tournament_key=(
                    str(item.get("exclusive_tournament_key"))
                    if item.get("exclusive_tournament_key") is not None
                    else None
                ),
            )
            for item in (metadata.get("reward_tiers") or [])
            if isinstance(item, dict)
        ],
        ended_at=season.ended_at,
        rewards_distributed_at=season.rewards_distributed_at,
        metadata_json=metadata,
    )


def _reward_view(reward) -> SeasonRewardView:
    metadata = dict(getattr(reward, "metadata_json", {}) or {})
    return SeasonRewardView(
        season_id=reward.season_id,
        board_key=reward.board_key,
        player_id=reward.player_id,
        display_name=reward.display_name,
        rank_position=reward.rank_position,
        title=str(metadata.get("title")) if metadata.get("title") is not None else None,
        coins=reward.coins,
        trophies=reward.trophies,
        badges=[str(item) for item in (reward.badges_json or [])],
        visibility_boost=int(metadata.get("visibility_boost", 0) or 0),
        exclusive_tournament_key=(
            str(metadata.get("exclusive_tournament_key"))
            if metadata.get("exclusive_tournament_key") is not None
            else None
        ),
        status=reward.status,
        distributed_at=reward.distributed_at,
    )


def _lifecycle_view(result: SeasonLifecycleResult) -> SeasonLifecycleView:
    return SeasonLifecycleView(
        ended_season=_season_view(result.ended_season),
        next_season=_season_view(result.next_season) if result.next_season is not None else None,
        rewards=[_reward_view(item) for item in result.rewards],
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
    return _season_view(season)


@router.get("/season/history", response_model=SeasonHistoryView)
def get_season_history(
    limit: int = Query(default=20, ge=1, le=200),
    season_service: SeasonService = Depends(get_season_service),
) -> SeasonHistoryView:
    seasons = season_service.get_history(limit=limit)
    return SeasonHistoryView(
        seasons=[_season_view(season) for season in seasons]
    )


@admin_router.post("/season/archive", response_model=SeasonLifecycleView)
def archive_current_season(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    season_service: SeasonService = Depends(get_season_service),
) -> SeasonLifecycleView:
    result = season_service.archive_season()
    session.commit()
    return _lifecycle_view(result)


@admin_router.post("/season/reset", response_model=SeasonLifecycleView)
def reset_current_rankings(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    season_service: SeasonService = Depends(get_season_service),
) -> SeasonLifecycleView:
    result = season_service.reset_rankings()
    session.commit()
    return _lifecycle_view(result)
