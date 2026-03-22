from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.fast_cups.api.schemas import (
    FastCupBracketView,
    FastCupPreviewView,
    FastCupResultSummaryView,
    JoinFastCupRequest,
    JoinFastCupResponse,
    RegistrationCountdownView,
    UpcomingFastCupsView,
)
from app.fast_cups.models.domain import (
    ClubCompetitionWindow,
    FastCupDivision,
    FastCupEntrant,
    FastCupNotFoundError,
    FastCupStateError,
    FastCupValidationError,
)
from app.fast_cups.services.ecosystem import (
    FastCupEcosystemService,
    build_fast_cup_ecosystem_for_session,
)

router = APIRouter(prefix="/fast-cups", tags=["fast-cups"])


def get_fast_cup_ecosystem(request: Request) -> FastCupEcosystemService:
    ecosystem = getattr(request.app.state, "fast_cup_ecosystem", None)
    if ecosystem is None:
        ecosystem = build_fast_cup_ecosystem_for_session(getattr(request.app.state, "session_factory", None))
        request.app.state.fast_cup_ecosystem = ecosystem
    return ecosystem


@router.get("/upcoming", response_model=UpcomingFastCupsView)
def list_upcoming_fast_cups(
    now: datetime | None = None,
    division: FastCupDivision | None = None,
    size: int | None = Query(default=None, ge=32),
    horizon_intervals: int = Query(default=4, ge=1, le=8),
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> UpcomingFastCupsView:
    current_time = now or datetime.now(UTC)
    cups = ecosystem.list_upcoming_cups(
        now=current_time,
        division=division,
        size=size,
        horizon_intervals=horizon_intervals,
    )
    return UpcomingFastCupsView(cups=[FastCupPreviewView.model_validate(cup) for cup in cups])


@router.post("/{cup_id}/join", response_model=JoinFastCupResponse)
def join_fast_cup(
    cup_id: str,
    payload: JoinFastCupRequest,
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> JoinFastCupResponse:
    try:
        cup = ecosystem.join_cup(
            cup_id=cup_id,
            entrant=FastCupEntrant(
                club_id=payload.club_id,
                club_name=payload.club_name,
                division=payload.division,
                rating=payload.rating,
                registered_at=payload.registered_at or datetime.now(UTC),
            ),
            existing_windows=tuple(
                ClubCompetitionWindow(
                    club_id=window.club_id,
                    competition_id=window.competition_id,
                    competition_type=window.competition_type,
                    starts_at=window.starts_at,
                    ends_at=window.ends_at,
                    window=window.window,
                )
                for window in payload.existing_windows
            ),
            now=payload.registered_at or datetime.now(UTC),
        )
    except FastCupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FastCupStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except FastCupValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return JoinFastCupResponse(
        cup=FastCupPreviewView.model_validate(cup),
        entrants_registered=len(cup.entrants),
        slots_remaining=max(0, cup.size - len(cup.entrants)),
    )


@router.get("/{cup_id}/bracket", response_model=FastCupBracketView)
def get_fast_cup_bracket(
    cup_id: str,
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> FastCupBracketView:
    try:
        bracket = ecosystem.get_bracket(cup_id=cup_id)
    except FastCupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FastCupStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FastCupBracketView.model_validate(bracket)


@router.get("/{cup_id}/countdown", response_model=RegistrationCountdownView)
def get_fast_cup_countdown(
    cup_id: str,
    now: datetime | None = None,
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> RegistrationCountdownView:
    try:
        countdown = ecosystem.get_countdown(cup_id=cup_id, now=now or datetime.now(UTC))
    except FastCupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RegistrationCountdownView.model_validate(countdown)


@router.get("/{cup_id}/result-summary", response_model=FastCupResultSummaryView)
def get_fast_cup_result_summary(
    cup_id: str,
    now: datetime | None = None,
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> FastCupResultSummaryView:
    try:
        summary = ecosystem.get_result_summary(cup_id=cup_id, now=now or datetime.now(UTC))
    except FastCupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FastCupStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FastCupResultSummaryView.model_validate(summary)
