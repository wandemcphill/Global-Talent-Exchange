"""HTTP routes for Club Legacy phase 6."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy.full import phase6
from app.club_legacy.full.http import run_legacy

router = APIRouter()


class ContractBody(BaseModel):
    sponsor_name: str
    placement: str = "shirt_front"
    fee: Decimal
    zones: list[str] | None = None


class PublishBody(BaseModel):
    template_name: str
    zones: dict[str, str] = Field(default_factory=dict)


class PreviewBody(BaseModel):
    template_name: str = "Home"


class DeliveryBody(BaseModel):
    impressions: int
    note: str


@router.get("/{club_id}/sponsors/zones")
def read_zones(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    del club_id, user

    def go():
        return {"zones": phase6.commercial_inventory()}

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts")
def offer_contract(
    club_id: str, body: ContractBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    def go():
        contract = phase6.offer_sponsor(
            session,
            club_id=club_id,
            user_id=user.id,
            sponsor_name=body.sponsor_name,
            placement=body.placement,
            fee=body.fee,
            zones=body.zones,
        )
        return phase6.contract_dict(session, contract)

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/preview")
def preview_kit(
    club_id: str,
    contract_id: str,
    body: PreviewBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    def go():
        return phase6.preview_kit(
            session, club_id=club_id, user_id=user.id, contract_id=contract_id, template_name=body.template_name
        )

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/suggest")
def suggest_kit(
    club_id: str, contract_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    def go():
        return phase6.suggest_kit(session, club_id=club_id, user_id=user.id, contract_id=contract_id)

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/approve")
def approve_contract(
    club_id: str, contract_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        contract = phase6.approve_sponsor(session, contract_id=contract_id, user_id=user.id)
        return phase6.contract_dict(session, contract)

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/publish")
def publish_kit(
    club_id: str,
    contract_id: str,
    body: PublishBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    def go():
        kit = phase6.publish_kit(
            session,
            club_id=club_id,
            user_id=user.id,
            contract_id=contract_id,
            template_name=body.template_name,
            zones=body.zones,
        )
        return {
            "id": kit.id,
            "version": kit.version,
            "status": kit.status,
            "zones": kit.zones_json,
            "template_name": kit.template_name,
        }

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/delivery")
def report_delivery(
    club_id: str,
    contract_id: str,
    body: DeliveryBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id

    def go():
        contract = phase6.report_delivery(
            session, contract_id=contract_id, user_id=user.id, impressions=body.impressions, note=body.note
        )
        return phase6.contract_dict(session, contract)

    return run_legacy(session, go)


@router.post("/{club_id}/sponsors/contracts/{contract_id}/renew")
def renew_contract(
    club_id: str, contract_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        contract = phase6.renew_sponsor(session, contract_id=contract_id, user_id=user.id)
        return phase6.contract_dict(session, contract)

    return run_legacy(session, go)
