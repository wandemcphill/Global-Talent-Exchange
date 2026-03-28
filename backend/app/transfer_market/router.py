from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.transfer_market.schemas import (
    ClubTeamDynamicsView,
    CoachDemandCreateRequest,
    CoachDemandView,
    CoachProfileUpsertRequest,
    CoachProfileView,
    ContractOfferRequest,
    MarketWatchlistEntryView,
    PlayerDecisionProfileUpsertRequest,
    PlayerDecisionProfileView,
    TeamDynamicsUpsertRequest,
    TransferBidPlaceRequest,
    TransferListingCreateRequest,
    TransferListingView,
    TransferMarketJobRunRequest,
    TransferMarketJobRunView,
    TransferNegotiationView,
    WatchlistEntryCreateRequest,
)
from app.transfer_market.service import (
    TransferMarketNotFoundError,
    TransferMarketService,
    TransferMarketValidationError,
    ensure_transfer_market_hub,
)

router = APIRouter(tags=["transfer-market"])


def _service(request: Request, session: Session = Depends(get_session)) -> TransferMarketService:
    hub = ensure_transfer_market_hub(request.app)
    event_publisher = getattr(request.app.state, "event_publisher", None)
    return TransferMarketService(session, event_publisher=event_publisher, hub=hub)


def _raise_transfer_market_error(exc: Exception) -> None:
    if isinstance(exc, TransferMarketNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, TransferMarketValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/api/transfer-market/listings", response_model=list[TransferListingView])
def list_transfer_market_listings(
    status_filter: str | None = Query(default=None, alias="status"),
    player_id: str | None = Query(default=None),
    club_id: str | None = Query(default=None),
    service: TransferMarketService = Depends(_service),
) -> list[TransferListingView]:
    return service.list_listings(status=status_filter, player_id=player_id, club_id=club_id)


@router.post("/api/transfer-market/listings", response_model=TransferListingView, status_code=status.HTTP_201_CREATED)
def create_transfer_market_listing(
    payload: TransferListingCreateRequest,
    service: TransferMarketService = Depends(_service),
) -> TransferListingView:
    try:
        return service.create_listing(payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.get("/api/transfer-market/listings/{listing_id}", response_model=TransferListingView)
def get_transfer_market_listing(listing_id: str, service: TransferMarketService = Depends(_service)) -> TransferListingView:
    try:
        return service.get_listing(listing_id)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/listings/{listing_id}/bids", response_model=TransferListingView)
def place_transfer_market_bid(
    listing_id: str,
    payload: TransferBidPlaceRequest,
    service: TransferMarketService = Depends(_service),
) -> TransferListingView:
    try:
        return service.place_bid(
            listing_id,
            bidder_club_id=payload.bidder_club_id,
            amount=payload.amount,
            activity_context=payload.activity_context,
        )
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/listings/{listing_id}/close", response_model=TransferListingView)
def close_transfer_market_listing(listing_id: str, service: TransferMarketService = Depends(_service)) -> TransferListingView:
    try:
        return service.finalize_listing(listing_id)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.get("/api/transfer-market/listings/{listing_id}/negotiation", response_model=TransferNegotiationView)
def get_transfer_market_negotiation(
    listing_id: str,
    service: TransferMarketService = Depends(_service),
) -> TransferNegotiationView:
    try:
        return service.get_negotiation(listing_id)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/listings/{listing_id}/contract-offer", response_model=TransferNegotiationView)
def submit_transfer_market_contract_offer(
    listing_id: str,
    payload: ContractOfferRequest,
    service: TransferMarketService = Depends(_service),
) -> TransferNegotiationView:
    try:
        return service.submit_contract_offer(listing_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/players/{player_id}/decision-profile", response_model=PlayerDecisionProfileView)
def upsert_transfer_market_player_profile(
    player_id: str,
    payload: PlayerDecisionProfileUpsertRequest,
    service: TransferMarketService = Depends(_service),
) -> PlayerDecisionProfileView:
    try:
        return service.upsert_player_decision_profile(player_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/coaches/{club_id}/profile", response_model=CoachProfileView)
def upsert_transfer_market_coach_profile(
    club_id: str,
    payload: CoachProfileUpsertRequest,
    service: TransferMarketService = Depends(_service),
) -> CoachProfileView:
    try:
        return service.upsert_coach_profile(club_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/coaches/{club_id}/demands", response_model=CoachDemandView, status_code=status.HTTP_201_CREATED)
def create_transfer_market_coach_demand(
    club_id: str,
    payload: CoachDemandCreateRequest,
    service: TransferMarketService = Depends(_service),
) -> CoachDemandView:
    try:
        return service.create_coach_demand(club_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/clubs/{club_id}/team-dynamics", response_model=ClubTeamDynamicsView)
def upsert_transfer_market_team_dynamics(
    club_id: str,
    payload: TeamDynamicsUpsertRequest,
    service: TransferMarketService = Depends(_service),
) -> ClubTeamDynamicsView:
    try:
        return service.upsert_team_dynamics(club_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/watchlist", response_model=MarketWatchlistEntryView, status_code=status.HTTP_201_CREATED)
def add_transfer_market_watchlist_entry(
    payload: WatchlistEntryCreateRequest,
    service: TransferMarketService = Depends(_service),
) -> MarketWatchlistEntryView:
    try:
        return service.add_watchlist_entry(payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/jobs/run", response_model=TransferMarketJobRunView)
def run_transfer_market_jobs(
    payload: TransferMarketJobRunRequest,
    service: TransferMarketService = Depends(_service),
) -> TransferMarketJobRunView:
    try:
        return service.run_background_jobs(reference_at=payload.reference_at)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.websocket("/api/transfer-market/listings/{listing_id}/stream")
async def stream_transfer_market_listing(listing_id: str, websocket: WebSocket) -> None:
    app = websocket.scope["app"]
    hub = ensure_transfer_market_hub(app)
    state = hub.get_state(listing_id)
    if state is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    cursor = 0
    try:
        while True:
            state = hub.get_state(listing_id)
            if state is None:
                break
            if state.snapshot is not None:
                await websocket.send_json(
                    {
                        "channel": state.channel,
                        "kind": "timer",
                        "payload": {"time_remaining": state.snapshot.time_remaining, "status": state.status},
                    }
                )
                await websocket.send_json(
                    {
                        "channel": state.channel,
                        "kind": "snapshot",
                        "payload": state.snapshot.model_dump(mode="json"),
                    }
                )
            events, cursor = hub.get_events_since(listing_id, cursor)
            if events:
                await websocket.send_json(
                    {
                        "channel": state.channel,
                        "kind": "events",
                        "payload": [event.model_dump(mode="json") for event in events],
                    }
                )
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    await websocket.close()


__all__ = ["router"]
