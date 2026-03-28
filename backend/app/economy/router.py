from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.economy.fx_schemas import FxQuoteView, FxRateUpsertRequest, FxRateView, RegionalPricingRuleUpsertRequest, RegionalPricingRuleView
from app.economy.fx_service import FxPricingError, FxPricingService
from app.economy.governor_schemas import (
    EconomyGovernorApplyRequest,
    EconomyGovernorMetricsInput,
    EconomyGovernorPolicyUpdate,
    EconomyGovernorSnapshotView,
)
from app.economy.governor_service import EconomyGovernorError, EconomyGovernorModeError, EconomyGovernorService
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


@router.get("/fx/quote", response_model=FxQuoteView)
def quote_fx_price(
    gtex_amount: Decimal = Query(default=Decimal("1.0000"), gt=0),
    currency: str = Query(min_length=3, max_length=8),
    region_code: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> FxQuoteView:
    try:
        payload = FxPricingService(session).quote_gtex_price(
            gtex_amount=gtex_amount,
            currency=currency,
            region_code=region_code,
        )
    except FxPricingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FxQuoteView.model_validate(payload)


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


@admin_router.get("/governor", response_model=EconomyGovernorSnapshotView)
def get_governor_snapshot(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EconomyGovernorSnapshotView:
    del actor
    return EconomyGovernorSnapshotView.model_validate(EconomyGovernorService(session).snapshot())


@admin_router.post("/governor/policy", response_model=EconomyGovernorSnapshotView)
def update_governor_policy(
    payload: EconomyGovernorPolicyUpdate,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EconomyGovernorSnapshotView:
    service = EconomyGovernorService(session)
    try:
        service.update_policy(actor=actor, **payload.model_dump(exclude_none=True))
    except EconomyGovernorModeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return EconomyGovernorSnapshotView.model_validate(service.snapshot())


@admin_router.post("/governor/evaluate", response_model=EconomyGovernorSnapshotView)
def evaluate_governor(
    payload: EconomyGovernorMetricsInput | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EconomyGovernorSnapshotView:
    del actor
    service = EconomyGovernorService(session)
    metrics = None if payload is None else payload.model_dump(mode="json", exclude_none=True)
    service.evaluate(metrics=metrics)
    session.commit()
    return EconomyGovernorSnapshotView.model_validate(service.snapshot(metrics=metrics))


@admin_router.post("/governor/apply", response_model=EconomyGovernorSnapshotView)
def apply_governor_actions(
    payload: EconomyGovernorApplyRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EconomyGovernorSnapshotView:
    service = EconomyGovernorService(session)
    try:
        snapshot = service.apply_actions(
            actor=actor,
            actions=None if payload.actions is None else [item.model_dump(mode="json") for item in payload.actions],
            metrics=None if payload.metrics is None else payload.metrics.model_dump(mode="json", exclude_none=True),
            allow_manual_override=payload.allow_manual_override,
        )
    except EconomyGovernorError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    return EconomyGovernorSnapshotView.model_validate(snapshot)


@admin_router.get("/fx-rates", response_model=list[FxRateView])
def list_fx_rates(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[FxRateView]:
    del actor
    return [FxRateView.model_validate(item) for item in FxPricingService(session).list_fx_rates()]


@admin_router.post("/fx-rates", response_model=FxRateView)
def upsert_fx_rate(
    payload: FxRateUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> FxRateView:
    item = FxPricingService(session).upsert_fx_rate(
        actor=actor,
        currency=payload.currency,
        rate_to_naira=payload.rate_to_naira,
    )
    session.commit()
    session.refresh(item)
    return FxRateView.model_validate(item)


@admin_router.get("/regional-pricing", response_model=list[RegionalPricingRuleView])
def list_regional_pricing(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[RegionalPricingRuleView]:
    del actor
    return [RegionalPricingRuleView.model_validate(item) for item in FxPricingService(session).list_regional_rules()]


@admin_router.post("/regional-pricing", response_model=RegionalPricingRuleView)
def upsert_regional_pricing(
    payload: RegionalPricingRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegionalPricingRuleView:
    item = FxPricingService(session).upsert_regional_rule(
        actor=actor,
        region_code=payload.region_code,
        label=payload.label,
        price_multiplier=payload.price_multiplier,
        withdrawal_limit_multiplier=payload.withdrawal_limit_multiplier,
        kyc_tier_label=payload.kyc_tier_label,
        tax_tracking_required=payload.tax_tracking_required,
        compliance_note=payload.compliance_note,
    )
    session.commit()
    session.refresh(item)
    return RegionalPricingRuleView.model_validate(item)


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
