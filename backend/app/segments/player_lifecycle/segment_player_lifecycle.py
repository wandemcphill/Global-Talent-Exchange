from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.schemas.player_lifecycle import (
    CareerEntryView,
    ContractView,
    InjuryCaseView,
    TransferBidCreateRequest,
    TransferBidView,
    TransferWindowView,
)
from backend.app.services.player_lifecycle_service import PlayerLifecycleService

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


@router.get("/api/players/{player_id}/career", response_model=list[CareerEntryView])
def get_player_career(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[CareerEntryView]:
    return [CareerEntryView.model_validate(item, from_attributes=True) for item in service.get_career(player_id)]


@router.get("/api/players/{player_id}/contracts", response_model=list[ContractView])
def get_player_contracts(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[ContractView]:
    return [ContractView.model_validate(item, from_attributes=True) for item in service.get_contracts(player_id)]


@router.get("/api/players/{player_id}/injuries", response_model=list[InjuryCaseView])
def get_player_injuries(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[InjuryCaseView]:
    return [InjuryCaseView.model_validate(item, from_attributes=True) for item in service.get_injuries(player_id)]


@router.get("/api/transfers/windows", response_model=list[TransferWindowView])
def list_transfer_windows(
    territory_code: str | None = Query(default=None),
    active_on: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> list[TransferWindowView]:
    return [TransferWindowView.model_validate(item, from_attributes=True) for item in service.list_transfer_windows(territory_code=territory_code, active_on=active_on)]


@router.get("/api/transfers/windows/{window_id}/bids", response_model=list[TransferBidView])
def list_transfer_window_bids(window_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[TransferBidView]:
    return [TransferBidView.model_validate(item, from_attributes=True) for item in service.list_window_bids(window_id)]


@router.post("/api/transfers/windows/{window_id}/bids", response_model=TransferBidView, status_code=status.HTTP_201_CREATED)
def create_transfer_bid(
    window_id: str,
    payload: TransferBidCreateRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> TransferBidView:
    result = service.create_bid(window_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transfer window {window_id} was not found")
    return TransferBidView.model_validate(result, from_attributes=True)
