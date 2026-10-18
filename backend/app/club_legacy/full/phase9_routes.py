"""Season, catalogue, and subsystem routes.

Turning one subsystem flag off hides only that subsystem. Turning club_legacy off hides all of them.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy import flags
from app.club_legacy.full import phase9
from app.club_legacy.full.http import run
from app.club_legacy.models import ClubLegacyCatalogueItem, ClubLegacyPreseasonInvite, ClubLegacySponsorContract

router = APIRouter()


class SeasonBody(BaseModel):
    seasons: int = Field(default=3, ge=1, le=12)
    tier: str
    seed: int = 0


class FailureBody(BaseModel):
    reason: str = Field(min_length=1)


@router.post("/{club_id}/seasons/simulate")
def simulate(
    club_id: str, body: SeasonBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session)
        return phase9.simulate_seasons(session, club_id, body.seasons, body.tier, seed=body.seed)

    return run(session, go)


@router.post("/{club_id}/catalogue/load")
def read_catalogue(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id, user

    def go():
        flags.require_enabled(session)
        return phase9.load_catalogue(session, 40)

    return run(session, go)


@router.post("/{club_id}/showroom/failures")
def showroom_failure(
    club_id: str, body: FailureBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session)
        failure = phase9.record_showroom_failure(session, club_id=club_id, reason=body.reason)
        return {"id": failure.id, "reason": failure.reason}

    return run(session, go)


@router.get("/{club_id}/market/supply")
def market_supply(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id, user

    def go():
        flags.require_enabled(session, flags.MARKET_KEY)
        from app.club_legacy.operations import seed_catalogue

        seed_catalogue(session)
        items = []
        for item in session.scalars(select(ClubLegacyCatalogueItem).order_by(ClubLegacyCatalogueItem.sku.asc())).all():
            remaining = None if item.supply_cap is None else int(item.supply_cap) - int(item.minted_count)
            items.append(
                {
                    "sku": item.sku,
                    "supply_cap": item.supply_cap,
                    "minted_count": int(item.minted_count),
                    "remaining": remaining,
                }
            )
        return {"items": items}

    return run(session, go)


@router.get("/{club_id}/preseason/invitations")
def preseason_invitations(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session, flags.PRESEASON_KEY)
        rows = session.scalars(
            select(ClubLegacyPreseasonInvite).where(
                (ClubLegacyPreseasonInvite.from_club_id == club_id) | (ClubLegacyPreseasonInvite.to_club_id == club_id)
            )
        ).all()
        accepted = sum(1 for row in rows if row.status == "accepted")
        return {
            "invitations": [
                {
                    "id": row.id,
                    "match_on": row.match_on,
                    "status": row.status,
                    "appearance_fee": str(row.appearance_fee),
                }
                for row in rows
            ],
            "invitation_count": len(rows),
            "acceptance": accepted,
        }

    return run(session, go)


@router.get("/{club_id}/sponsors/contracts")
def sponsor_contracts(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        flags.require_enabled(session, flags.SPONSORS_KEY)
        rows = session.scalars(
            select(ClubLegacySponsorContract).where(ClubLegacySponsorContract.club_id == club_id)
        ).all()
        return {
            "contracts": [
                {
                    "id": row.id,
                    "sponsor_name": row.sponsor_name,
                    "placement": row.placement,
                    "status": row.status,
                    "fee": str(row.fee),
                }
                for row in rows
            ]
        }

    return run(session, go)
