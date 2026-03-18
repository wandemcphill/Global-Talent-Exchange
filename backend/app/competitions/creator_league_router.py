from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.models.user import User
from backend.app.schemas.creator_league import (
    CreatorLeagueConfigUpdateRequest,
    CreatorLeagueConfigView,
    CreatorLeagueFinancialReportView,
    CreatorLeagueLivePriorityView,
    CreatorLeagueSeasonCreateRequest,
    CreatorLeagueSettlementReviewRequest,
    CreatorLeagueSettlementView,
    CreatorLeagueSeasonView,
    CreatorLeagueStandingView,
    CreatorLeagueTierCreateRequest,
    CreatorLeagueTierUpdateRequest,
)
from backend.app.services.creator_league_finance_service import CreatorLeagueFinanceService
from backend.app.services.creator_league_service import CreatorLeagueError, CreatorLeagueService

router = APIRouter(prefix="/creator-league", tags=["creator-league"])


@router.get("", response_model=CreatorLeagueConfigView)
def get_creator_league_overview(
    session: Session = Depends(get_session),
) -> CreatorLeagueConfigView:
    return CreatorLeagueService(session).get_overview()


@router.patch("/config", response_model=CreatorLeagueConfigView)
def update_creator_league_config(
    payload: CreatorLeagueConfigUpdateRequest,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> CreatorLeagueConfigView:
    return _handle_errors(lambda: CreatorLeagueService(session).update_config(payload, actor_user_id=admin.id))


@router.post("/tiers", response_model=CreatorLeagueConfigView, status_code=status.HTTP_201_CREATED)
def add_creator_league_tier(
    payload: CreatorLeagueTierCreateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueConfigView:
    return _handle_errors(lambda: CreatorLeagueService(session).add_tier(payload))


@router.patch("/tiers/{tier_id}", response_model=CreatorLeagueConfigView)
def update_creator_league_tier(
    tier_id: str,
    payload: CreatorLeagueTierUpdateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueConfigView:
    return _handle_errors(lambda: CreatorLeagueService(session).update_tier(tier_id, payload))


@router.delete("/tiers/{tier_id}", response_model=CreatorLeagueConfigView)
def delete_creator_league_tier(
    tier_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueConfigView:
    return _handle_errors(lambda: CreatorLeagueService(session).delete_tier(tier_id))


@router.post("/reset", response_model=CreatorLeagueConfigView)
def reset_creator_league_structure(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueConfigView:
    return _handle_errors(lambda: CreatorLeagueService(session).reset_structure())


@router.post("/seasons", response_model=CreatorLeagueSeasonView, status_code=status.HTTP_201_CREATED)
def create_creator_league_season(
    payload: CreatorLeagueSeasonCreateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueSeasonView:
    return _handle_errors(lambda: CreatorLeagueService(session).create_season(payload))


@router.get("/seasons/{season_id}", response_model=CreatorLeagueSeasonView)
def get_creator_league_season(
    season_id: str,
    session: Session = Depends(get_session),
) -> CreatorLeagueSeasonView:
    return _handle_errors(lambda: CreatorLeagueService(session).get_season(season_id))


@router.post("/seasons/{season_id}/pause", response_model=CreatorLeagueSeasonView)
def pause_creator_league_season(
    season_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueSeasonView:
    return _handle_errors(lambda: CreatorLeagueService(session).pause_season(season_id))


@router.get("/season-tiers/{season_tier_id}/standings", response_model=tuple[CreatorLeagueStandingView, ...])
def get_creator_league_standings(
    season_tier_id: str,
    session: Session = Depends(get_session),
) -> tuple[CreatorLeagueStandingView, ...]:
    return _handle_errors(lambda: CreatorLeagueService(session).get_standings(season_tier_id))


@router.get("/live-priority", response_model=CreatorLeagueLivePriorityView)
def get_creator_league_live_priority(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> CreatorLeagueLivePriorityView:
    return CreatorLeagueService(session).live_priority(limit=limit)


@router.get("/financial-report", response_model=CreatorLeagueFinancialReportView)
def get_creator_league_financial_report(
    season_id: str | None = None,
    settlement_limit: int = Query(default=10, ge=1, le=100),
    audit_limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CreatorLeagueFinancialReportView:
    payload = CreatorLeagueFinanceService(session).get_report(
        season_id=season_id,
        settlement_limit=settlement_limit,
        audit_limit=audit_limit,
    )
    return CreatorLeagueFinancialReportView.model_validate(payload)


@router.get("/financial-settlements", response_model=tuple[CreatorLeagueSettlementView, ...])
def list_creator_league_financial_settlements(
    season_id: str | None = None,
    review_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> tuple[CreatorLeagueSettlementView, ...]:
    items = CreatorLeagueFinanceService(session).list_settlements(
        season_id=season_id,
        review_status=review_status,
        limit=limit,
    )
    return tuple(CreatorLeagueSettlementView.model_validate(item) for item in items)


@router.post("/financial-settlements/{settlement_id}/approve", response_model=CreatorLeagueSettlementView)
def approve_creator_league_financial_settlement(
    settlement_id: str,
    payload: CreatorLeagueSettlementReviewRequest,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> CreatorLeagueSettlementView:
    return _handle_errors(
        lambda: CreatorLeagueSettlementView.model_validate(
            CreatorLeagueFinanceService(session).approve_settlement(
                settlement_id=settlement_id,
                actor=admin,
                review_note=payload.review_note,
            )
        )
    )


def _handle_errors(operation):
    try:
        return operation()
    except CreatorLeagueError as exc:
        raise _to_http_error(exc) from exc


def _to_http_error(exc: CreatorLeagueError) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.reason.endswith("_not_found"):
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.reason in {
        "assignment_mismatch",
        "club_not_found",
        "creator_league_disabled",
        "creator_league_paused",
        "duplicate_club_assignment",
        "invalid_club_count",
        "minimum_divisions",
        "settlement_review_not_required",
    }:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=exc.detail)


__all__ = ["router"]
