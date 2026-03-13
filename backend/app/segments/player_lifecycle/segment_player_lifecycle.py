from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.schemas.player_lifecycle import (
    CareerEntryView,
    ContractCreateRequest,
    ContractRenewRequest,
    ContractSummaryView,
    ContractView,
    InjuryCaseView,
    InjuryCreateRequest,
    InjuryRecoveryRequest,
    PlayerAvailabilityView,
    PlayerCareerSummaryView,
    PlayerLifecycleEventView,
    PlayerOverviewView,
    PlayerLifecycleSnapshotView,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
    TransferBidView,
    TransferWindowView,
)
from backend.app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


def _raise_for_lifecycle_error(exc: Exception) -> None:
    if isinstance(exc, PlayerLifecycleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PlayerLifecycleValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/api/players/{player_id}/career", response_model=list[CareerEntryView])
def get_player_career(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[CareerEntryView]:
    return [service.to_career_entry_view(item) for item in service.get_career(player_id)]


@router.get("/api/players/{player_id}/career/summary", response_model=PlayerCareerSummaryView)
def get_player_career_summary(
    player_id: str,
    as_of: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> PlayerCareerSummaryView:
    try:
        return service.get_career_summary(player_id, on_date=as_of)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/players/{player_id}/overview", response_model=PlayerOverviewView)
def get_player_overview(
    player_id: str,
    as_of: date | None = Query(default=None),
    territory_code: str | None = Query(default=None),
    event_limit: int = Query(default=8, ge=1, le=50),
    service: PlayerLifecycleService = Depends(_service),
) -> PlayerOverviewView:
    try:
        return service.get_player_overview(
            player_id,
            on_date=as_of,
            territory_code=territory_code,
            event_limit=event_limit,
        )
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/players/{player_id}/lifecycle-snapshot", response_model=PlayerLifecycleSnapshotView)
def get_player_lifecycle_snapshot(
    player_id: str,
    as_of: date | None = Query(default=None),
    territory_code: str | None = Query(default=None),
    event_limit: int = Query(default=8, ge=1, le=50),
    service: PlayerLifecycleService = Depends(_service),
) -> PlayerLifecycleSnapshotView:
    try:
        return service.get_player_lifecycle_snapshot(
            player_id,
            on_date=as_of,
            territory_code=territory_code,
            event_limit=event_limit,
        )
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/players/{player_id}/events", response_model=list[PlayerLifecycleEventView])
def get_player_lifecycle_events(
    player_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: PlayerLifecycleService = Depends(_service),
) -> list[PlayerLifecycleEventView]:
    try:
        return [
            service.to_event_view(event)
            for event in service.list_events(player_id, limit=limit)
        ]
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/players/{player_id}/contracts", response_model=list[ContractView])
def get_player_contracts(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[ContractView]:
    reference_on = date.today()
    return [service.to_contract_view(item, reference_on=reference_on) for item in service.get_contracts(player_id)]


@router.get("/api/players/{player_id}/contracts/summary", response_model=ContractSummaryView | None)
def get_player_contract_summary(
    player_id: str,
    as_of: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> ContractSummaryView | None:
    try:
        return service.get_contract_summary(player_id, on_date=as_of)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/clubs/{club_id}/contracts", response_model=list[ContractView])
def get_club_contracts(club_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[ContractView]:
    reference_on = date.today()
    return [service.to_contract_view(item, reference_on=reference_on) for item in service.get_club_contracts(club_id)]


@router.post("/api/players/{player_id}/contracts", response_model=ContractView, status_code=status.HTTP_201_CREATED)
def create_player_contract(
    player_id: str,
    payload: ContractCreateRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> ContractView:
    try:
        return service.to_contract_view(service.create_contract(player_id, payload), reference_on=date.today())
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.post("/api/players/{player_id}/contracts/{contract_id}/renew", response_model=ContractView)
def renew_player_contract(
    player_id: str,
    contract_id: str,
    payload: ContractRenewRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> ContractView:
    try:
        return service.to_contract_view(service.renew_contract(player_id, contract_id, payload), reference_on=date.today())
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/players/{player_id}/injuries", response_model=list[InjuryCaseView])
def get_player_injuries(player_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[InjuryCaseView]:
    return [service.to_injury_view(item) for item in service.get_injuries(player_id)]


@router.get("/api/players/{player_id}/availability", response_model=PlayerAvailabilityView)
def get_player_availability(
    player_id: str,
    on_date: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> PlayerAvailabilityView:
    try:
        return service.get_player_availability(player_id, on_date=on_date)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.post("/api/players/{player_id}/injuries", response_model=InjuryCaseView, status_code=status.HTTP_201_CREATED)
def create_player_injury(
    player_id: str,
    payload: InjuryCreateRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> InjuryCaseView:
    try:
        return service.to_injury_view(service.create_injury_case(player_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.post("/api/players/{player_id}/injuries/{injury_id}/recover", response_model=InjuryCaseView)
def recover_player_injury(
    player_id: str,
    injury_id: str,
    payload: InjuryRecoveryRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> InjuryCaseView:
    try:
        return service.to_injury_view(service.recover_injury(player_id, injury_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/transfers/windows", response_model=list[TransferWindowView])
def list_transfer_windows(
    territory_code: str | None = Query(default=None),
    active_on: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> list[TransferWindowView]:
    reference_on = active_on or date.today()
    return [service.to_transfer_window_view(item, reference_on=reference_on) for item in service.list_transfer_windows(territory_code=territory_code, active_on=active_on)]


@router.get("/api/transfers/windows/{window_id}", response_model=TransferWindowView)
def get_transfer_window(
    window_id: str,
    on_date: date | None = Query(default=None),
    service: PlayerLifecycleService = Depends(_service),
) -> TransferWindowView:
    try:
        return service.to_transfer_window_view(service.get_transfer_window(window_id), reference_on=on_date or date.today())
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.get("/api/transfers/windows/{window_id}/bids", response_model=list[TransferBidView])
def list_transfer_window_bids(window_id: str, service: PlayerLifecycleService = Depends(_service)) -> list[TransferBidView]:
    return [service.to_transfer_bid_view(item) for item in service.list_window_bids(window_id)]


@router.post("/api/transfers/windows/{window_id}/bids", response_model=TransferBidView, status_code=status.HTTP_201_CREATED)
def create_transfer_bid(
    window_id: str,
    payload: TransferBidCreateRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> TransferBidView:
    try:
        return service.to_transfer_bid_view(service.create_bid(window_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.post("/api/transfers/windows/{window_id}/bids/{bid_id}/accept", response_model=TransferBidView)
def accept_transfer_bid(
    window_id: str,
    bid_id: str,
    payload: TransferBidAcceptRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> TransferBidView:
    try:
        return service.to_transfer_bid_view(service.accept_bid(window_id, bid_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)


@router.post("/api/transfers/windows/{window_id}/bids/{bid_id}/reject", response_model=TransferBidView)
def reject_transfer_bid(
    window_id: str,
    bid_id: str,
    payload: TransferBidRejectRequest,
    service: PlayerLifecycleService = Depends(_service),
) -> TransferBidView:
    try:
        return service.to_transfer_bid_view(service.reject_bid(window_id, bid_id, payload))
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)
