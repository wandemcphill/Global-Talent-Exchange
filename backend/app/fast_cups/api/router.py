from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_session
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
    FastCupDivision,
    FastCupNotFoundError,
    FastCupStateError,
    FastCupValidationError,
)
from app.fast_cups.services.ecosystem import (
    FastCupEcosystemService,
    build_fast_cup_ecosystem_for_session,
)
from app.fast_cups.services.finance import FastCupFinanceError, FastCupFinanceService
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.wallets.service import InsufficientBalanceError

router = APIRouter(prefix="/fast-cups", tags=["fast-cups"])


def get_fast_cup_ecosystem(request: Request) -> FastCupEcosystemService:
    ecosystem = getattr(request.app.state, "fast_cup_ecosystem", None)
    if ecosystem is None:
        ecosystem = build_fast_cup_ecosystem_for_session(getattr(request.app.state, "session_factory", None))
        request.app.state.fast_cup_ecosystem = ecosystem
    return ecosystem


def _utc_now_for_app(request: Request) -> datetime:
    pinned_now = getattr(request.app.state, "fast_cup_now", None)
    if isinstance(pinned_now, datetime):
        return pinned_now.astimezone(UTC) if pinned_now.tzinfo is not None else pinned_now.replace(tzinfo=UTC)
    return datetime.now(UTC)


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
    request: Request,
    cup_id: str,
    payload: JoinFastCupRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> JoinFastCupResponse:
    registered = None
    try:
        now = _utc_now_for_app(request)
        cup = ecosystem.repository.get(cup_id)
        finance = FastCupFinanceService(session)
        entrant = finance.build_server_entrant(cup=cup, actor=current_user, club_id=payload.club_id, now=now)
        updated = ecosystem.registration_service.join_cup(
            cup=cup,
            entrant=entrant,
            existing_windows=(),
            now=now,
        )
        club = session.get(ClubProfile, entrant.club_id)
        if club is None:
            raise FastCupFinanceError("club_not_found")
        registered = finance.escrow_registration(cup=cup, actor=current_user, club=club, now=now)
        cup = ecosystem.repository.save(updated)
        session.commit()
    except FastCupNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FastCupStateError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except FastCupValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except FastCupFinanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InsufficientBalanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc

    return JoinFastCupResponse(
        cup=FastCupPreviewView.model_validate(cup),
        entrants_registered=len(cup.entrants),
        slots_remaining=max(0, cup.size - len(cup.entrants)),
        registration_id=registered.id if registered is not None else None,
        escrow_status=(
            registered.escrow_status.value
            if registered is not None and hasattr(registered.escrow_status, "value")
            else (str(registered.escrow_status) if registered is not None else None)
        ),
        entry_fee_amount=registered.entry_fee_amount if registered is not None else None,
        entry_fee_currency=registered.entry_fee_currency if registered is not None else None,
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
    session: Session = Depends(get_session),
    ecosystem: FastCupEcosystemService = Depends(get_fast_cup_ecosystem),
) -> FastCupResultSummaryView:
    try:
        summary = ecosystem.get_result_summary(cup_id=cup_id, now=now or datetime.now(UTC))
        FastCupFinanceService(session).settle_result_summary(summary=summary)
        session.commit()
    except FastCupNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FastCupStateError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except FastCupFinanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return FastCupResultSummaryView.model_validate(summary)
