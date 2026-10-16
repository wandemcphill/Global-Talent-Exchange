from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_match_user,
    get_current_wallet_user,
    get_session as auth_get_session,
)
from app.models.user import User
from app.ticketing.schemas import (
    TicketBuyRequest,
    TicketBuyResponse,
    TicketEventResponse,
    TicketReactionRequest,
    TicketReactionResponse,
    TicketResellRequest,
    TicketResellResponse,
    TicketWaitlistRequest,
    TicketWaitlistView,
)
from app.ticketing.service import (
    TicketingConflictError,
    TicketingNotFoundError,
    TicketingService,
    TicketingValidationError,
)

router = APIRouter(prefix="/tickets", tags=["ticketing"])


def _service(request: Request, session: Session) -> TicketingService:
    return TicketingService(session, app=request.app)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, TicketingNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, TicketingConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, TicketingValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/event/{match_id}", response_model=TicketEventResponse)
def read_event(
    match_id: str,
    request: Request,
    session: Session = Depends(auth_get_session),
    current_user: User = Depends(get_current_match_user),
) -> TicketEventResponse:
    try:
        response = _service(request, session).get_event(match_id=match_id, user=current_user)
        session.commit()
        return response
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/buy", response_model=TicketBuyResponse, status_code=status.HTTP_201_CREATED)
def buy_ticket(
    payload: TicketBuyRequest,
    request: Request,
    session: Session = Depends(auth_get_session),
    current_user: User = Depends(get_current_wallet_user),
) -> TicketBuyResponse:
    try:
        response = _service(request, session).buy_ticket(
            user=current_user,
            match_id=payload.match_id,
            seat_tier=payload.seat_tier,
            resale_ticket_id=payload.resale_ticket_id,
        )
        session.commit()
        return response
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/resell", response_model=TicketResellResponse)
def resell_ticket(
    payload: TicketResellRequest,
    request: Request,
    session: Session = Depends(auth_get_session),
    current_user: User = Depends(get_current_wallet_user),
) -> TicketResellResponse:
    try:
        response = _service(request, session).resell_ticket(
            user=current_user,
            ticket_id=payload.ticket_id,
            price=payload.price,
        )
        session.commit()
        return response
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/waitlist", response_model=TicketWaitlistView, status_code=status.HTTP_201_CREATED)
def join_waitlist(
    payload: TicketWaitlistRequest,
    request: Request,
    session: Session = Depends(auth_get_session),
    current_user: User = Depends(get_current_match_user),
) -> TicketWaitlistView:
    try:
        response = _service(request, session).join_waitlist(
            user=current_user,
            match_id=payload.match_id,
            seat_tier=payload.seat_tier,
        )
        session.commit()
        return response
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/attendance/{match_id}/react", response_model=TicketReactionResponse)
def react_as_attendee(
    match_id: str,
    payload: TicketReactionRequest,
    request: Request,
    session: Session = Depends(auth_get_session),
    current_user: User = Depends(get_current_match_user),
) -> TicketReactionResponse:
    try:
        response = _service(request, session).record_attendance_reaction(
            user=current_user,
            match_id=match_id,
            reaction_type=payload.reaction_type,
            intensity=payload.intensity,
            source="http",
        )
        session.commit()
        return response
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)
