from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.sponsorship_engine.schemas import (
    ClubSponsorAssignmentRequest,
    ClubSponsorView,
    SponsorCategoryToggleRequest,
    SponsorEligibilityMetricsView,
    SponsorEligibilityView,
    SponsorOfferCreateRequest,
    SponsorOfferRuleUpsertRequest,
    SponsorOfferRuleView,
    SponsorOfferView,
    SponsorshipOfferAnalyticsView,
    SponsorshipContractView,
    SponsorshipDashboardView,
    SponsorshipLeadCreateRequest,
    SponsorshipLeadView,
    SponsorshipPlacementRequest,
    SponsorshipPlacementResponse,
    SponsorshipPlacementView,
    SponsorshipPackageView,
    SponsorshipPayoutView,
    SponsorshipReviewRequest,
    SponsorshipSettlementView,
)
from app.sponsorship_engine.offer_service import ClubSponsorOfferError, ClubSponsorOfferService
from app.sponsorship_engine.service import SponsorshipEngineError, SponsorshipEngineService
from app.services.sponsorship_placement_service import SponsorshipPlacementService
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/sponsorship", tags=["sponsorship"])
admin_router = APIRouter(prefix="/admin/sponsorship", tags=["admin-sponsorship"])


def get_service(session: Session = Depends(get_session)) -> SponsorshipEngineService:
    return SponsorshipEngineService(session)


def get_offer_service(session: Session = Depends(get_session)) -> ClubSponsorOfferService:
    return ClubSponsorOfferService(session=session, analytics=AnalyticsService())


def _raise(exc: SponsorshipEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _raise_offer(exc: ClubSponsorOfferError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/packages", response_model=list[SponsorshipPackageView])
def list_packages(service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipPackageView]:
    return [SponsorshipPackageView.model_validate(item) for item in service.list_packages(active_only=True)]


@router.post("/placements", response_model=SponsorshipPlacementResponse)
def resolve_placements(
    payload: SponsorshipPlacementRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SponsorshipPlacementResponse:
    service = SponsorshipPlacementService(session=session, settings=request.app.state.settings, analytics=AnalyticsService())
    placements = service.resolve_placements(
        home_club_id=payload.home_club_id,
        away_club_id=payload.away_club_id,
        competition_id=payload.competition_id,
        stage_name=payload.stage_name,
        region_code=payload.region_code,
        surfaces=tuple(payload.surfaces) if payload.surfaces else None,
    )
    return SponsorshipPlacementResponse(
        placements=[
            SponsorshipPlacementView(
                surface=item.surface,
                sponsor_name=item.sponsor_name,
                campaign_code=item.campaign_code,
                source=item.source,
                asset_type=item.asset_type,
                creative_url=item.creative_url,
                fallback=item.fallback,
                metadata=item.metadata,
            )
            for item in placements
        ]
    )


@router.get("/clubs/{club_id}/contracts", response_model=list[SponsorshipContractView])
def list_club_contracts(club_id: str, service: SponsorshipEngineService = Depends(get_service)) -> list[SponsorshipContractView]:
    return [SponsorshipContractView.model_validate(item) for item in service.list_club_contracts(club_id=club_id)]


@router.get("/clubs/{club_id}/dashboard", response_model=SponsorshipDashboardView)
def get_dashboard(club_id: str, service: SponsorshipEngineService = Depends(get_service)) -> SponsorshipDashboardView:
    return SponsorshipDashboardView.model_validate(service.dashboard(club_id=club_id))


@router.get("/clubs/{club_id}/offers", response_model=list[SponsorEligibilityView])
def list_eligible_offers(club_id: str, service: ClubSponsorOfferService = Depends(get_offer_service)) -> list[SponsorEligibilityView]:
    payloads = service.list_eligible_offers(club_id=club_id)
    return [
        SponsorEligibilityView(
            offer=SponsorOfferView.model_validate(item["offer"]),
            club_metrics=SponsorEligibilityMetricsView.model_validate(item["club_metrics"]),
            eligible=item["eligible"],
            unmet_rules=list(item["unmet_rules"]),
        )
        for item in payloads
    ]


@router.get("/clubs/{club_id}/sponsors", response_model=list[ClubSponsorView])
def list_club_sponsors(club_id: str, service: ClubSponsorOfferService = Depends(get_offer_service)) -> list[ClubSponsorView]:
    return [ClubSponsorView.model_validate(item) for item in service.list_club_sponsors(club_id=club_id)]


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


@admin_router.get("/offers", response_model=list[SponsorOfferView])
def admin_list_offers(_: User = Depends(get_current_admin), service: ClubSponsorOfferService = Depends(get_offer_service)) -> list[SponsorOfferView]:
    return [SponsorOfferView.model_validate(item) for item in service.list_offers(active_only=False)]


@admin_router.post("/offers", response_model=SponsorOfferView, status_code=status.HTTP_201_CREATED)
def admin_create_offer(
    payload: SponsorOfferCreateRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> SponsorOfferView:
    service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
    try:
        offer = service.create_offer(payload)
    except ClubSponsorOfferError as exc:
        _raise_offer(exc)
    session.commit()
    session.refresh(offer)
    return SponsorOfferView.model_validate(offer)


@admin_router.put("/offers/{offer_id}/rule", response_model=SponsorOfferRuleView)
def admin_upsert_offer_rule(
    offer_id: str,
    payload: SponsorOfferRuleUpsertRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> SponsorOfferRuleView:
    service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
    try:
        rule = service.upsert_offer_rule(offer_id=offer_id, payload=payload)
    except ClubSponsorOfferError as exc:
        _raise_offer(exc)
    session.commit()
    session.refresh(rule)
    return SponsorOfferRuleView.model_validate(rule)


@admin_router.post("/offers/{offer_id}/assign", response_model=ClubSponsorView)
def admin_assign_offer(
    offer_id: str,
    payload: ClubSponsorAssignmentRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ClubSponsorView:
    service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
    try:
        sponsor = service.assign_offer_to_club(actor=actor, offer_id=offer_id, payload=payload)
    except ClubSponsorOfferError as exc:
        _raise_offer(exc)
    session.commit()
    session.refresh(sponsor)
    return ClubSponsorView.model_validate(sponsor)


@admin_router.post("/categories/{category}", response_model=list[SponsorOfferView])
def admin_toggle_category(
    category: str,
    payload: SponsorCategoryToggleRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[SponsorOfferView]:
    service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
    offers = service.set_category_enabled(category=category, enabled=payload.enabled)
    session.commit()
    return [SponsorOfferView.model_validate(item) for item in offers]


@admin_router.get("/analytics", response_model=SponsorshipOfferAnalyticsView)
def admin_offer_analytics(_: User = Depends(get_current_admin), service: ClubSponsorOfferService = Depends(get_offer_service)) -> SponsorshipOfferAnalyticsView:
    return SponsorshipOfferAnalyticsView.model_validate(service.sponsorship_analytics())


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
