from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.simulation_matchmaking.schemas import (
    HostedCompetitionPreviewRequest,
    HostedCompetitionPreviewResponse,
    QuickGameRequest,
    QuickGameResponse,
    QuickTournamentRequest,
    QuickTournamentResponse,
    SimulationGameProfileInput,
    SimulationGameProfileView,
)
from app.simulation_matchmaking.service import (
    MatchmakingUnavailableError,
    ProfileNotFoundError,
    SimulationMatchmakingService,
)

router = APIRouter(tags=["simulation-matchmaking"])
legacy_router = APIRouter(prefix="/simulation-matchmaking")
api_router = APIRouter(prefix="/api/simulation-matchmaking")


def get_simulation_matchmaking_service(request: Request) -> SimulationMatchmakingService:
    service = getattr(request.app.state, "simulation_matchmaking_service", None)
    if service is None:
        service = SimulationMatchmakingService()
        request.app.state.simulation_matchmaking_service = service
    return service


@legacy_router.put("/profiles/{user_id}", response_model=SimulationGameProfileView)
@api_router.put("/profiles/{user_id}", response_model=SimulationGameProfileView)
def upsert_simulation_profile(
    user_id: str,
    payload: SimulationGameProfileInput,
    service: SimulationMatchmakingService = Depends(get_simulation_matchmaking_service),
) -> SimulationGameProfileView:
    if payload.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path user_id must match payload user_id.")
    return service.upsert_profile(payload)


@legacy_router.get("/profiles/{user_id}", response_model=SimulationGameProfileView)
@api_router.get("/profiles/{user_id}", response_model=SimulationGameProfileView)
def get_simulation_profile(
    user_id: str,
    service: SimulationMatchmakingService = Depends(get_simulation_matchmaking_service),
) -> SimulationGameProfileView:
    try:
        return service.get_profile(user_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@legacy_router.post("/quick-game", response_model=QuickGameResponse)
@api_router.post("/quick-game", response_model=QuickGameResponse)
def create_quick_game(
    payload: QuickGameRequest,
    service: SimulationMatchmakingService = Depends(get_simulation_matchmaking_service),
) -> QuickGameResponse:
    try:
        return service.create_quick_game(payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MatchmakingUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@legacy_router.post("/quick-tournament", response_model=QuickTournamentResponse)
@api_router.post("/quick-tournament", response_model=QuickTournamentResponse)
def create_quick_tournament(
    payload: QuickTournamentRequest,
    service: SimulationMatchmakingService = Depends(get_simulation_matchmaking_service),
) -> QuickTournamentResponse:
    try:
        return service.create_quick_tournament(payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MatchmakingUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@legacy_router.post("/hosted-competitions/preview", response_model=HostedCompetitionPreviewResponse)
@api_router.post("/hosted-competitions/preview", response_model=HostedCompetitionPreviewResponse)
def preview_hosted_competition(
    payload: HostedCompetitionPreviewRequest,
    service: SimulationMatchmakingService = Depends(get_simulation_matchmaking_service),
) -> HostedCompetitionPreviewResponse:
    try:
        return service.preview_hosted_competition(payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MatchmakingUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_simulation_matchmaking_service", "router"]
