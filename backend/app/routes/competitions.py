from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.competitions.schemas import (
    CompetitionBracketContract,
    CompetitionFixturesContract,
    CompetitionStandingsContract,
)
from app.competitions.router import router as competition_control_router
from app.segments.competitions.segment_competitions import admin_router as competition_admin_segment_router
from app.segments.competitions.segment_competitions import router as competition_segment_router
from app.services.competition_orchestrator import CompetitionOrchestrator, get_competition_orchestrator

router = APIRouter()
competition_contract_router = APIRouter(prefix="/api/competitions", tags=["competitions"])


@competition_contract_router.get(
    "/{competition_id}/fixtures",
    response_model=CompetitionFixturesContract,
    response_model_exclude_none=True,
)
def get_competition_fixtures_contract(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionFixturesContract:
    result = orchestrator.fixtures_contract(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@competition_contract_router.get(
    "/{competition_id}/standings",
    response_model=CompetitionStandingsContract,
    response_model_exclude_none=True,
)
def get_competition_standings_contract(
    competition_id: str,
    group_key: str | None = Query(default=None),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionStandingsContract:
    result = orchestrator.standings_contract(competition_id, group_key=group_key)
    if result is None:
        raise _not_found(competition_id)
    return result


@competition_contract_router.get(
    "/{competition_id}/rounds",
    response_model=CompetitionBracketContract,
    response_model_exclude_none=True,
)
def get_competition_rounds_contract(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionBracketContract:
    result = orchestrator.bracket_contract(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@competition_contract_router.get(
    "/{competition_id}/bracket",
    response_model=CompetitionBracketContract,
    response_model_exclude_none=True,
)
def get_competition_bracket_contract(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionBracketContract:
    result = orchestrator.bracket_contract(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


def _not_found(competition_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Competition {competition_id} was not found",
    )


router.include_router(competition_contract_router)
router.include_router(competition_segment_router)
router.include_router(competition_admin_segment_router)
router.include_router(competition_control_router)

__all__ = ["router"]
