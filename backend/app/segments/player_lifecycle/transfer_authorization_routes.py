from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.transfer_bid import TransferBid
from app.models.user import User
from app.schemas.player_lifecycle import (
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
    TransferBidView,
)
from app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


def _require_club_owner(session: Session, club_id: str | None, user: User, *, action: str) -> None:
    if not club_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{action} requires a club")
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Club profile {club_id} was not found")
    if club.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not control this club")


def _raise(exc: Exception) -> None:
    if isinstance(exc, PlayerLifecycleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/api/transfers/windows/{window_id}/bids",
    response_model=TransferBidView,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer_bid_authorized(
    window_id: str,
    payload: TransferBidCreateRequest,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    _require_club_owner(service.session, payload.buying_club_id, current_user, action="Creating a transfer bid")
    try:
        return service.to_transfer_bid_view(service.create_bid(window_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise(exc)


@router.post("/api/transfers/windows/{window_id}/bids/{bid_id}/accept", response_model=TransferBidView)
def accept_transfer_bid_authorized(
    window_id: str,
    bid_id: str,
    payload: TransferBidAcceptRequest,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    bid = service.session.get(TransferBid, bid_id)
    if bid is None or bid.window_id != window_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transfer bid {bid_id} was not found")
    _require_club_owner(service.session, bid.selling_club_id, current_user, action="Accepting a transfer bid")
    try:
        return service.to_transfer_bid_view(service.accept_bid(window_id, bid_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise(exc)


@router.post("/api/transfers/windows/{window_id}/bids/{bid_id}/reject", response_model=TransferBidView)
def reject_transfer_bid_authorized(
    window_id: str,
    bid_id: str,
    payload: TransferBidRejectRequest,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    bid = service.session.get(TransferBid, bid_id)
    if bid is None or bid.window_id != window_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transfer bid {bid_id} was not found")
    _require_club_owner(service.session, bid.selling_club_id, current_user, action="Rejecting a transfer bid")
    try:
        return service.to_transfer_bid_view(service.reject_bid(window_id, bid_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise(exc)
