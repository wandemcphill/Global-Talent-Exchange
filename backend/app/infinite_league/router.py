from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import get_optional_current_user
from app.infinite_league.schemas import (
    InfiniteLeagueEconomyView,
    InfiniteLeagueLivestreamView,
    InfiniteLeagueMatchesResponse,
    InfiniteLeagueMatchView,
    InfiniteLeagueStatusView,
)
from app.infinite_league.service import ensure_infinite_league_runtime
from app.models.user import User, UserRole
from app.pundits.schemas import PunditDebateResponse
from app.viral.schemas import ViralFeedResponse

router = APIRouter(prefix="/infinite-league", tags=["infinite-league"])


def _production_like_environment(request: Request) -> bool:
    settings = getattr(getattr(request, "app", None).state, "settings", None)
    app_env = str(getattr(settings, "app_env", "") or "").strip().lower()
    return app_env in {"production", "prod", "staging", "release"}


def _raise_generated_runtime_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Infinite League generated runtime is disabled in protected environments. "
            "Use persisted Competition OS or live match endpoints instead."
        ),
    )


def _require_generated_runtime_available(request: Request) -> None:
    if _production_like_environment(request):
        _raise_generated_runtime_disabled()


def require_infinite_league_tick_control(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
) -> None:
    if not _production_like_environment(request):
        return
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication is required to advance Infinite League matches.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required to advance Infinite League matches.",
        )


@router.get("/status", response_model=InfiniteLeagueStatusView)
def read_infinite_league_status(request: Request) -> InfiniteLeagueStatusView:
    _require_generated_runtime_available(request)
    return ensure_infinite_league_runtime(request.app).status_view()


@router.post("/tick", response_model=InfiniteLeagueMatchesResponse)
def tick_infinite_league(
    request: Request,
    count: int = Query(default=1, ge=1, le=10),
    _: None = Depends(require_infinite_league_tick_control),
) -> InfiniteLeagueMatchesResponse:
    _require_generated_runtime_available(request)
    runtime = ensure_infinite_league_runtime(request.app)
    generated = runtime.advance(count=count)
    matches = []
    for item in generated:
        match_view = runtime.get_match_view(item.result.match_id)
        if match_view is not None:
            matches.append(match_view)
    return InfiniteLeagueMatchesResponse(matches=matches)


@router.get("/matches", response_model=InfiniteLeagueMatchesResponse)
def read_infinite_league_matches(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
) -> InfiniteLeagueMatchesResponse:
    _require_generated_runtime_available(request)
    return InfiniteLeagueMatchesResponse(matches=ensure_infinite_league_runtime(request.app).list_matches(limit=limit))


@router.get("/matches/{match_id}", response_model=InfiniteLeagueMatchView)
def read_infinite_league_match(match_id: str, request: Request) -> InfiniteLeagueMatchView:
    _require_generated_runtime_available(request)
    runtime = ensure_infinite_league_runtime(request.app)
    match_view = runtime.get_match_view(match_id)
    if match_view is None:
        raise HTTPException(status_code=404, detail="Infinite league match not found.")
    return match_view


@router.get("/viral-feed", response_model=ViralFeedResponse)
def read_infinite_league_viral_feed(
    request: Request,
    limit: int = Query(default=12, ge=1, le=50),
) -> ViralFeedResponse:
    _require_generated_runtime_available(request)
    return ensure_infinite_league_runtime(request.app).build_viral_feed(limit=limit)


@router.get("/pundits/{match_id}", response_model=PunditDebateResponse)
def read_infinite_league_pundits(match_id: str, request: Request) -> PunditDebateResponse:
    _require_generated_runtime_available(request)
    debate = ensure_infinite_league_runtime(request.app).build_pundit_debate(match_id)
    if debate is None:
        raise HTTPException(status_code=404, detail="Infinite league match not found.")
    return debate


@router.get("/livestream", response_model=InfiniteLeagueLivestreamView)
def read_infinite_league_livestream(request: Request) -> InfiniteLeagueLivestreamView:
    _require_generated_runtime_available(request)
    return ensure_infinite_league_runtime(request.app).livestream_view()


@router.get("/economy", response_model=InfiniteLeagueEconomyView)
def read_infinite_league_economy(request: Request) -> InfiniteLeagueEconomyView:
    _require_generated_runtime_available(request)
    return ensure_infinite_league_runtime(request.app).economy_view()
