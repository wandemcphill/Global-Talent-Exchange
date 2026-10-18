"""Governance routes. Hidden when club_legacy or club_legacy_governance is off."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy import flags
from app.club_legacy.full import phase8
from app.club_legacy.full.http import run

router = APIRouter()


class CaseBody(BaseModel):
    rule_code: str = Field(min_length=2, max_length=64)
    allegation: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class RulingBody(BaseModel):
    sanction: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1)


class AppealBody(BaseModel):
    outcome: str = Field(min_length=1)


class StakeBody(BaseModel):
    holder_user_id: str
    percentage: str
    voting_rights: str | None = None


class DistributionBody(BaseModel):
    amount: str
    idempotency_key: str = Field(min_length=2, max_length=128)


def _guard(session: Session) -> None:
    flags.require_enabled(session, flags.GOVERNANCE_KEY)


@router.post("/{club_id}/governance/cases")
def open_case(
    club_id: str, body: CaseBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        return phase8.case_dict(
            phase8.open_case(
                session,
                club_id=club_id,
                rule_code=body.rule_code,
                allegation=body.allegation,
                evidence=body.evidence,
            )
        )

    return run(session, go)


@router.get("/{club_id}/governance/cases")
def list_cases(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        from sqlalchemy import select

        from app.club_legacy.models import ClubLegacyCase

        rows = session.scalars(select(ClubLegacyCase).where(ClubLegacyCase.club_id == club_id)).all()
        return {"cases": [phase8.case_dict(row) for row in rows]}

    return run(session, go)


@router.post("/governance/cases/{case_id}/ruling")
def rule_case(
    case_id: str, body: RulingBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        return phase8.case_dict(phase8.rule_case(session, case_id=case_id, sanction=body.sanction, reason=body.reason))

    return run(session, go)


@router.post("/governance/cases/{case_id}/appeal")
def appeal_case(
    case_id: str, body: AppealBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        return phase8.case_dict(phase8.appeal_case(session, case_id=case_id, outcome=body.outcome))

    return run(session, go)


@router.get("/{club_id}/governance/trades")
def list_trades(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        return {"trades": [phase8.trade_review_dict(row) for row in phase8.list_trade_reviews(session, club_id)]}

    return run(session, go)


@router.post("/{club_id}/governance/stakes")
def put_stake(
    club_id: str, body: StakeBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        _guard(session)
        stake = phase8.set_stake(
            session,
            club_id=club_id,
            holder_user_id=body.holder_user_id,
            percentage=body.percentage,
            voting_rights=body.voting_rights,
        )
        return {
            "holder_user_id": stake.holder_user_id,
            "percentage": str(stake.percentage),
            "voting_rights": str(stake.voting_rights),
            "economic_interest": str(
                phase8.economic_interest(session, club_id=club_id, holder_user_id=stake.holder_user_id)
            ),
        }

    return run(session, go)


@router.post("/{club_id}/governance/distributions")
def pay_distribution(
    club_id: str, body: DistributionBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        _guard(session)
        distribution = phase8.distribute(
            session, club_id=club_id, user_id=user.id, amount=body.amount, idempotency_key=body.idempotency_key
        )
        return phase8.distribution_dict(session, distribution)

    return run(session, go)


@router.get("/{club_id}/governance/net-worth")
def read_net_worth(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id

    def go():
        _guard(session)
        return phase8.owner_net_worth(session, user.id)

    return run(session, go)
