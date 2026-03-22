from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.economy.schemas import (
    EconomyBurnEventView,
    GiftComboRuleUpsertRequest,
    GiftComboRuleView,
    GiftCatalogItemUpsertRequest,
    GiftCatalogItemView,
    RevenueShareRuleUpsertRequest,
    RevenueShareRuleView,
    ServicePricingRuleUpsertRequest,
    ServicePricingRuleView,
)
from app.economy.service import EconomyConfigService
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.user import User

router = APIRouter(prefix="/economy", tags=["economy"])
admin_router = APIRouter(prefix="/admin/economy", tags=["admin-economy"])


@router.get("/gift-catalog", response_model=list[GiftCatalogItemView])
def list_gift_catalog(session: Session = Depends(get_session)) -> list[GiftCatalogItemView]:
    service = EconomyConfigService(session)
    return [GiftCatalogItemView.model_validate(item, from_attributes=True) for item in service.list_gifts(active_only=True)]


@router.get("/service-pricing", response_model=list[ServicePricingRuleView])
def list_service_pricing(session: Session = Depends(get_session)) -> list[ServicePricingRuleView]:
    service = EconomyConfigService(session)
    return [ServicePricingRuleView.model_validate(item, from_attributes=True) for item in service.list_service_pricing(active_only=True)]


@admin_router.post("/gift-catalog", response_model=GiftCatalogItemView)
def upsert_gift_catalog_item(
    payload: GiftCatalogItemUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> GiftCatalogItemView:
    service = EconomyConfigService(session)
    item = service.upsert_gift(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return GiftCatalogItemView.model_validate(item, from_attributes=True)


@admin_router.post("/service-pricing", response_model=ServicePricingRuleView)
def upsert_service_pricing_rule(
    payload: ServicePricingRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ServicePricingRuleView:
    service = EconomyConfigService(session)
    item = service.upsert_service_pricing(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return ServicePricingRuleView.model_validate(item, from_attributes=True)


@admin_router.get("/revenue-share-rules", response_model=list[RevenueShareRuleView])
def list_revenue_share_rules(
    session: Session = Depends(get_session),
    active_only: bool = Query(default=True),
) -> list[RevenueShareRuleView]:
    service = EconomyConfigService(session)
    return [RevenueShareRuleView.model_validate(item) for item in service.list_revenue_share_rules(active_only=active_only)]


@admin_router.post("/revenue-share-rules", response_model=RevenueShareRuleView)
def upsert_revenue_share_rule(
    payload: RevenueShareRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RevenueShareRuleView:
    service = EconomyConfigService(session)
    item = service.upsert_revenue_share_rule(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return RevenueShareRuleView.model_validate(item)


@admin_router.get("/gift-combo-rules", response_model=list[GiftComboRuleView])
def list_gift_combo_rules(
    session: Session = Depends(get_session),
    active_only: bool = Query(default=True),
) -> list[GiftComboRuleView]:
    service = EconomyConfigService(session)
    return [GiftComboRuleView.model_validate(item) for item in service.list_gift_combo_rules(active_only=active_only)]


@admin_router.post("/gift-combo-rules", response_model=GiftComboRuleView)
def upsert_gift_combo_rule(
    payload: GiftComboRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> GiftComboRuleView:
    service = EconomyConfigService(session)
    item = service.upsert_gift_combo_rule(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return GiftComboRuleView.model_validate(item)


@admin_router.get("/burn-events", response_model=list[EconomyBurnEventView])
def list_burn_events(
    session: Session = Depends(get_session),
    user_id: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EconomyBurnEventView]:
    stmt = select(EconomyBurnEvent).order_by(EconomyBurnEvent.created_at.desc()).limit(limit)
    if user_id:
        stmt = stmt.where(EconomyBurnEvent.user_id == user_id)
    if source_type:
        stmt = stmt.where(EconomyBurnEvent.source_type == source_type)
    return [EconomyBurnEventView.model_validate(item) for item in session.scalars(stmt).all()]
