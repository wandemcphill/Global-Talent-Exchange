from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.competitions.schemas import CompetitionView
from app.competitions.service import CompetitionQueryService
from app.manager_market.schemas import CompetitionAdminUpdateRequest, CompetitionAdminView, CompetitionOrchestrationView, CompetitionRuntimeView
from app.manager_market.service import ManagerMarketService
from app.models.user import User
from app.wallets.service import WalletService

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("/{competition_id}", response_model=CompetitionView)
def get_competition(
    competition_id: str,
    session: Session = Depends(get_session),
) -> CompetitionView:
    competition = CompetitionQueryService(session).get_competition(competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition {competition_id} was not found",
        )
    return CompetitionView.model_validate(competition)


def _manager_market_service() -> ManagerMarketService:
    return ManagerMarketService(wallet_service=WalletService())


@router.get('/runtime/{code}', response_model=CompetitionRuntimeView)
def preview_runtime(
    code: str,
    request: Request,
    participants: int = Query(default=2, ge=0),
    region: str = Query(default='africa'),
    session: Session = Depends(get_session),
) -> CompetitionRuntimeView:
    return _manager_market_service().preview_competition_runtime(request.app, session, code=code, participants=participants, region=region)


@router.get('/admin', response_model=list[CompetitionAdminView])
def list_admin_competitions(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> list[CompetitionAdminView]:
    return _manager_market_service().list_competitions(request.app, session)


@router.patch('/admin/{code}', response_model=CompetitionAdminView)
def update_admin_competition(
    code: str,
    payload: CompetitionAdminUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CompetitionAdminView:
    result = _manager_market_service().update_competition(
        request.app,
        session,
        code=code,
        enabled=payload.enabled,
        minimum_viable_participants=payload.minimum_viable_participants,
        geo_locked_regions=payload.geo_locked_regions,
        allow_fallback_fill=payload.allow_fallback_fill,
        fallback_source_regions=payload.fallback_source_regions,
    )
    session.commit()
    return result


@router.get('/admin/{code}/orchestrate', response_model=CompetitionOrchestrationView)
def preview_admin_orchestration(
    code: str,
    request: Request,
    participants: int = Query(default=4, ge=0),
    region: str = Query(default='africa'),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> CompetitionOrchestrationView:
    return _manager_market_service().orchestrate_competition(request.app, session, code=code, participants=participants, region=region)
