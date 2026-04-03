from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.core.cache_namespaces import COMPETITIONS_CACHE_NAMESPACE
from app.core.pagination import build_pagination_meta, resolve_pagination
from app.core.response_cache import get_response_cache
from app.global_memory.schemas import (
    CompetitionEntryResultView,
    CompetitionEnterRequest,
    CompetitionListItemView,
    CompetitionPageView,
    DynastyLeaderboardEntryView,
    HallOfFamePlayerView,
    NationalPoolPlayerView,
    PlayerHistoryResponseView,
    PlayerRentRequest,
    PlayerRentResultView,
    UserDynastyView,
)
from app.global_memory.service import GlobalMemoryError, GlobalMemoryNotFoundError, GlobalMemoryService
from app.ingestion.models import Competition, Country

router = APIRouter(tags=["global-memory"])


def _service(request: Request, session: Session = Depends(get_session)) -> GlobalMemoryService:
    return GlobalMemoryService(session, event_publisher=getattr(request.app.state, "event_publisher", None))


def _raise_http(exc: GlobalMemoryError) -> None:
    if isinstance(exc, GlobalMemoryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/competitions", response_model=CompetitionPageView)
def list_competitions(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    country_code: str | None = Query(default=None),
    age_bracket: str | None = Query(default=None),
    service: GlobalMemoryService = Depends(_service),
) -> CompetitionPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)
    settings = request.app.state.settings
    if settings.api_cache_enabled:
        cached_payload = get_response_cache(request.app).get_json(
            namespace=COMPETITIONS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
        )
        if cached_payload is not None:
            return CompetitionPageView.model_validate(cached_payload)

    count_stmt = select(func.count()).select_from(Competition).outerjoin(Country, Country.id == Competition.country_id)
    if country_code:
        count_stmt = count_stmt.where(func.upper(Country.alpha2_code) == country_code.upper())
    if age_bracket:
        count_stmt = count_stmt.where(func.lower(func.coalesce(Competition.age_bracket, "")) == age_bracket.lower())
    total = int(service.session.scalar(count_stmt) or 0)

    items = service.list_competitions(
        limit=params.per_page,
        offset=params.offset,
        country_code=country_code,
        age_bracket=age_bracket,
    )
    response = CompetitionPageView(
        items=tuple(CompetitionListItemView.model_validate(item) for item in items),
        pagination=build_pagination_meta(params=params, total=total),
    )
    if settings.api_cache_enabled:
        get_response_cache(request.app).set_json(
            namespace=COMPETITIONS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.competitions_cache_ttl_seconds,
        )
    return response


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
