from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.ownership_group import OwnershipGroupClub, OwnershipGroupEvent
from app.models.user import User
from app.ownership_groups.schemas import (
    OwnershipGroupAddClubRequest,
    OwnershipGroupBudgetAllocateRequest,
    OwnershipGroupBudgetTransferRequest,
    OwnershipGroupClubView,
    OwnershipGroupCreateRequest,
    OwnershipGroupEventView,
    OwnershipGroupValidationView,
    OwnershipGroupView,
)
from app.ownership_groups.service import OwnershipGroupError, OwnershipGroupService

router = APIRouter(prefix="/ownership-groups", tags=["ownership-groups"])
admin_router = APIRouter(prefix="/admin/ownership-groups", tags=["admin-ownership-groups"])


def _service(session: Session = Depends(get_session)) -> OwnershipGroupService:
    return OwnershipGroupService(session)


def _group_view(group, service: OwnershipGroupService) -> OwnershipGroupView:
    club_rows = list(
        service.session.scalars(
            select(OwnershipGroupClub).where(OwnershipGroupClub.group_id == group.id).order_by(OwnershipGroupClub.created_at.asc())
        ).all()
    )
    events = list(
        service.session.scalars(
            select(OwnershipGroupEvent).where(OwnershipGroupEvent.group_id == group.id).order_by(OwnershipGroupEvent.created_at.desc()).limit(5)
        ).all()
    )
    clubs = []
    total_value = Decimal("0.0000")
    for row in club_rows:
        club = service.session.get(ClubProfile, row.club_id)
        if club is None:
            continue
        clubs.append(
            OwnershipGroupClubView(
                club_id=club.id,
                club_name=club.club_name,
                owner_user_id=club.owner_user_id,
                added_at=row.created_at,
            )
        )
        total_value += service.club_value(club.id)
    allocations = {key: value for key, value in service.budget_allocations(group).items()}
    metadata = dict(group.metadata_json or {})
    return OwnershipGroupView(
        id=group.id,
        owner_user_id=group.owner_user_id,
        name=group.name,
        clubs=clubs,
        total_value=total_value,
        reputation=float(group.reputation_score or 0.0),
        budget_pool=group.budget_pool,
        philosophy=group.philosophy,
        global_brand_strength=float(group.global_brand_strength or 0.0),
        scouting_network_boost=float(metadata.get("scouting_network_boost", 0.0) or 0.0),
        branding_boost=float(metadata.get("branding_boost", 0.0) or 0.0),
        shared_budget_enabled=group.shared_budget_enabled,
        budget_allocations=allocations,
        recent_events=[
            OwnershipGroupEventView(
                id=item.id,
                event_type=item.event_type,
                headline=item.headline,
                impact_json=dict(item.impact_json or {}),
                created_at=item.created_at,
            )
            for item in events
        ],
        metadata_json=metadata,
    )


@router.get("", response_model=list[OwnershipGroupView])
def list_ownership_groups(
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> list[OwnershipGroupView]:
    return [_group_view(group, service) for group in service.list_groups(actor=actor)]


@router.post("", response_model=OwnershipGroupView)
def create_ownership_group(
    payload: OwnershipGroupCreateRequest,
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupView:
    try:
        group = service.create_group(actor=actor, payload=payload)
        service.session.commit()
    except OwnershipGroupError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _group_view(group, service)


@router.get("/transfers/validate", response_model=OwnershipGroupValidationView)
def validate_internal_group_transfer(
    player_id: str = Query(..., min_length=1),
    selling_club_id: str | None = Query(default=None),
    buying_club_id: str | None = Query(default=None),
    bid_amount: Decimal = Query(..., gt=0),
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupValidationView:
    _ = actor
    return OwnershipGroupValidationView(**service.validate_transfer(
        player_id=player_id,
        selling_club_id=selling_club_id,
        buying_club_id=buying_club_id,
        bid_amount=bid_amount,
    ))


@router.get("/{group_id}", response_model=OwnershipGroupView)
def read_ownership_group(
    group_id: str,
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupView:
    try:
        group = service.get_group(actor=actor, group_id=group_id)
    except OwnershipGroupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    return _group_view(group, service)


@router.post("/{group_id}/clubs", response_model=OwnershipGroupView)
def add_club_to_ownership_group(
    group_id: str,
    payload: OwnershipGroupAddClubRequest,
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupView:
    try:
        group = service.add_club(actor=actor, group_id=group_id, club_id=payload.club_id)
        service.session.commit()
    except OwnershipGroupError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _group_view(group, service)


@router.post("/{group_id}/budget/allocate", response_model=OwnershipGroupView)
def allocate_group_budget(
    group_id: str,
    payload: OwnershipGroupBudgetAllocateRequest,
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupView:
    try:
        group = service.allocate_budget(actor=actor, group_id=group_id, club_id=payload.club_id, amount=payload.amount)
        service.session.commit()
    except OwnershipGroupError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _group_view(group, service)


@router.post("/{group_id}/budget/transfer", response_model=OwnershipGroupView)
def transfer_group_budget(
    group_id: str,
    payload: OwnershipGroupBudgetTransferRequest,
    actor: User = Depends(get_current_user),
    service: OwnershipGroupService = Depends(_service),
) -> OwnershipGroupView:
    try:
        group = service.transfer_budget(
            actor=actor,
            group_id=group_id,
            source_club_id=payload.source_club_id,
            target_club_id=payload.target_club_id,
            amount=payload.amount,
        )
        service.session.commit()
    except OwnershipGroupError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return _group_view(group, service)


@admin_router.post("/reputation-cycle", status_code=status.HTTP_200_OK)
def run_ownership_group_reputation_cycle(
    _admin=Depends(get_current_admin),
    service: OwnershipGroupService = Depends(_service),
) -> dict[str, int]:
    payload = service.run_reputation_cycle()
    service.session.commit()
    return payload


__all__ = ["admin_router", "router"]
