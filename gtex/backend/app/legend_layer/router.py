from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_current_user, get_session
from app.legend_layer.schemas import (
    GlobalPrestigeRankingsView,
    NewsArticleView,
    PlayerInterviewView,
    PlayerPersonalityView,
    PrestigeRankingEntryView,
    PrestigeRankingListView,
)
from app.legend_layer.service import LegendLayerNotFoundError, LegendLayerService
from app.models.user import User

router = APIRouter(tags=["legend-layer"])


def get_legend_layer_service(
    request: Request,
    session: Session = Depends(get_session),
) -> LegendLayerService:
    settings = getattr(request.app.state, "settings", None)
    redis_url = getattr(settings, "redis_url", None) if settings is not None else None
    return LegendLayerService(session=session, redis_url=redis_url)


def _raise_not_found(exc: LegendLayerNotFoundError) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _ranking_entry_views(items) -> list[PrestigeRankingEntryView]:
    return [PrestigeRankingEntryView.model_validate(item, from_attributes=True) for item in items]


@router.get("/news/feed", response_model=list[NewsArticleView])
def get_news_feed(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> list[NewsArticleView]:
    articles = service.list_news_feed(current_user=current_user, limit=limit)
    session.commit()
    return [NewsArticleView.model_validate(item, from_attributes=True) for item in articles]


@router.get("/news/{article_id}", response_model=NewsArticleView)
def get_news_article(
    article_id: str,
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> NewsArticleView:
    try:
        article = service.get_article(article_id)
    except LegendLayerNotFoundError as exc:
        _raise_not_found(exc)
    session.commit()
    return NewsArticleView.model_validate(article, from_attributes=True)


@router.get("/rankings/global", response_model=GlobalPrestigeRankingsView)
def get_global_rankings(
    scope: str = Query(default="lifetime", pattern="^(lifetime|seasonal)$"),
    season_key: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> GlobalPrestigeRankingsView:
    payload = service.get_global_rankings(scope=scope, season_key=season_key, limit=limit)
    session.commit()
    return GlobalPrestigeRankingsView(
        scope=payload["scope"],
        season_key=payload["season_key"],
        generated_at=payload["generated_at"],
        players=_ranking_entry_views(payload["players"]),
        clubs=_ranking_entry_views(payload["clubs"]),
        users=_ranking_entry_views(payload["users"]),
        national_teams=_ranking_entry_views(payload["national_teams"]),
    )


@router.get("/rankings/players", response_model=PrestigeRankingListView)
def get_player_rankings(
    scope: str = Query(default="lifetime", pattern="^(lifetime|seasonal)$"),
    season_key: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> PrestigeRankingListView:
    payload = service.get_rankings(entity_type="player", scope=scope, season_key=season_key, limit=limit)
    session.commit()
    return PrestigeRankingListView(
        entity_type=payload["entity_type"],
        scope=payload["scope"],
        season_key=payload["season_key"],
        generated_at=payload["generated_at"],
        entries=_ranking_entry_views(payload["entries"]),
    )


@router.get("/rankings/clubs", response_model=PrestigeRankingListView)
def get_club_rankings(
    scope: str = Query(default="lifetime", pattern="^(lifetime|seasonal)$"),
    season_key: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> PrestigeRankingListView:
    payload = service.get_rankings(entity_type="club", scope=scope, season_key=season_key, limit=limit)
    session.commit()
    return PrestigeRankingListView(
        entity_type=payload["entity_type"],
        scope=payload["scope"],
        season_key=payload["season_key"],
        generated_at=payload["generated_at"],
        entries=_ranking_entry_views(payload["entries"]),
    )


@router.get("/players/{player_id}/personality", response_model=PlayerPersonalityView)
def get_player_personality(
    player_id: str,
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> PlayerPersonalityView:
    try:
        payload = service.get_player_personality_profile(player_id)
    except LegendLayerNotFoundError as exc:
        _raise_not_found(exc)
    session.commit()
    return PlayerPersonalityView.model_validate(payload)


@router.get("/players/{player_id}/interviews", response_model=list[PlayerInterviewView])
def get_player_interviews(
    player_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    service: LegendLayerService = Depends(get_legend_layer_service),
) -> list[PlayerInterviewView]:
    try:
        interviews = service.list_player_interviews(player_id, limit=limit)
    except LegendLayerNotFoundError as exc:
        _raise_not_found(exc)
    session.commit()
    return [PlayerInterviewView.model_validate(item, from_attributes=True) for item in interviews]
