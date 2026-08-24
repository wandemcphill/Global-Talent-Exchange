from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_session
from app.models.user import User
from app.tournaments.schemas import (
    TournamentCreateRequest,
    TournamentJoinRequest,
    TournamentListView,
    TournamentMatchResultRequest,
    TournamentView,
)
from app.tournaments.service import (
    TournamentError,
    TournamentNotFoundError,
    TournamentService,
    TournamentValidationError,
)

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


def _service(session: Session = Depends(get_session)) -> TournamentService:
    return TournamentService(session=session)


def _raise_http(exc: TournamentError) -> None:
    if isinstance(exc, TournamentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, TournamentValidationError):
        conflict_reasons = {
            "insufficient_balance",
            "operation_busy",
            "registration_closed",
            "round_locked",
            "round_not_ready",
            "tournament_full",
        }
        status_code = status.HTTP_409_CONFLICT if exc.reason in conflict_reasons else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("", response_model=TournamentListView)
def list_tournaments(
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentListView:
    try:
        tournaments = service.list_tournaments()
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentListView(tournaments=[TournamentView.model_validate(item) for item in tournaments])


@router.post("", response_model=TournamentView, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may create platform tournaments.",
        )
    try:
        tournament = service.create_tournament(payload)
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)


@router.get("/{tournament_id}", response_model=TournamentView)
def get_tournament(
    tournament_id: str,
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    try:
        tournament = service.get_tournament(tournament_id)
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)


@router.post("/{tournament_id}/join", response_model=TournamentView)
def join_tournament(
    tournament_id: str,
    payload: TournamentJoinRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tournament joins must be performed for the authenticated user.",
        )
    try:
        tournament = service.join_tournament(tournament_id, user_id=current_user.id)
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)


@router.post("/{tournament_id}/matches/{match_id}/result", response_model=TournamentView)
def report_match_result(
    tournament_id: str,
    match_id: str,
    payload: TournamentMatchResultRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    try:
        tournament = service.record_match_result(
            tournament_id,
            match_id,
            payload,
            actor_user_id=current_user.id,
        )
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)


@router.post("/{tournament_id}/advance", response_model=TournamentView)
def advance_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    try:
        tournament = service.advance_tournament(tournament_id, actor_user_id=current_user.id)
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)
