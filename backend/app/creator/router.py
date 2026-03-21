from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.schemas.creator_application import (
    CreatorAdminDashboardView,
    CreatorApplicationAdminActionRequest,
    CreatorApplicationSubmitRequest,
    CreatorApplicationView,
    CreatorContactVerificationView,
)
from app.schemas.creator_card import (
    CreatorCardAssignRequest,
    CreatorCardListingCreateRequest,
    CreatorCardListingView,
    CreatorCardLoanCreateRequest,
    CreatorCardLoanView,
    CreatorCardSaleView,
    CreatorCardSwapRequest,
    CreatorCardSwapView,
    CreatorCardView,
)
from app.schemas.creator_share_market import (
    CreatorClubShareDistributionView,
    CreatorClubShareHoldingView,
    CreatorClubShareMarketControlUpdateRequest,
    CreatorClubShareMarketControlView,
    CreatorClubShareMarketIssueRequest,
    CreatorClubShareMarketView,
    CreatorClubSharePurchaseRequest,
    CreatorClubSharePurchaseView,
)
from app.segments.creators.segment_creators import router as legacy_creator_router
from app.services.creator_application_service import (
    CreatorApplicationConflictError,
    CreatorApplicationError,
    CreatorApplicationNotFoundError,
    CreatorApplicationService,
)
from app.services.creator_card_service import (
    CreatorCardError,
    CreatorCardPermissionError,
    CreatorCardService,
    CreatorCardValidationError,
)
from app.services.creator_share_market_service import (
    CreatorClubShareMarketError,
    CreatorClubShareMarketService,
)
from app.wallets.service import InsufficientBalanceError


def get_application_service(session: Session = Depends(get_session)) -> CreatorApplicationService:
    return CreatorApplicationService(session)


def get_creator_card_service(session: Session = Depends(get_session)) -> CreatorCardService:
    return CreatorCardService(session)


def get_creator_share_market_service(session: Session = Depends(get_session)) -> CreatorClubShareMarketService:
    return CreatorClubShareMarketService(session)


def raise_creator_application_http(exc: CreatorApplicationError) -> None:
    if isinstance(exc, CreatorApplicationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CreatorApplicationConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def raise_creator_card_http(exc: CreatorCardError) -> None:
    if isinstance(exc, CreatorCardPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, CreatorCardValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def raise_creator_share_market_http(exc: CreatorClubShareMarketError) -> None:
    if exc.reason in {"share_market_not_found", "creator_club_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.reason) from exc
    if exc.reason in {"creator_scope_denied", "admin_required"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.reason) from exc
    if exc.reason in {
        "shareholder_cap_exceeded",
        "shareholder_anti_takeover_cap_exceeded",
        "share_supply_exhausted",
        "share_market_cap_conflict",
        "share_holding_cap_conflict",
        "share_market_issuance_disabled",
        "share_purchase_disabled",
        "share_purchase_value_cap_exceeded",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason) from exc


creator_router = APIRouter(prefix="/creator", tags=["creator"])
admin_router = APIRouter(prefix="/admin/creator", tags=["admin-creator"])


@creator_router.post("/verify-email", response_model=CreatorContactVerificationView)
def verify_creator_email(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorContactVerificationView:
    try:
        user = service.verify_email(actor=current_user)
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorContactVerificationView(
        user_id=user.id,
        email_verified_at=user.email_verified_at,
        phone_verified_at=user.phone_verified_at,
    )


@creator_router.post("/verify-phone", response_model=CreatorContactVerificationView)
def verify_creator_phone(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorContactVerificationView:
    try:
        user = service.verify_phone(actor=current_user)
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorContactVerificationView(
        user_id=user.id,
        email_verified_at=user.email_verified_at,
        phone_verified_at=user.phone_verified_at,
    )


@creator_router.post("/apply", response_model=CreatorApplicationView, status_code=status.HTTP_201_CREATED)
def submit_creator_application(
    payload: CreatorApplicationSubmitRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorApplicationView:
    try:
        application = service.submit_application(actor=current_user, payload=payload)
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorApplicationView.model_validate(service.serialize_application(application))


@creator_router.get("/application", response_model=CreatorApplicationView | None)
def get_my_creator_application(
    current_user: User = Depends(get_current_user),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorApplicationView | None:
    application = service.get_my_application(actor=current_user)
    if application is None:
        return None
    return CreatorApplicationView.model_validate(service.serialize_application(application))


@creator_router.get("/cards", response_model=list[CreatorCardView])
def list_creator_cards(
    current_user: User = Depends(get_current_user),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> list[CreatorCardView]:
    try:
        cards = service.list_inventory(actor=current_user)
    except CreatorCardError as exc:
        raise_creator_card_http(exc)
    return [CreatorCardView.model_validate(item) for item in cards]


@creator_router.get("/cards/listings", response_model=list[CreatorCardListingView])
def list_creator_card_listings(
    service: CreatorCardService = Depends(get_creator_card_service),
) -> list[CreatorCardListingView]:
    listings = service.list_open_listings()
    return [CreatorCardListingView.model_validate(item) for item in listings]


@creator_router.post("/cards/{creator_card_id}/list", response_model=CreatorCardListingView, status_code=status.HTTP_201_CREATED)
def create_creator_card_listing(
    creator_card_id: str,
    payload: CreatorCardListingCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardListingView:
    try:
        listing = service.create_listing(
            actor=current_user,
            creator_card_id=creator_card_id,
            price_credits=payload.price_credits,
        )
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    return CreatorCardListingView.model_validate(listing)


@creator_router.post("/cards/listings/{listing_id}/buy", response_model=CreatorCardSaleView)
def buy_creator_card_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardSaleView:
    try:
        sale = service.buy_listing(actor=current_user, listing_id=listing_id)
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    except InsufficientBalanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreatorCardSaleView.model_validate(sale)


@creator_router.post("/cards/swap", response_model=CreatorCardSwapView)
def swap_creator_cards(
    payload: CreatorCardSwapRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardSwapView:
    try:
        swap = service.swap_cards(
            actor=current_user,
            offered_card_id=payload.offered_card_id,
            requested_card_id=payload.requested_card_id,
        )
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    return CreatorCardSwapView.model_validate(swap)


@creator_router.post("/cards/{creator_card_id}/loan", response_model=CreatorCardLoanView, status_code=status.HTTP_201_CREATED)
def loan_creator_card(
    creator_card_id: str,
    payload: CreatorCardLoanCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardLoanView:
    try:
        loan = service.loan_card(
            actor=current_user,
            creator_card_id=creator_card_id,
            borrower_user_id=payload.borrower_user_id,
            duration_days=payload.duration_days,
            loan_fee_credits=payload.loan_fee_credits,
        )
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    except InsufficientBalanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreatorCardLoanView.model_validate(loan)


@creator_router.post("/cards/loans/{loan_id}/return", response_model=CreatorCardLoanView)
def return_creator_card_loan(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardLoanView:
    try:
        loan = service.return_loan(actor=current_user, loan_id=loan_id)
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    return CreatorCardLoanView.model_validate(loan)


@creator_router.get("/clubs/{club_id}/fan-share-market", response_model=CreatorClubShareMarketView)
def get_creator_club_fan_share_market(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubShareMarketView:
    try:
        market = service.get_market(club_id=club_id)
    except CreatorClubShareMarketError as exc:
        raise_creator_share_market_http(exc)
    return CreatorClubShareMarketView.model_validate(service.serialize_market(market, viewer=current_user))


@creator_router.post("/clubs/{club_id}/fan-share-market", response_model=CreatorClubShareMarketView, status_code=status.HTTP_201_CREATED)
def issue_creator_club_fan_shares(
    club_id: str,
    payload: CreatorClubShareMarketIssueRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubShareMarketView:
    try:
        market = service.issue_market(
            actor=current_user,
            club_id=club_id,
            share_price_coin=payload.share_price_coin,
            max_shares_issued=payload.max_shares_issued,
            max_shares_per_fan=payload.max_shares_per_fan,
            metadata_json=payload.metadata_json,
        )
        session.commit()
    except CreatorClubShareMarketError as exc:
        session.rollback()
        raise_creator_share_market_http(exc)
    return CreatorClubShareMarketView.model_validate(service.serialize_market(market, viewer=current_user))


@creator_router.post("/clubs/{club_id}/fan-share-market/purchase", response_model=CreatorClubSharePurchaseView, status_code=status.HTTP_201_CREATED)
def purchase_creator_club_fan_shares(
    club_id: str,
    payload: CreatorClubSharePurchaseRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubSharePurchaseView:
    try:
        purchase = service.purchase_shares(
            actor=current_user,
            club_id=club_id,
            share_count=payload.share_count,
        )
        session.commit()
    except CreatorClubShareMarketError as exc:
        session.rollback()
        raise_creator_share_market_http(exc)
    return CreatorClubSharePurchaseView.model_validate(service.serialize_purchase(purchase))


@creator_router.get("/clubs/{club_id}/fan-share-market/holding", response_model=CreatorClubShareHoldingView | None)
def get_my_creator_club_fan_share_holding(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubShareHoldingView | None:
    holding = service.get_holding(club_id=club_id, user_id=current_user.id)
    if holding is None:
        return None
    return CreatorClubShareHoldingView.model_validate(service.serialize_holding(holding))


@creator_router.get("/clubs/{club_id}/fan-share-market/distributions", response_model=list[CreatorClubShareDistributionView])
def list_creator_club_fan_share_distributions(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> list[CreatorClubShareDistributionView]:
    _ = current_user
    try:
        service.get_market(club_id=club_id)
    except CreatorClubShareMarketError as exc:
        raise_creator_share_market_http(exc)
    return [
        CreatorClubShareDistributionView.model_validate(service.serialize_distribution(item))
        for item in service.list_distributions(club_id=club_id)
    ]


@admin_router.get("/applications", response_model=list[CreatorApplicationView])
def list_creator_applications(
    current_admin: User = Depends(get_current_admin),
    service: CreatorApplicationService = Depends(get_application_service),
) -> list[CreatorApplicationView]:
    _ = current_admin
    applications = service.list_applications()
    return [CreatorApplicationView.model_validate(service.serialize_application(item)) for item in applications]


@admin_router.get("/dashboard", response_model=CreatorAdminDashboardView)
def get_creator_admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorAdminDashboardView:
    _ = current_admin
    return CreatorAdminDashboardView.model_validate(service.build_dashboard())


@admin_router.post("/applications/{application_id}/approve", response_model=CreatorApplicationView)
def approve_creator_application(
    application_id: str,
    payload: CreatorApplicationAdminActionRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorApplicationView:
    try:
        application = service.approve_application(
            application_id=application_id,
            reviewer=current_admin,
            review_notes=payload.review_notes,
            reason=payload.reason,
        )
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorApplicationView.model_validate(service.serialize_application(application))


@admin_router.post("/applications/{application_id}/reject", response_model=CreatorApplicationView)
def reject_creator_application(
    application_id: str,
    payload: CreatorApplicationAdminActionRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorApplicationView:
    try:
        application = service.reject_application(
            application_id=application_id,
            reviewer=current_admin,
            review_notes=payload.review_notes,
            reason=payload.reason,
        )
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorApplicationView.model_validate(service.serialize_application(application))


@admin_router.post("/applications/{application_id}/request-verification", response_model=CreatorApplicationView)
def request_creator_application_verification(
    application_id: str,
    payload: CreatorApplicationAdminActionRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: CreatorApplicationService = Depends(get_application_service),
) -> CreatorApplicationView:
    try:
        application = service.request_verification(
            application_id=application_id,
            reviewer=current_admin,
            review_notes=payload.review_notes,
            reason=payload.reason,
        )
        session.commit()
    except CreatorApplicationError as exc:
        session.rollback()
        raise_creator_application_http(exc)
    return CreatorApplicationView.model_validate(service.serialize_application(application))


@admin_router.post("/cards/assign", response_model=CreatorCardView, status_code=status.HTTP_201_CREATED)
def assign_creator_card(
    payload: CreatorCardAssignRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: CreatorCardService = Depends(get_creator_card_service),
) -> CreatorCardView:
    _ = current_admin
    try:
        card = service.assign_card(player_id=payload.player_id, owner_user_id=payload.owner_user_id)
        session.commit()
    except CreatorCardError as exc:
        session.rollback()
        raise_creator_card_http(exc)
    return CreatorCardView.model_validate(card)


@admin_router.get("/fan-share-market/control", response_model=CreatorClubShareMarketControlView)
def get_creator_fan_share_market_control(
    current_admin: User = Depends(get_current_admin),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubShareMarketControlView:
    _ = current_admin
    return CreatorClubShareMarketControlView.model_validate(service.serialize_control(service.get_admin_control()))


@admin_router.put("/fan-share-market/control", response_model=CreatorClubShareMarketControlView)
def update_creator_fan_share_market_control(
    payload: CreatorClubShareMarketControlUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: CreatorClubShareMarketService = Depends(get_creator_share_market_service),
) -> CreatorClubShareMarketControlView:
    try:
        control = service.update_admin_control(
            actor=current_admin,
            max_shares_per_club=payload.max_shares_per_club,
            max_shares_per_fan=payload.max_shares_per_fan,
            shareholder_revenue_share_bps=payload.shareholder_revenue_share_bps,
            issuance_enabled=payload.issuance_enabled,
            purchase_enabled=payload.purchase_enabled,
            max_primary_purchase_value_coin=payload.max_primary_purchase_value_coin,
        )
        session.commit()
    except CreatorClubShareMarketError as exc:
        session.rollback()
        raise_creator_share_market_http(exc)
    return CreatorClubShareMarketControlView.model_validate(service.serialize_control(control))


router = APIRouter()
router.include_router(legacy_creator_router)
router.include_router(creator_router)
router.include_router(admin_router)

api_router = APIRouter(prefix="/api")
api_router.include_router(creator_router)
api_router.include_router(admin_router)
router.include_router(api_router)


__all__ = ["router"]
