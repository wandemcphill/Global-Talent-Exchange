from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.models.user import User
from app.players.real_player_schemas import (
    PlayerMatchEventCreate,
    PlayerMatchEventView,
    PlayerMatchProfileView,
    RealPlayerMatchRequest,
    RealPlayerMatchResponseView,
    RealPlayerUniverseDetailView,
    RealPlayerUniverseListView,
    RealPlayerUniversePageView,
)
from app.players.real_player_read_models import RealPlayerUniverseListResult
from app.players.match_learning_service import (
    PlayerMatchLearningError,
    PlayerMatchLearningNotFoundError,
    PlayerMatchLearningService,
    PlayerMatchLearningValidationError,
)
from app.players.real_player_service import (
    RealPlayerUniverseError,
    RealPlayerUniverseNotFoundError,
    RealPlayerUniverseQueryService,
    RealPlayerUniverseValidationError,
)
from app.players.schemas import PlayerSummaryView
from app.players.service import PlayerSummaryQueryService
from app.regen_universe.expansion_service import (
    RegenUniverseExpansionError,
    RegenUniverseExpansionNotFoundError,
    RegenUniverseExpansionService,
    RegenUniverseExpansionValidationError,
)
from app.schemas.regen_universe_expansion import PlayerDNAView, PlayerRivalryView, PlayerStoryView

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


def raise_player_match_learning_http_exception(exc: PlayerMatchLearningError) -> Never:
    if isinstance(exc, PlayerMatchLearningNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PlayerMatchLearningValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def raise_regen_universe_expansion_http_exception(exc: RegenUniverseExpansionError) -> Never:
    if isinstance(exc, RegenUniverseExpansionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenUniverseExpansionValidationError):
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


@router.get("/{player_id}/story", response_model=PlayerStoryView)
def get_player_story(
    player_id: str,
    session: Session = Depends(get_session),
) -> PlayerStoryView:
    try:
        payload = RegenUniverseExpansionService(session).get_player_story(player_id)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    return PlayerStoryView.model_validate(payload)


@router.get("/{player_id}/dna", response_model=PlayerDNAView)
def get_player_dna(
    player_id: str,
    session: Session = Depends(get_session),
) -> PlayerDNAView:
    try:
        payload = RegenUniverseExpansionService(session).get_player_dna(player_id)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    return PlayerDNAView.model_validate(payload)


@router.get("/{player_id}/rivalries", response_model=list[PlayerRivalryView])
def get_player_rivalries(
    player_id: str,
    limit: int = Query(default=10, ge=1, le=20),
    session: Session = Depends(get_session),
) -> list[PlayerRivalryView]:
    try:
        payload = RegenUniverseExpansionService(session).list_player_rivalries(player_id, limit=limit)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    return [PlayerRivalryView.model_validate(item) for item in payload]


@router.post("/match", response_model=RealPlayerMatchResponseView)
def match_players(
    payload: RealPlayerMatchRequest,
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
    current_user: User | None = Depends(get_optional_current_user),
) -> RealPlayerMatchResponseView:
    try:
        result = service.match_players(
            payload=payload,
            user_id=current_user.id if current_user is not None else None,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerMatchResponseView.model_validate(result)


@router.post("/events", response_model=PlayerMatchEventView, status_code=status.HTTP_201_CREATED)
def create_player_match_event(
    payload: PlayerMatchEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PlayerMatchEventView:
    service = PlayerMatchLearningService(session=session)
    try:
        event = service.track_event(
            user_id=current_user.id,
            player_id=payload.player_id,
            event_type=payload.event,
            filters=payload.filters,
            match_score=payload.match_score,
            reasons=payload.reasons,
            metadata=payload.metadata,
        )
    except PlayerMatchLearningError as exc:
        raise_player_match_learning_http_exception(exc)
    session.commit()
    session.refresh(event)
    return PlayerMatchEventView.model_validate(event)


@router.get("/me/match-profile", response_model=PlayerMatchProfileView)
def read_current_user_match_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PlayerMatchProfileView:
    service = PlayerMatchLearningService(session=session)
    payload = service.build_profile_payload(user_id=current_user.id)
    return PlayerMatchProfileView.model_validate(payload)


@router.get("", response_model=RealPlayerUniversePageView)
def list_players(
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0, deprecated=True),
    position: str | None = Query(default=None),
    country: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniversePageView:
    try:
        result = service.list_players(
            limit=limit,
            cursor=cursor,
            offset=offset,
            position=position,
            country=country,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=availability,
            search=search,
            sort=sort,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniversePageView.model_validate(result)


@router.get("/real-universe", response_model=RealPlayerUniverseListView)
def list_real_player_universe(
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0, deprecated=True),
    position: str | None = Query(default=None),
    country: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniverseListView:
    try:
        page = service.list_players(
            limit=limit,
            cursor=cursor,
            offset=offset,
            position=position,
            country=country,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=availability,
            search=search,
            sort=sort,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniverseListView.model_validate(_to_legacy_list_result(page))


@router.get("/real-universe/search", response_model=RealPlayerUniverseListView)
def search_real_player_universe(
    search: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0, deprecated=True),
    position: str | None = Query(default=None),
    country: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: RealPlayerUniverseQueryService = Depends(get_real_player_universe_query_service),
) -> RealPlayerUniverseListView:
    try:
        page = service.list_players(
            limit=limit,
            cursor=cursor,
            offset=offset,
            position=position,
            country=country,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=availability,
            search=search,
            sort=sort,
        )
    except RealPlayerUniverseError as exc:
        raise_real_player_http_exception(exc)
    return RealPlayerUniverseListView.model_validate(_to_legacy_list_result(page))


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


def _to_legacy_list_result(result) -> RealPlayerUniverseListResult:
    return RealPlayerUniverseListResult(
        items=result.items,
        limit=result.limit,
        offset=result.offset,
        total=result.total,
    )
