from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.admin_godmode.service import AdminGodModeService, PermissionDeniedError
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
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
from app.players.token_schemas import (
    PlayerShareDividendRequest,
    PlayerShareDividendView,
    PlayerShareEventView,
    PlayerShareHoldingView,
    PlayerShareMarketIssueRequest,
    PlayerShareMarketView,
    PlayerSharePerformanceRequest,
    PlayerSharePurchaseRequest,
    PlayerSharePurchaseView,
)
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.players.service import PlayerSummaryQueryService
from app.regen_universe.expansion_service import (
    RegenUniverseExpansionError,
    RegenUniverseExpansionNotFoundError,
    RegenUniverseExpansionService,
    RegenUniverseExpansionValidationError,
)
from app.schemas.avatar import PlayerAvatarRenderView
from app.schemas.regen_universe_expansion import PlayerDNAView, PlayerRivalryView, PlayerStoryView
from app.services.player_face_service import PlayerFaceError, PlayerFaceNotFoundError, PlayerFaceService
from app.wallets.service import WalletService

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


def raise_player_face_http_exception(exc: PlayerFaceError) -> Never:
    if isinstance(exc, PlayerFaceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def raise_player_token_market_http_exception(exc: PlayerTokenMarketError) -> Never:
    if exc.reason in {"player_not_found", "market_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if exc.reason in {
        "admin_required",
        "total_shares_invalid",
        "share_price_invalid",
        "share_count_invalid",
        "market_inactive",
        "share_supply_insufficient",
        "multiplier_invalid",
        "dividend_invalid",
        "no_shareholders",
        "no_circulation",
        "total_shares_below_circulation",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


def _require_manager_supply_permission(request: Request, actor: User) -> None:
    service = AdminGodModeService(
        wallet_service=WalletService(
            cache_backend=getattr(request.app.state, "cache_backend", None)
        )
    )
    try:
        state = service._load_state(request.app)
        profile = service.resolve_profile(actor, state)
        service._assert_has_permission(profile, "manage_manager_supply")
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


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


@router.get("/{player_id}/shares/market", response_model=PlayerShareMarketView)
def get_player_share_market(
    player_id: str,
    session: Session = Depends(get_session),
) -> PlayerShareMarketView:
    try:
        market = PlayerTokenMarketService(session).get_market(player_id=player_id)
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    return PlayerShareMarketView.model_validate(market)


@router.get("/{player_id}/shares/events", response_model=list[PlayerShareEventView])
def list_player_share_events(
    player_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[PlayerShareEventView]:
    try:
        events = PlayerTokenMarketService(session).list_events(player_id=player_id, limit=limit)
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    return [PlayerShareEventView.model_validate(item) for item in events]


@router.get("/me/shares/holdings", response_model=list[PlayerShareHoldingView])
def list_my_player_share_holdings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[PlayerShareHoldingView]:
    holdings = PlayerTokenMarketService(session).list_holdings(user_id=current_user.id)
    return [PlayerShareHoldingView.model_validate(item) for item in holdings]


@router.post("/{player_id}/shares/issue", response_model=PlayerShareMarketView)
def issue_player_share_market(
    player_id: str,
    payload: PlayerShareMarketIssueRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> PlayerShareMarketView:
    _require_manager_supply_permission(request, actor)
    service = PlayerTokenMarketService(session)
    try:
        market = service.issue_market(
            actor=actor,
            player_id=player_id,
            total_shares=payload.total_shares,
            share_price_coin=payload.share_price_coin,
            status=payload.status,
        )
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    session.commit()
    session.refresh(market)
    return PlayerShareMarketView.model_validate(market)


@router.post("/{player_id}/shares/buy", response_model=PlayerSharePurchaseView, status_code=status.HTTP_201_CREATED)
def buy_player_shares(
    player_id: str,
    payload: PlayerSharePurchaseRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
) -> PlayerSharePurchaseView:
    service = PlayerTokenMarketService(session)
    try:
        result = service.buy_shares(actor=actor, player_id=player_id, share_count=payload.share_count)
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    session.commit()
    session.refresh(result["market"])
    session.refresh(result["holding"])
    return PlayerSharePurchaseView(
        market=PlayerShareMarketView.model_validate(result["market"]),
        holding=PlayerShareHoldingView.model_validate(result["holding"]),
        transaction_id=result["transaction_id"],
        gross_amount_coin=result["gross_amount_coin"],
    )


@router.post("/{player_id}/shares/performance", response_model=PlayerShareMarketView)
def reprice_player_shares_from_performance(
    player_id: str,
    payload: PlayerSharePerformanceRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> PlayerShareMarketView:
    _require_manager_supply_permission(request, actor)
    service = PlayerTokenMarketService(session)
    try:
        market = service.apply_performance_adjustment(
            actor=actor,
            player_id=player_id,
            multiplier=payload.multiplier,
            reason=payload.reason,
        )
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    session.commit()
    session.refresh(market)
    return PlayerShareMarketView.model_validate(market)


@router.post("/{player_id}/shares/dividends", response_model=PlayerShareDividendView)
def distribute_player_share_dividends(
    player_id: str,
    payload: PlayerShareDividendRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> PlayerShareDividendView:
    _require_manager_supply_permission(request, actor)
    service = PlayerTokenMarketService(session)
    try:
        result = service.distribute_dividend(
            actor=actor,
            player_id=player_id,
            gross_amount_coin=payload.gross_amount_coin,
            note=payload.note,
        )
    except PlayerTokenMarketError as exc:
        raise_player_token_market_http_exception(exc)
    session.commit()
    session.refresh(result["market"])
    return PlayerShareDividendView(
        market=PlayerShareMarketView.model_validate(result["market"]),
        transaction_id=result["transaction_id"],
        gross_amount_coin=result["gross_amount_coin"],
    )


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


@router.get("/{player_id}/avatar", response_model=PlayerAvatarRenderView)
def get_player_avatar(
    player_id: str,
    format: str = Query(default="json"),
    session: Session = Depends(get_session),
) -> PlayerAvatarRenderView | Response:
    if format not in {"json", "svg", "static", "model"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported avatar format.")
    try:
        payload = PlayerFaceService(session).get_avatar_render(player_id, render_format=format)
    except PlayerFaceError as exc:
        raise_player_face_http_exception(exc)
    session.commit()
    if format == "svg":
        return Response(content=payload.layered_svg or "", media_type="image/svg+xml")
    return payload


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
