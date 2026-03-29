from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_match_user, get_current_user, get_optional_current_user, get_session
from app.gtex.runtime import ensure_gtex_runtime
from app.gtex.schemas import (
    AiLeaguesView,
    AiLeagueView,
    AiMatchView,
    CreatorPlayerView,
    CreatorTradeRequest,
    CreatorTradeView,
    JackpotContributionRequest,
    JackpotContributionView,
    JackpotHistoryItemView,
    JackpotPayoutView,
    JackpotStateView,
    MarketTrendingView,
    MatchFindRequest,
    MatchFindResponse,
)
from app.gtex.service import GtexConflictError, GtexError, GtexNotFoundError, GtexValidationError
from app.models.user import User

router = APIRouter(tags=["gtex"])


def get_runtime(request: Request):
    return ensure_gtex_runtime(request.app)


def raise_gtex_http_exception(exc: GtexError) -> Never:
    if isinstance(exc, GtexNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, GtexConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, GtexValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/jackpot/state", response_model=JackpotStateView)
def get_jackpot_state(
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotStateView:
    return JackpotStateView.model_validate(runtime.jackpot.get_state(session))


@router.post("/jackpot/contribute", response_model=JackpotContributionView, status_code=status.HTTP_201_CREATED)
def create_jackpot_contribution(
    payload: JackpotContributionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> JackpotContributionView:
    try:
        contribution = runtime.jackpot.contribute_from_wallet(
            session,
            actor=current_user,
            source_type=payload.source_type,
            source_id=payload.source_id,
            entry_fee=payload.entry_fee,
            eligibility_score=payload.eligibility_score,
            metadata=payload.metadata,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return JackpotContributionView.model_validate(contribution)


@router.get("/jackpot/history", response_model=list[JackpotHistoryItemView])
def get_jackpot_history(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> list[JackpotHistoryItemView]:
    items = []
    for round_record in runtime.jackpot.list_history(session, limit=limit):
        items.append(
            JackpotHistoryItemView(
                id=round_record.id,
                round_number=round_record.round_number,
                status=round_record.status.value,
                distribution_mode=round_record.distribution_mode.value,
                trigger_mode=round_record.trigger_mode.value if round_record.trigger_mode else None,
                current_balance=round_record.current_balance,
                winning_user_id=round_record.winning_user_id,
                triggered_at=round_record.triggered_at,
                settled_at=round_record.settled_at,
                payouts=[
                    JackpotPayoutView.model_validate(payout)
                    for payout in sorted(round_record.payouts, key=lambda item: item.rank)
                ],
            )
        )
    return items


@router.get("/players/{player_id}", response_model=CreatorPlayerView)
def get_creator_player(
    player_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> CreatorPlayerView:
    try:
        return CreatorPlayerView.model_validate(
            runtime.creator_market.get_view(session, player_id=player_id, viewer=current_user)
        )
    except GtexError as exc:
        raise_gtex_http_exception(exc)


@router.post("/market/buy", response_model=CreatorTradeView, status_code=status.HTTP_201_CREATED)
def buy_creator_shares(
    payload: CreatorTradeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CreatorTradeView:
    try:
        trade = runtime.creator_market.buy_shares(
            session,
            buyer=current_user,
            player_id=payload.player_id,
            shares=payload.shares,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return CreatorTradeView.model_validate(trade)


@router.post("/market/sell", response_model=CreatorTradeView, status_code=status.HTTP_201_CREATED)
def sell_creator_shares(
    payload: CreatorTradeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CreatorTradeView:
    try:
        trade = runtime.creator_market.sell_shares(
            session,
            seller=current_user,
            player_id=payload.player_id,
            shares=payload.shares,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return CreatorTradeView.model_validate(trade)


@router.get("/market/trending", response_model=MarketTrendingView)
def get_market_trending(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> MarketTrendingView:
    return MarketTrendingView(items=[CreatorPlayerView.model_validate(item) for item in runtime.creator_market.list_trending(session, limit=limit, viewer=current_user)])


@router.post("/match/find", response_model=MatchFindResponse, status_code=status.HTTP_202_ACCEPTED)
def find_match(
    payload: MatchFindRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_match_user),
    runtime=Depends(get_runtime),
) -> MatchFindResponse:
    try:
        queue_entry = runtime.ai_leagues.queue_match_request(
            session,
            user=current_user,
            league_ref=payload.league_id,
            entry_fee=payload.entry_fee,
            metadata=payload.metadata,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return MatchFindResponse(
        queue_entry_id=queue_entry.id,
        match_id=queue_entry.match_id,
        status=queue_entry.status.value,
        league_id=queue_entry.league_id,
        expires_at=queue_entry.expires_at,
    )


@router.get("/ai/leagues", response_model=AiLeaguesView)
def list_ai_leagues(
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> AiLeaguesView:
    leagues = [AiLeagueView.model_validate(item) for item in runtime.ai_leagues.list_leagues(session)]
    return AiLeaguesView(leagues=leagues)


@router.get("/ai/match/{match_id}", response_model=AiMatchView)
def get_ai_match(
    match_id: str,
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> AiMatchView:
    try:
        return AiMatchView.model_validate(runtime.ai_leagues.get_match_view(session, match_id=match_id))
    except GtexError as exc:
        raise_gtex_http_exception(exc)
