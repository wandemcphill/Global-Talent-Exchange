from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_current_user, get_session
from app.core.cache import NullCacheBackend
from app.models.user import User
from app.news_engine.schemas import DailyNewsResponse
from app.news_engine.schemas import NewsStoryView
from app.services.gtex_news_engine import GTEXNewsEngineService, GTEXNewsRateLimitError

router = APIRouter(prefix="/news", tags=["gtex-news"])


@router.get("/daily", response_model=DailyNewsResponse)
def get_daily_news(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> dict:
    cache_backend = getattr(request.app.state, "cache_backend", None) or NullCacheBackend()
    user_id = current_user.id if current_user is not None else _anonymous_user_id(request)
    try:
        return GTEXNewsEngineService(session, cache_backend=cache_backend).daily_news(user_id=user_id)
    except GTEXNewsRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"X-RateLimit-Limit": str(exc.limit)},
        ) from exc


@router.get("/personalized", response_model=DailyNewsResponse)
def get_personalized_news(
    request: Request,
    favorite_club: str | None = None,
    watched_players: list[str] = Query(default_factory=list),
    rival_clubs: list[str] = Query(default_factory=list),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> dict:
    cache_backend = getattr(request.app.state, "cache_backend", None) or NullCacheBackend()
    user_id = current_user.id if current_user is not None else _anonymous_user_id(request)
    resolved_favorite_club = favorite_club or (current_user.favourite_club if current_user is not None else None)
    try:
        return GTEXNewsEngineService(session, cache_backend=cache_backend).personalized_news(
            {
                "user_id": user_id,
                "favorite_club": resolved_favorite_club,
                "watched_players": watched_players,
                "rival_clubs": rival_clubs,
            }
        )
    except GTEXNewsRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"X-RateLimit-Limit": str(exc.limit)},
        ) from exc


@router.get("/breaking", response_model=list[NewsStoryView])
def get_breaking_news(
    request: Request,
    session: Session = Depends(get_session),
) -> list[dict]:
    cache_backend = getattr(request.app.state, "cache_backend", None) or NullCacheBackend()
    return GTEXNewsEngineService(session, cache_backend=cache_backend).breaking_news()


def _anonymous_user_id(request: Request) -> str:
    client_host = request.client.host if request.client is not None else "unknown"
    return f"anon:{client_host}"


__all__ = ["router"]
