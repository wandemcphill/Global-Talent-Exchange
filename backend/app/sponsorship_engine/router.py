from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.user import User
from backend.app.sponsorship_engine.schemas import (
    SponsorshipContractView,
    SponsorshipDashboardView,
    SponsorshipLeadCreateRequest,
    SponsorshipLeadView,
    SponsorshipPackageView,
    SponsorshipPayoutView,
    SponsorshipReviewRequest,
    SponsorshipSettlementView,
)
from backend.app.sponsorship_engine.service import SponsorshipEngineError, SponsorshipEngineService

router = APIRouter(prefix="/sponsorship", tags=["sponsorship"])
admin_router = APIRouter(prefix="/admin/sponsorship", tags=["admin-sponsorship"])


def get_service(session: Session = Depends(get_session)) -> SponsorshipEngineService:
    return SponsorshipEngineService(session)


def _raise(exc: SponsorshipEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/packages", response_model=list[SponsorshipPackageView])
def list_packages(service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipPackageView]:
    return [SponsorshipPackageView.model_validate(item) for item in service.list_packages(active_only=True)]


@router.get("/clubs/{club_id}/contracts", response_model=list[SponsorshipContractView])
def list_club_contracts(club_id: str, service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipContractView]:
    return [SponsorshipContractView.model_validate(item) for item in service.list_club_contracts(club_id=club_id)]


@router.get("/clubs/{club_id}/dashboard", response_model=SponsorshipDashboardView)
def get_dashboard(club_id: str, service: SponsorshipEngineService = Depends(get_service)) -> SponsorshipDashboardView:
    return SponsorshipDashboardView.model_validate(service.dashboard(club_id=club_id))


@router.get("/me/leads", response_model=list[SponsorshipLeadView])
def list_my_leads(current_user: User = Depends(get_current_user), service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipLeadView]:
    return [SponsorshipLeadView.model_validate(item) for item in service.list_my_leads(actor=current_user)]


@router.post("/contracts/request", response_model=SponsorshipLeadView, status_code=status.HTTP_201_CREATED)
def request_contract(payload: SponsorshipLeadCreateRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> SponsorshipLeadView:
    service = SponsorshipEngineService(session)
    try:
        lead, _contract = service.request_contract(actor=current_user, payload=payload)
    except SponsorshipEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(lead)
    return SponsorshipLeadView.model_validate(lead)


@admin_router.get("/packages", response_model=list[SponsorshipPackageView])
def admin_list_packages(_: User = Depends(get_current_admin), service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipPackageView]:
    return [SponsorshipPackageView.model_validate(item) for item in service.list_packages(active_only=False)]


@admin_router.post("/contracts/{contract_id}/review", response_model=SponsorshipContractView)
def review_contract(contract_id: str, payload: SponsorshipReviewRequest, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> SponsorshipContractView:
    service = SponsorshipEngineService(session)
    try:
        contract = service.review_contract(actor=actor, contract_id=contract_id, action=payload.action, resolution_note=payload.resolution_note)
    except SponsorshipEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(contract)
    return SponsorshipContractView.model_validate(contract)


@admin_router.post("/contracts/{contract_id}/settle-next", response_model=SponsorshipSettlementView)
def settle_next_payout(contract_id: str, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> SponsorshipSettlementView:
    service = SponsorshipEngineService(session)
    try:
        contract, payout, credited_amount, destination_user_id = service.settle_next_payout(actor=actor, contract_id=contract_id)
    except SponsorshipEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(contract)
    session.refresh(payout)
    return SponsorshipSettlementView(
        contract=SponsorshipContractView.model_validate(contract),
        payout=SponsorshipPayoutView.model_validate(payout),
        credited_amount=credited_amount,
        currency=contract.currency,
        destination_user_id=destination_user_id,
    )
