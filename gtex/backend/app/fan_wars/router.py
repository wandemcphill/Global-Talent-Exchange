from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.fan_wars.schemas import (
    CreatorCountryAssignmentRequest,
    CreatorCountryAssignmentView,
    FanWarDashboardView,
    FanWarLeaderboardView,
    FanWarPointRecordRequest,
    FanWarPointView,
    FanWarProfileUpsertRequest,
    FanWarProfileView,
    NationsCupCreateRequest,
    NationsCupOverviewView,
    RivalryLeaderboardView,
)
from app.fan_wars.service import FanWarError, FanWarService
from app.models.user import User

router = APIRouter(prefix="/fan-wars", tags=["fan-wars"])
admin_router = APIRouter(prefix="/admin/fan-wars", tags=["admin-fan-wars"])


@router.get("/leaderboards/{board_type}", response_model=FanWarLeaderboardView)
def get_leaderboard(
    board_type: str,
    period_type: str = Query(default="weekly"),
    limit: int = Query(default=20, ge=1, le=100),
    reference_date: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> FanWarLeaderboardView:
    return _handle_errors(lambda: FanWarService(session).get_leaderboard(board_type=board_type, period_type=period_type, limit=limit, reference_date=reference_date))


@router.get("/rivalries/{board_type}", response_model=RivalryLeaderboardView)
def get_rivalry_board(
    board_type: str,
    period_type: str = Query(default="weekly"),
    limit: int = Query(default=20, ge=1, le=100),
    reference_date: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> RivalryLeaderboardView:
    return _handle_errors(lambda: FanWarService(session).get_rivalry_leaderboard(board_type=board_type, period_type=period_type, limit=limit, reference_date=reference_date))


@router.get("/profiles/{profile_id}/dashboard", response_model=FanWarDashboardView)
def get_dashboard(
    profile_id: str,
    period_type: str = Query(default="weekly"),
    reference_date: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> FanWarDashboardView:
    return _handle_errors(lambda: FanWarService(session).get_dashboard(profile_id=profile_id, period_type=period_type, reference_date=reference_date))


@router.get("/nations-cup/{competition_id}", response_model=NationsCupOverviewView)
def get_nations_cup(
    competition_id: str,
    session: Session = Depends(get_session),
) -> NationsCupOverviewView:
    return _handle_errors(lambda: FanWarService(session).get_nations_cup(competition_id))


@admin_router.put("/profiles", response_model=FanWarProfileView)
def upsert_profile(
    payload: FanWarProfileUpsertRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> FanWarProfileView:
    return _commit_and_handle(session, lambda: FanWarService(session).upsert_profile(payload))


@admin_router.post("/profiles/{profile_id}/rivals/{rival_profile_id}", response_model=tuple[FanWarProfileView, FanWarProfileView])
def link_rivals(
    profile_id: str,
    rival_profile_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> tuple[FanWarProfileView, FanWarProfileView]:
    return _commit_and_handle(session, lambda: FanWarService(session).link_rivals(profile_id, rival_profile_id))


@admin_router.post("/points", response_model=tuple[FanWarPointView, ...], status_code=status.HTTP_201_CREATED)
def record_points(
    payload: FanWarPointRecordRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> tuple[FanWarPointView, ...]:
    return _commit_and_handle(session, lambda: FanWarService(session).record_points(payload))


@admin_router.post("/creator-country-assignments", response_model=CreatorCountryAssignmentView)
def assign_creator_country(
    payload: CreatorCountryAssignmentRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> CreatorCountryAssignmentView:
    return _commit_and_handle(session, lambda: FanWarService(session).assign_creator_country(payload, actor=actor))


@admin_router.post("/nations-cup", response_model=NationsCupOverviewView, status_code=status.HTTP_201_CREATED)
def create_nations_cup(
    payload: NationsCupCreateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> NationsCupOverviewView:
    return _commit_and_handle(session, lambda: FanWarService(session).create_nations_cup(payload))


@admin_router.post("/nations-cup/{competition_id}/advance", response_model=NationsCupOverviewView)
def advance_nations_cup(
    competition_id: str,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> NationsCupOverviewView:
    return _commit_and_handle(session, lambda: FanWarService(session).advance_nations_cup(competition_id, force=force))


def _commit_and_handle(session: Session, operation):
    try:
        result = operation()
        session.commit()
        return result
    except FanWarError as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


def _handle_errors(operation):
    try:
        return operation()
    except FanWarError as exc:
        raise _to_http_error(exc) from exc


def _to_http_error(exc: FanWarError) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.reason.endswith("_not_found"):
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.reason in {
        "creator_country_assignment_missing",
        "duplicate_country_assignment",
        "invalid_board_type",
        "invalid_knockout_size",
        "invalid_nations_cup_size",
        "missing_target_fanbase",
        "rival_type_mismatch",
    }:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=exc.detail)


__all__ = ["admin_router", "router"]
