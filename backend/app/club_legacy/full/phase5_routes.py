"""HTTP routes for Club Legacy phase 5."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy.full import phase5
from app.club_legacy.full.http import run_legacy
from app.club_legacy.models import ClubLegacyPreseasonEvent, ClubLegacyPreseasonOffer

router = APIRouter()


class WindowBody(BaseModel):
    name: str
    starts_on: str
    ends_on: str


class InviteBody(BaseModel):
    window_id: str
    to_club_id: str
    match_on: str
    appearance_fee: Decimal


class RespondBody(BaseModel):
    decision: str
    as_staff: bool = False
    appearance_fee: Decimal | None = None
    match_on: str | None = None


class SettleBody(BaseModel):
    tv_pool: Decimal
    gift_pool: Decimal = Decimal("0")


class TournamentBody(BaseModel):
    window_id: str
    name: str
    match_on: str
    participant_club_ids: list[str] = Field(min_length=1)


class ParticipantBody(BaseModel):
    club_id: str


class TournamentSettleBody(BaseModel):
    tv_pool: Decimal


@router.post("/{club_id}/preseason/windows")
def open_window(
    club_id: str, body: WindowBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id, user

    def go():
        window = phase5.open_window(session, name=body.name, starts_on=body.starts_on, ends_on=body.ends_on)
        return {"id": window.id, "name": window.name, "starts_on": window.starts_on, "ends_on": window.ends_on}

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/invites")
def invite(
    club_id: str, body: InviteBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    def go():
        row = phase5.invite_preseason(
            session,
            window_id=body.window_id,
            from_club_id=club_id,
            to_club_id=body.to_club_id,
            match_on=body.match_on,
            appearance_fee=body.appearance_fee,
            user_id=user.id,
        )
        return phase5.invite_dict(row)

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/invites/{invite_id}/respond")
def respond(
    club_id: str,
    invite_id: str,
    body: RespondBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id

    def go():
        row = phase5.respond_preseason(
            session,
            invite_id=invite_id,
            user_id=user.id,
            decision=body.decision,
            as_staff=body.as_staff,
            appearance_fee=body.appearance_fee,
            match_on=body.match_on,
        )
        history = session.scalars(
            select(ClubLegacyPreseasonEvent)
            .where(ClubLegacyPreseasonEvent.invite_id == row.id)
            .order_by(ClubLegacyPreseasonEvent.sequence.asc())
        ).all()
        offers = session.scalars(
            select(ClubLegacyPreseasonOffer)
            .where(ClubLegacyPreseasonOffer.invite_id == row.id)
            .order_by(ClubLegacyPreseasonOffer.sequence.asc())
        ).all()
        payload = phase5.invite_dict(row)
        payload["history"] = [
            {"sequence": item.sequence, "status": item.status, "appearance_fee": str(item.appearance_fee), "match_on": item.match_on}
            for item in history
        ]
        payload["offers"] = [
            {
                "sequence": item.sequence,
                "status": item.status,
                "appearance_fee": str(item.appearance_fee),
                "match_on": item.match_on,
            }
            for item in offers
        ]
        return payload

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/invites/{invite_id}/settle")
def settle(
    club_id: str,
    invite_id: str,
    body: SettleBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id, user

    def go():
        row = phase5.settle_preseason(session, invite_id=invite_id, tv_pool=body.tv_pool, gift_pool=body.gift_pool)
        return phase5.settlement_dict(row)

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/tournaments")
def host_tournament(
    club_id: str, body: TournamentBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    def go():
        row = phase5.host_tournament(
            session,
            window_id=body.window_id,
            host_club_id=club_id,
            name=body.name,
            match_on=body.match_on,
            user_id=user.id,
            participant_club_ids=body.participant_club_ids,
        )
        return phase5.tournament_dict(row, body.participant_club_ids)

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/tournaments/{tournament_id}/participants")
def add_participant(
    club_id: str,
    tournament_id: str,
    body: ParticipantBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id

    def go():
        row = phase5.add_tournament_participant(
            session, tournament_id=tournament_id, club_id=body.club_id, user_id=user.id
        )
        return {"id": row.id, "tournament_id": row.tournament_id, "club_id": row.club_id}

    return run_legacy(session, go)


@router.post("/{club_id}/preseason/tournaments/{tournament_id}/settle")
def settle_tournament(
    club_id: str,
    tournament_id: str,
    body: TournamentSettleBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id, user

    def go():
        row = phase5.settle_tournament(session, tournament_id=tournament_id, tv_pool=body.tv_pool)
        return {
            "id": row.id,
            "rule_version": row.rule_version,
            "platform_amount": str(row.platform_amount),
            "host_amount": str(row.host_amount),
            "participant_amount": str(row.participant_amount),
            "audience": row.audience,
            "reputation_delta": row.reputation_delta,
        }

    return run_legacy(session, go)
