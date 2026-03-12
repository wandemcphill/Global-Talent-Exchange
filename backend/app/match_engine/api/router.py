from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.match_engine.schemas import MatchEventTimelineView, MatchFinalSummaryView, MatchReplayPayloadView, MatchSimulationRequest
from backend.app.match_engine.services.match_simulation_service import MatchSimulationService

router = APIRouter(tags=["match-engine"])
legacy_router = APIRouter(prefix="/match-engine")
api_router = APIRouter(prefix="/api/match-engine")


def get_match_simulation_service() -> MatchSimulationService:
    return MatchSimulationService()


@legacy_router.post("/replay", response_model=MatchReplayPayloadView)
@api_router.post("/replay", response_model=MatchReplayPayloadView)
def create_match_replay(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchReplayPayloadView:
    return service.build_replay_payload(payload)


@legacy_router.post("/timeline", response_model=MatchEventTimelineView)
@api_router.post("/timeline", response_model=MatchEventTimelineView)
def create_match_timeline(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchEventTimelineView:
    return service.build_timeline(payload)


@legacy_router.post("/summary", response_model=MatchFinalSummaryView)
@api_router.post("/summary", response_model=MatchFinalSummaryView)
def create_match_summary(
    payload: MatchSimulationRequest,
    service: MatchSimulationService = Depends(get_match_simulation_service),
) -> MatchFinalSummaryView:
    return service.build_summary(payload)


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_match_simulation_service", "router"]
