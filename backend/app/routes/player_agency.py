from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
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
        return service.get_snapshot(player_id, reference_on=as_of)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/players/{player_id}/agency/contract-decision", response_model=ContractDecisionView)
def evaluate_contract_decision(
    player_id: str,
    payload: ContractDecisionRequest,
    service: PlayerAgencyService = Depends(_service),
) -> ContractDecisionView:
    try:
        return service.evaluate_contract_offer(player_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/players/{player_id}/agency/transfer-decision", response_model=TransferDecisionView)
def evaluate_transfer_decision(
    player_id: str,
    payload: TransferDecisionRequest,
    service: PlayerAgencyService = Depends(_service),
) -> TransferDecisionView:
    try:
        return service.evaluate_transfer_opportunity(player_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
