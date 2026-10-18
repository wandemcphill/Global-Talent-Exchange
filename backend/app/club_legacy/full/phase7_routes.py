"""Manager negotiation routes. Hidden when club_legacy is off."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy import flags
from app.club_legacy.full import phase7
from app.club_legacy.full.http import run

router = APIRouter()


class ManagerBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    personality: str = Field(min_length=1, max_length=40)
    ambition: int = Field(ge=0, le=20)
    wage_expectation: str
    seed: int = 1


class OfferBody(BaseModel):
    wage: str
    contract_length: int = Field(ge=1, le=8)
    role: str = Field(min_length=1, max_length=40)
    prestige: int = 10
    seed: int = 1


class RespondBody(BaseModel):
    decision: str
    wage: str | None = None
    contract_length: int | None = None
    role: str | None = None


class PromiseBody(BaseModel):
    subject: str = Field(min_length=1, max_length=160)
    manager_id: str | None = None


class ResolvePromiseBody(BaseModel):
    kept: bool


class RetentionBody(BaseModel):
    rival_wage: str
    rival_prestige: int = 40
    seed: int = 1


@router.post("/{club_id}/managers")
def create_manager(
    club_id: str, body: ManagerBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id

    def go():
        flags.require_enabled(session)
        manager = phase7.register_manager(
            session,
            name=body.name,
            personality=body.personality,
            ambition=body.ambition,
            wage_expectation=body.wage_expectation,
            seed=body.seed,
        )
        return phase7.manager_dict(manager)

    return run(session, go)


@router.post("/{club_id}/managers/{manager_id}/offers")
def create_offer(
    club_id: str,
    manager_id: str,
    body: OfferBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    def go():
        flags.require_enabled(session)
        offer = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=user.id,
            manager_id=manager_id,
            wage=body.wage,
            contract_length=body.contract_length,
            role=body.role,
            prestige=body.prestige,
            seed=body.seed,
        )
        return phase7.offer_dict(offer)

    return run(session, go)


@router.post("/offers/{offer_id}/respond")
def respond_offer(
    offer_id: str, body: RespondBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session)
        offer = phase7.respond_to_offer(
            session,
            offer_id=offer_id,
            decision=body.decision,
            wage=body.wage,
            contract_length=body.contract_length,
            role=body.role,
        )
        return phase7.offer_dict(offer)

    return run(session, go)


@router.get("/{club_id}/managers/{manager_id}/history")
def read_history(
    club_id: str, manager_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id, user

    def go():
        flags.require_enabled(session)
        return {"offers": [phase7.offer_dict(offer) for offer in phase7.offer_history(session, manager_id)]}

    return run(session, go)


@router.post("/{club_id}/promises")
def create_promise(
    club_id: str, body: PromiseBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        flags.require_enabled(session)
        promise = phase7.make_promise(
            session, club_id=club_id, user_id=user.id, subject=body.subject, manager_id=body.manager_id
        )
        return {"id": promise.id, "status": promise.status, "trust": promise.trust, "manager_id": promise.manager_id}

    return run(session, go)


@router.post("/promises/{promise_id}/resolve")
def resolve_promise(
    promise_id: str, body: ResolvePromiseBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session)
        promise = phase7.resolve_promise(session, promise_id=promise_id, kept=body.kept)
        from app.club_legacy.models import ClubLegacyManager

        manager = session.get(ClubLegacyManager, promise.manager_id) if promise.manager_id else None
        relationship = manager.relationship_score if manager is not None else None
        return {"id": promise.id, "status": promise.status, "trust": promise.trust, "relationship_score": relationship}

    return run(session, go)


@router.post("/{club_id}/managers/{manager_id}/gifts")
def give_gift(
    club_id: str, manager_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session)
        event = phase7.record_gift(session, manager_id=manager_id, club_id=club_id)
        return {
            "id": event.id,
            "kind": event.kind,
            "delta": event.delta,
            "score_before": event.score_before,
            "score_after": event.score_after,
        }

    return run(session, go)


@router.post("/{club_id}/managers/{manager_id}/poach")
def poach(
    club_id: str, manager_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        flags.require_enabled(session)
        manager = phase7.poach_manager(session, manager_id=manager_id, from_club_id=club_id, user_id=user.id)
        return phase7.manager_dict(manager)

    return run(session, go)


@router.post("/{club_id}/managers/{manager_id}/retention")
def retention(
    club_id: str,
    manager_id: str,
    body: RetentionBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    del club_id, user

    def go():
        flags.require_enabled(session)
        return phase7.consider_retention(
            session,
            manager_id=manager_id,
            rival_wage=body.rival_wage,
            rival_prestige=body.rival_prestige,
            seed=body.seed,
        )

    return run(session, go)
