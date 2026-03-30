from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.access_control import OrganizationRole, OrganizationType
from app.models.club_profile import ClubProfile
from app.models.user import User
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
    TransferMarketPermissionError,
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
    if isinstance(exc, TransferMarketPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, TransferMarketValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _require_transfer_market_club_access(
    *,
    access_service: AccessControlService,
    current_user: User,
    club_id: str,
) -> ClubProfile:
    try:
        return access_service.require_club_access(
            user=current_user,
            club_id=club_id,
            allowed_roles={OrganizationRole.CLUB, OrganizationRole.ADMIN},
            forbidden_detail="transfer_market_club_access_required",
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def _resolve_transfer_market_actor_club(
    *,
    request: Request,
    session: Session,
    current_user: User,
    requested_club_id: str | None = None,
) -> ClubProfile:
    access_service = AccessControlService(session)
    if requested_club_id:
        return _require_transfer_market_club_access(
            access_service=access_service,
            current_user=current_user,
            club_id=requested_club_id,
        )

    access_context = access_service.bind_user_access_context(current_user)
    candidate_club_ids: list[str] = []
    token_payload = getattr(request.state, "auth_token_payload", None)
    token_org_id = token_payload.get("org_id") if isinstance(token_payload, dict) else None
    if (
        isinstance(token_org_id, str)
        and token_org_id
        and any(
            membership.organization_id == token_org_id and membership.organization_type == OrganizationType.CLUB
            for membership in access_context.memberships
        )
    ):
        candidate_club_ids.append(token_org_id)
    for membership in access_context.memberships:
        if membership.organization_type == OrganizationType.CLUB and membership.organization_id not in candidate_club_ids:
            candidate_club_ids.append(membership.organization_id)
    for club_id in session.scalars(select(ClubProfile.id).where(ClubProfile.owner_user_id == current_user.id)).all():
        if club_id not in candidate_club_ids:
            candidate_club_ids.append(club_id)

    if not candidate_club_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="transfer_market_club_access_required")
    if len(candidate_club_ids) > 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="transfer_market_club_context_required")
    return _require_transfer_market_club_access(
        access_service=access_service,
        current_user=current_user,
        club_id=candidate_club_ids[0],
    )


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
    current_user: User = Depends(get_current_user),
) -> TransferListingView:
    try:
        return service.create_listing(payload, actor=current_user, selling_club_id=payload.selling_club_id)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
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
    current_user: User = Depends(get_current_user),
) -> TransferListingView:
    try:
        return service.place_bid(
            listing_id,
            actor=current_user,
            bidder_club_id=payload.bidder_club_id,
            amount=payload.amount,
            activity_context=payload.activity_context,
        )
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/listings/{listing_id}/close", response_model=TransferListingView)
def close_transfer_market_listing(
    listing_id: str,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferListingView:
    try:
        return service.finalize_listing(listing_id, actor=current_user)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.get("/api/transfer-market/listings/{listing_id}/negotiation", response_model=TransferNegotiationView)
def get_transfer_market_negotiation(
    listing_id: str,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferNegotiationView:
    try:
        return service.get_negotiation(listing_id, actor=current_user)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/listings/{listing_id}/contract-offer", response_model=TransferNegotiationView)
def submit_transfer_market_contract_offer(
    listing_id: str,
    payload: ContractOfferRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferNegotiationView:
    try:
        return service.submit_contract_offer(
            listing_id,
            payload,
            actor=current_user,
            bidder_club_id=payload.bidder_club_id,
        )
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/players/{player_id}/decision-profile", response_model=PlayerDecisionProfileView)
def upsert_transfer_market_player_profile(
    request: Request,
    player_id: str,
    payload: PlayerDecisionProfileUpsertRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> PlayerDecisionProfileView:
    try:
        player_club = service.get_current_player_club(player_id)
        _resolve_transfer_market_actor_club(
            request=request,
            session=service.session,
            current_user=current_user,
            requested_club_id=player_club.id,
        )
        return service.upsert_player_decision_profile(player_id, payload)
    except (TransferMarketNotFoundError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/coaches/{club_id}/profile", response_model=CoachProfileView)
def upsert_transfer_market_coach_profile(
    club_id: str,
    payload: CoachProfileUpsertRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoachProfileView:
    try:
        return service.upsert_coach_profile(club_id, payload, actor=current_user)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/coaches/{club_id}/demands", response_model=CoachDemandView, status_code=status.HTTP_201_CREATED)
def create_transfer_market_coach_demand(
    club_id: str,
    payload: CoachDemandCreateRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoachDemandView:
    try:
        return service.create_coach_demand(club_id, payload, actor=current_user)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.put("/api/transfer-market/clubs/{club_id}/team-dynamics", response_model=ClubTeamDynamicsView)
def upsert_transfer_market_team_dynamics(
    club_id: str,
    payload: TeamDynamicsUpsertRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> ClubTeamDynamicsView:
    try:
        return service.upsert_team_dynamics(club_id, payload, actor=current_user)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/watchlist", response_model=MarketWatchlistEntryView, status_code=status.HTTP_201_CREATED)
def add_transfer_market_watchlist_entry(
    payload: WatchlistEntryCreateRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> MarketWatchlistEntryView:
    try:
        return service.add_watchlist_entry(payload, actor=current_user, club_id=payload.club_id)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
        _raise_transfer_market_error(exc)


@router.post("/api/transfer-market/jobs/run", response_model=TransferMarketJobRunView)
def run_transfer_market_jobs(
    payload: TransferMarketJobRunRequest,
    service: TransferMarketService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> TransferMarketJobRunView:
    try:
        return service.run_background_jobs(actor=current_user, reference_at=payload.reference_at)
    except (TransferMarketNotFoundError, TransferMarketPermissionError, TransferMarketValidationError) as exc:
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
