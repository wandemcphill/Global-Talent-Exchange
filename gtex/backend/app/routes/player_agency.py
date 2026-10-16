from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.player_agency import (
    ContractDecisionRequest,
    ContractDecisionView,
    PlayerAgencySnapshotView,
    TransferDecisionRequest,
    TransferDecisionView,
)
from app.services.player_agency_service import PlayerAgencyService

router = APIRouter(tags=["player-agency"])


def _service(session: Session = Depends(get_session)) -> PlayerAgencyService:
    return PlayerAgencyService(session)


@router.get("/api/players/{player_id}/agency", response_model=PlayerAgencySnapshotView)
def get_player_agency_snapshot(
    player_id: str,
    as_of: date | None = Query(default=None),
    service: PlayerAgencyService = Depends(_service),
) -> PlayerAgencySnapshotView:
    try:
        return service.get_agency_profile(player_id, reference_on=as_of)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/players/{player_id}/agency/contract-decision", response_model=ContractDecisionView)
def evaluate_contract_decision(
    player_id: str,
    payload: ContractDecisionRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerAgencyService = Depends(_service),
) -> ContractDecisionView:
    # Not just a read-only preview: evaluate_contract_decision mutates the player's
    # persistent agent state (contract_stance, cooldowns, cached decision) via
    # PlayerAgencyService, the same engine the authenticated transfer/contract flows
    # in player_lifecycle_service.py and transfer_market/service.py use for real
    # offers. Requiring an authenticated caller here closes an anonymous write path
    # onto shared player state; a fabricated offer submitted by anyone could still
    # perturb a real player's negotiation history and cooldown timers.
    del current_user
    try:
        return service.evaluate_contract_decision(player_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/players/{player_id}/agency/transfer-decision", response_model=TransferDecisionView)
def evaluate_transfer_decision(
    player_id: str,
    payload: TransferDecisionRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerAgencyService = Depends(_service),
) -> TransferDecisionView:
    # See evaluate_contract_decision above: same engine, same write to persistent
    # player agent state (cooldowns, transfer_appetite, cached decision), same reason
    # to require an authenticated caller rather than accept anonymous input.
    del current_user
    try:
        return service.evaluate_transfer_decision(player_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
