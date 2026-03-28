from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.broadcast_rights.schemas import (
    BroadcastAccessGrantRequest,
    BroadcastJobRunView,
    BroadcastMatchAccessView,
    BroadcastRevenueDistributionView,
    BroadcastRightOwnerView,
    BroadcastRightView,
    BroadcastRightsAcquireRequest,
    BroadcastRightsAuctionBidView,
    BroadcastRightsAuctionCreateRequest,
    BroadcastRightsAuctionView,
    BroadcastRightsBidCreateRequest,
    BroadcastRightsSummaryView,
)
from app.broadcast_rights.service import BroadcastRightsError, BroadcastRightsService
from app.models.broadcast_rights import BroadcastRevenueDistribution, BroadcastRightsBid
from app.models.user import User

router = APIRouter(prefix="/broadcast-rights", tags=["broadcast-rights"])
admin_router = APIRouter(prefix="/admin/broadcast-rights", tags=["admin-broadcast-rights"])


def _service(session: Session = Depends(get_session)) -> BroadcastRightsService:
    return BroadcastRightsService(session)


def _owner_view(owner_id: str, service: BroadcastRightsService) -> BroadcastRightOwnerView:
    owner_name = service.session.get(User, owner_id)
    if owner_id == "platform":
        return BroadcastRightOwnerView(owner_id=owner_id, owner_name="GTEX Platform", owner_type="platform")
    return BroadcastRightOwnerView(
        owner_id=owner_id,
        owner_name=(owner_name.display_name or owner_name.full_name or owner_name.username) if owner_name is not None else None,
        owner_type="user",
    )


def _right_view(item, service: BroadcastRightsService, *, viewers: int = 0) -> BroadcastRightView:
    revenue_generated = service.session.scalar(
        select(func.coalesce(func.sum(BroadcastRevenueDistribution.amount), 0)).where(
            BroadcastRevenueDistribution.broadcast_right_id == item.id
        )
    )
    return BroadcastRightView(
        id=item.id,
        competition_id=item.competition_id,
        owner=_owner_view(item.owner_id, service),
        acquisition_price=item.acquisition_price,
        revenue_share_percentage=item.revenue_share_percentage,
        exclusivity=item.exclusivity,
        start_date=item.start_date,
        end_date=item.end_date,
        metadata_json=dict(item.metadata_json or {}),
        revenue_generated=revenue_generated or 0,
        viewers=viewers,
    )


def _auction_view(item, service: BroadcastRightsService) -> BroadcastRightsAuctionView:
    bids = list(
        service.session.scalars(
            select(BroadcastRightsBid)
            .where(BroadcastRightsBid.auction_id == item.id)
            .order_by(BroadcastRightsBid.amount.desc(), BroadcastRightsBid.created_at.asc())
        ).all()
    )
    return BroadcastRightsAuctionView(
        id=item.id,
        competition_id=item.competition_id,
        seller_owner_id=item.seller_owner_id,
        reserve_price=item.reserve_price,
        revenue_share_percentage=item.revenue_share_percentage,
        exclusivity=item.exclusivity,
        start_date=item.start_date,
        end_date=item.end_date,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        status=item.status,
        bids=[
            BroadcastRightsAuctionBidView(
                id=bid.id,
                bidder_user_id=bid.bidder_user_id,
                bidder_name=(_owner_view(bid.bidder_user_id, service).owner_name),
                amount=bid.amount,
                status=bid.status,
                created_at=bid.created_at,
            )
            for bid in bids
        ],
    )


@router.get("/competitions/{competition_id}", response_model=BroadcastRightsSummaryView)
def read_broadcast_rights_summary(competition_id: str, service: BroadcastRightsService = Depends(_service)) -> BroadcastRightsSummaryView:
    try:
        payload = service.get_summary(competition_id)
    except BroadcastRightsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    return BroadcastRightsSummaryView(
        competition_id=competition_id,
        competition_name=payload["competition"].name,
        owner=_owner_view(payload["rights"][0].owner_id, service) if payload["rights"] else None,
        revenue_generated=payload["revenue_generated"],
        viewers=payload["viewers"],
        active_rights=[_right_view(item, service, viewers=payload["viewers"]) for item in payload["rights"]],
        auctions=[_auction_view(item, service) for item in payload["auctions"]],
    )


@router.post("/competitions/{competition_id}/acquire", response_model=BroadcastRightView)
def acquire_broadcast_rights(
    competition_id: str,
    payload: BroadcastRightsAcquireRequest,
    actor: User = Depends(get_current_user),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastRightView:
    try:
        item = service.acquire_rights(actor=actor, competition_id=competition_id, payload=payload)
        service.session.commit()
    except BroadcastRightsError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _right_view(item, service)


@router.post("/competitions/{competition_id}/auctions", response_model=BroadcastRightsAuctionView)
def create_broadcast_rights_auction(
    competition_id: str,
    payload: BroadcastRightsAuctionCreateRequest,
    actor: User = Depends(get_current_user),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastRightsAuctionView:
    try:
        item = service.create_auction(actor=actor, competition_id=competition_id, payload=payload)
        service.session.commit()
    except BroadcastRightsError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _auction_view(item, service)


@router.post("/auctions/{auction_id}/bids", response_model=BroadcastRightsAuctionBidView)
def bid_for_broadcast_rights(
    auction_id: str,
    payload: BroadcastRightsBidCreateRequest,
    actor: User = Depends(get_current_user),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastRightsAuctionBidView:
    try:
        item = service.place_bid(actor=actor, auction_id=auction_id, payload=payload)
        service.session.commit()
    except BroadcastRightsError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return BroadcastRightsAuctionBidView(
        id=item.id,
        bidder_user_id=item.bidder_user_id,
        bidder_name=_owner_view(item.bidder_user_id, service).owner_name,
        amount=item.amount,
        status=item.status,
        created_at=item.created_at,
    )


@router.post("/{right_id}/grants", status_code=status.HTTP_204_NO_CONTENT)
def grant_broadcast_access(
    right_id: str,
    payload: BroadcastAccessGrantRequest,
    actor: User = Depends(get_current_user),
    service: BroadcastRightsService = Depends(_service),
) -> None:
    try:
        service.grant_access(actor=actor, right_id=right_id, payload=payload)
        service.session.commit()
    except BroadcastRightsError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/matches/{match_id}/access", response_model=BroadcastMatchAccessView)
def read_match_broadcast_access(
    match_id: str,
    competition_id: str | None = Query(default=None),
    pay_to_view: bool = Query(default=False),
    actor: User = Depends(get_current_user),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastMatchAccessView:
    try:
        payload = service.resolve_match_access(
            actor=actor,
            match_id=match_id,
            competition_id=competition_id,
            pay_to_view=pay_to_view,
        )
        service.session.commit()
    except BroadcastRightsError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return BroadcastMatchAccessView(**payload)


@router.post("/matches/{match_id}/distribute", response_model=BroadcastRevenueDistributionView)
def distribute_broadcast_revenue(
    match_id: str,
    competition_id: str | None = Query(default=None),
    home_club_id: str | None = Query(default=None),
    away_club_id: str | None = Query(default=None),
    _admin=Depends(get_current_admin),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastRevenueDistributionView:
    payload = service.distribute_match_revenue(
        match_id=match_id,
        competition_id=competition_id,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
    )
    service.session.commit()
    return BroadcastRevenueDistributionView(**payload)


@admin_router.post("/jobs/run", response_model=BroadcastJobRunView)
def run_broadcast_jobs(
    _admin=Depends(get_current_admin),
    service: BroadcastRightsService = Depends(_service),
) -> BroadcastJobRunView:
    revenue = service.run_revenue_distribution_cycle()
    expiry = service.expire_rights_and_relist()
    service.session.commit()
    return BroadcastJobRunView(
        processed_matches=revenue["processed_matches"],
        settled_auctions=revenue["settled_auctions"],
        expired_rights=expiry["expired_rights"],
        relisted_auctions=expiry["relisted_auctions"],
    )


__all__ = ["admin_router", "router"]
