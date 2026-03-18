from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.club_sale_market.schemas import (
    ClubSaleHistoryView,
    ClubSaleInquiryCollectionView,
    ClubSaleInquiryCreateRequest,
    ClubSaleInquiryRespondRequest,
    ClubSaleInquiryView,
    ClubSaleListingCancelRequest,
    ClubSaleListingCollectionView,
    ClubSaleListingCreateRequest,
    ClubSaleListingDetailView,
    ClubSaleListingUpdateRequest,
    ClubSaleOfferCollectionView,
    ClubSaleOfferCounterRequest,
    ClubSaleOfferCreateRequest,
    ClubSaleOfferRespondRequest,
    ClubSaleOfferView,
    ClubSaleTransferExecuteRequest,
    ClubSaleTransferExecutionView,
    ClubSaleValuationView,
)
from backend.app.club_sale_market.service import ClubSaleMarketError, ClubSaleMarketService
from backend.app.models.user import User
from backend.app.wallets.service import InsufficientBalanceError

router = APIRouter(tags=["club_sale_market"])


def get_service(session: Session = Depends(get_session)) -> ClubSaleMarketService:
    return ClubSaleMarketService(session=session)


def _raise_http(exc: ClubSaleMarketError) -> None:
    if exc.reason in {
        "club_sale_club_not_found",
        "club_sale_listing_not_found",
        "club_sale_public_listing_not_found",
        "club_sale_inquiry_not_found",
        "club_sale_offer_not_found",
        "club_sale_transfer_not_found",
        "club_sale_user_not_found",
        "club_sale_valuation_not_found",
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.reason) from exc
    if exc.reason in {
        "club_sale_owner_required",
        "club_sale_listing_owner_required",
        "club_sale_self_inquiry_forbidden",
        "club_sale_self_offer_forbidden",
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.reason) from exc
    if exc.reason in {
        "club_sale_listing_already_active",
        "club_sale_listing_unavailable",
        "club_sale_offer_already_open",
        "club_sale_offer_not_actionable",
        "club_sale_transfer_path_invalid",
        "club_sale_transfer_already_settled",
        "club_sale_listing_update_blocked",
        "club_sale_listing_cancel_blocked",
        "club_sale_inquiry_closed",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason) from exc


@router.get("/api/clubs/{club_id}/valuation", response_model=ClubSaleValuationView)
def get_club_sale_market_valuation(
    club_id: str,
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleValuationView:
    try:
        payload = service.get_valuation(club_id=club_id)
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleValuationView.model_validate(payload)


@router.get("/api/clubs/sale-market/listings", response_model=ClubSaleListingCollectionView)
def list_public_club_sale_market_listings(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingCollectionView:
    payload = service.list_public_listings(limit=limit, offset=offset)
    return ClubSaleListingCollectionView.model_validate(payload)


@router.get("/api/clubs/{club_id}/sale-market", response_model=ClubSaleListingDetailView)
def get_public_club_sale_market_listing(
    club_id: str,
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingDetailView:
    try:
        payload = service.get_public_listing(club_id=club_id)
    except ClubSaleMarketError as exc:
        _raise_http(exc)
    return ClubSaleListingDetailView.model_validate(payload)


@router.post(
    "/api/clubs/{club_id}/sale-market/listing",
    response_model=ClubSaleListingDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_club_sale_market_listing(
    club_id: str,
    payload: ClubSaleListingCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingDetailView:
    try:
        body = service.create_listing(actor=current_user, club_id=club_id, **payload.model_dump())
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleListingDetailView.model_validate(body)


@router.put("/api/clubs/{club_id}/sale-market/listing", response_model=ClubSaleListingDetailView)
def update_club_sale_market_listing(
    club_id: str,
    payload: ClubSaleListingUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingDetailView:
    try:
        body = service.update_listing(actor=current_user, club_id=club_id, **payload.model_dump())
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleListingDetailView.model_validate(body)


@router.post("/api/clubs/{club_id}/sale-market/listing/cancel", response_model=ClubSaleListingDetailView)
def cancel_club_sale_market_listing(
    club_id: str,
    payload: ClubSaleListingCancelRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingDetailView:
    try:
        body = service.cancel_listing(actor=current_user, club_id=club_id, reason=payload.reason)
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleListingDetailView.model_validate(body)


@router.get("/api/me/clubs/sale-market/listings", response_model=ClubSaleListingCollectionView)
def list_my_club_sale_market_listings(
    current_user: User = Depends(get_current_user),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleListingCollectionView:
    payload = service.list_my_listings(actor=current_user)
    return ClubSaleListingCollectionView.model_validate(payload)


@router.post(
    "/api/clubs/{club_id}/sale-market/inquiries",
    response_model=ClubSaleInquiryView,
    status_code=status.HTTP_201_CREATED,
)
def create_club_sale_market_inquiry(
    club_id: str,
    payload: ClubSaleInquiryCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleInquiryView:
    try:
        body = service.create_inquiry(actor=current_user, club_id=club_id, **payload.model_dump())
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleInquiryView.model_validate(body)


@router.get("/api/clubs/{club_id}/sale-market/inquiries", response_model=ClubSaleInquiryCollectionView)
def list_club_sale_market_inquiries(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleInquiryCollectionView:
    try:
        payload = service.list_inquiries(actor=current_user, club_id=club_id)
    except ClubSaleMarketError as exc:
        _raise_http(exc)
    return ClubSaleInquiryCollectionView.model_validate(payload)


@router.post(
    "/api/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond",
    response_model=ClubSaleInquiryView,
)
def respond_club_sale_market_inquiry(
    club_id: str,
    inquiry_id: str,
    payload: ClubSaleInquiryRespondRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleInquiryView:
    try:
        body = service.respond_inquiry(
            actor=current_user,
            club_id=club_id,
            inquiry_id=inquiry_id,
            **payload.model_dump(),
        )
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleInquiryView.model_validate(body)


@router.post(
    "/api/clubs/{club_id}/sale-market/offers",
    response_model=ClubSaleOfferView,
    status_code=status.HTTP_201_CREATED,
)
def create_club_sale_market_offer(
    club_id: str,
    payload: ClubSaleOfferCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferView:
    try:
        body = service.create_offer(actor=current_user, club_id=club_id, **payload.model_dump())
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleOfferView.model_validate(body)


@router.get("/api/clubs/{club_id}/sale-market/offers", response_model=ClubSaleOfferCollectionView)
def list_club_sale_market_offers(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferCollectionView:
    try:
        payload = service.list_offers(actor=current_user, club_id=club_id)
    except ClubSaleMarketError as exc:
        _raise_http(exc)
    return ClubSaleOfferCollectionView.model_validate(payload)


@router.get("/api/me/clubs/sale-market/offers", response_model=ClubSaleOfferCollectionView)
def list_my_club_sale_market_offers(
    current_user: User = Depends(get_current_user),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferCollectionView:
    payload = service.list_my_offers(actor=current_user)
    return ClubSaleOfferCollectionView.model_validate(payload)


@router.post("/api/clubs/{club_id}/sale-market/offers/{offer_id}/counter", response_model=ClubSaleOfferView)
def counter_club_sale_market_offer(
    club_id: str,
    offer_id: str,
    payload: ClubSaleOfferCounterRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferView:
    try:
        body = service.counter_offer(
            actor=current_user,
            club_id=club_id,
            offer_id=offer_id,
            **payload.model_dump(),
        )
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleOfferView.model_validate(body)


@router.post("/api/clubs/{club_id}/sale-market/offers/{offer_id}/accept", response_model=ClubSaleOfferView)
def accept_club_sale_market_offer(
    club_id: str,
    offer_id: str,
    payload: ClubSaleOfferRespondRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferView:
    try:
        body = service.accept_offer(
            actor=current_user,
            club_id=club_id,
            offer_id=offer_id,
            **payload.model_dump(),
        )
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleOfferView.model_validate(body)


@router.post("/api/clubs/{club_id}/sale-market/offers/{offer_id}/reject", response_model=ClubSaleOfferView)
def reject_club_sale_market_offer(
    club_id: str,
    offer_id: str,
    payload: ClubSaleOfferRespondRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleOfferView:
    try:
        body = service.reject_offer(
            actor=current_user,
            club_id=club_id,
            offer_id=offer_id,
            **payload.model_dump(),
        )
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    return ClubSaleOfferView.model_validate(body)


@router.post("/api/clubs/{club_id}/sale-market/transfer", response_model=ClubSaleTransferExecutionView)
def execute_club_sale_market_transfer(
    club_id: str,
    payload: ClubSaleTransferExecuteRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleTransferExecutionView:
    try:
        body = service.execute_transfer(
            actor=current_user,
            club_id=club_id,
            offer_id=payload.offer_id,
            executed_sale_price=payload.executed_sale_price,
            metadata_json=payload.metadata_json,
        )
        session.commit()
    except ClubSaleMarketError as exc:
        session.rollback()
        _raise_http(exc)
    except InsufficientBalanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ClubSaleTransferExecutionView.model_validate(body)


@router.get("/api/clubs/{club_id}/sale-market/history", response_model=ClubSaleHistoryView)
def get_club_sale_market_history(
    club_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ClubSaleMarketService = Depends(get_service),
) -> ClubSaleHistoryView:
    try:
        payload = service.history_for_club(actor=current_user, club_id=club_id, limit=limit)
    except ClubSaleMarketError as exc:
        _raise_http(exc)
    return ClubSaleHistoryView.model_validate(payload)
