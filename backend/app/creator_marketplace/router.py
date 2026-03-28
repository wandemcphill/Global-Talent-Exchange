from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.creator_marketplace.schemas import (
    CampaignAcceptRequest,
    CampaignApplyRequest,
    CampaignCreateRequest,
    CampaignMarketplaceItemView,
    CampaignParticipationView,
    CampaignPerformanceView,
    CampaignView,
    CreatorOfferView,
    CreatorReputationView,
)
from app.creator_marketplace.service import (
    CreatorMarketplaceConflictError,
    CreatorMarketplaceError,
    CreatorMarketplaceNotFoundError,
    CreatorMarketplacePermissionError,
    CreatorMarketplaceService,
    CreatorMarketplaceValidationError,
)
from app.models.user import User

campaigns_router = APIRouter(prefix="/campaigns", tags=["creator-marketplace"])
creators_router = APIRouter(prefix="/creators", tags=["creator-marketplace"])
router = APIRouter()


def get_creator_marketplace_service(session: Session = Depends(get_session)) -> CreatorMarketplaceService:
    return CreatorMarketplaceService(session=session)


def _raise_http(exc: CreatorMarketplaceError) -> Never:
    if isinstance(exc, CreatorMarketplaceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CreatorMarketplacePermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, CreatorMarketplaceConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, CreatorMarketplaceValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@campaigns_router.post("/create", response_model=CampaignView, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> CampaignView:
    try:
        created = service.create_campaign(actor=current_user, payload=payload)
        session.commit()
    except CreatorMarketplaceError as exc:
        session.rollback()
        _raise_http(exc)
    return CampaignView.model_validate(created)


@campaigns_router.get("", response_model=list[CampaignView])
def list_campaigns(
    current_user: User = Depends(get_current_user),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> list[CampaignView]:
    try:
        items = service.list_campaigns(actor=current_user)
    except CreatorMarketplaceError as exc:
        _raise_http(exc)
    return [CampaignView.model_validate(item) for item in items]


@campaigns_router.post("/{id}/apply", response_model=CreatorOfferView, status_code=status.HTTP_201_CREATED)
def apply_to_campaign(
    id: str,
    payload: CampaignApplyRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> CreatorOfferView:
    try:
        offer = service.apply_to_campaign(actor=current_user, campaign_id=id, payload=payload)
        session.commit()
    except CreatorMarketplaceError as exc:
        session.rollback()
        _raise_http(exc)
    return CreatorOfferView.model_validate(offer)


@campaigns_router.post("/{id}/accept", response_model=CampaignParticipationView)
def accept_campaign_offer(
    id: str,
    payload: CampaignAcceptRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> CampaignParticipationView:
    try:
        participation = service.accept_offer(actor=current_user, campaign_id=id, payload=payload)
        session.commit()
    except CreatorMarketplaceError as exc:
        session.rollback()
        _raise_http(exc)
    return CampaignParticipationView.model_validate(participation)


@campaigns_router.get("/{id}/performance", response_model=CampaignPerformanceView)
def get_campaign_performance(
    id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> CampaignPerformanceView:
    try:
        body = service.get_campaign_performance(actor=current_user, campaign_id=id)
    except CreatorMarketplaceError as exc:
        _raise_http(exc)
    return CampaignPerformanceView.model_validate(body)


@creators_router.get("/marketplace", response_model=list[CampaignMarketplaceItemView])
def list_creator_marketplace(
    current_user: User = Depends(get_current_user),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> list[CampaignMarketplaceItemView]:
    try:
        items = service.list_creator_marketplace(actor=current_user)
    except CreatorMarketplaceError as exc:
        _raise_http(exc)
    return [CampaignMarketplaceItemView.model_validate(item) for item in items]


@creators_router.get("/me/reputation", response_model=CreatorReputationView)
def get_my_creator_reputation(
    current_user: User = Depends(get_current_user),
    service: CreatorMarketplaceService = Depends(get_creator_marketplace_service),
) -> CreatorReputationView:
    try:
        reputation = service.get_creator_reputation_view(actor=current_user)
    except CreatorMarketplaceError as exc:
        _raise_http(exc)
    return CreatorReputationView.model_validate(reputation)


router.include_router(campaigns_router)
router.include_router(creators_router)
