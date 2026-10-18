"""Phase 1 HTTP routes. Mounted under /owner/legacy/full/phase1."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.club_legacy.delegation import require_owner
from app.club_legacy.full.http import run_legacy
from app.club_legacy.full.phase1 import (
    current_settings,
    resolve_location,
    separate_ratings,
    settings_dict,
    update_settings,
)
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState

router = APIRouter(prefix="/full/phase1", tags=["club-legacy"])


class LocationBody(BaseModel):
    city_name: str | None = None
    country_code: str | None = None
    continent_code: str | None = None


class SettingsBody(BaseModel):
    transfer_fee_rate: Decimal
    inventory_caps: dict[str, int] = Field(default_factory=dict)
    preseason_shares: dict[str, Decimal] = Field(default_factory=dict)


@router.post("/location")
def check_location(
    body: LocationBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del user

    def go():
        city, country, continent = resolve_location(
            city_name=body.city_name, country_code=body.country_code, continent_code=body.continent_code
        )
        from app.club_legacy.geography import continent_name

        return {
            "city": city,
            "country_code": country,
            "continent_code": continent,
            "continent_name": continent_name(continent),
        }

    return run_legacy(session, go)


@router.get("/settings")
def read_settings(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    del user

    def go():
        return settings_dict(current_settings(session))

    return run_legacy(session, go)


@router.put("/settings")
def write_settings(
    body: SettingsBody, user=Depends(get_current_admin), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        row = update_settings(
            session,
            actor_user_id=user.id,
            transfer_fee_rate=body.transfer_fee_rate,
            inventory_caps=body.inventory_caps,
            preseason_shares={key: str(value) for key, value in body.preseason_shares.items()},
        )
        return settings_dict(row)

    return run_legacy(session, go)


@router.get("/{club_id}/ratings")
def read_ratings(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        facilities = state.facilities_json if state else {}
        cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        return separate_ratings(session, club_id, facilities, cash)

    return run_legacy(session, go)
