from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.player_lifecycle import TransferBidView
from app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)
from app.services.regen_contract_offer_service import accept_regen_contract_offer

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


@router.post(
    "/api/players/{player_id}/regen/contract-offers/{offer_id}/accept",
    response_model=TransferBidView,
)
def accept_regen_contract_offer_endpoint(
    player_id: str,
    offer_id: str,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    try:
        accepted_bid = accept_regen_contract_offer(
            service.session,
            player_id=player_id,
            offer_id=offer_id,
            actor=current_user,
        )
        return service.to_transfer_bid_view(accepted_bid)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        if isinstance(exc, PlayerLifecycleNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
