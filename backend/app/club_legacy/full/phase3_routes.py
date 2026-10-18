"""Phase 3 HTTP routes. Mounted under /owner/legacy/full/phase3."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy.delegation import require_owner
from app.club_legacy.full.http import run_legacy
from app.club_legacy.full.phase3 import club_page, financial_history, owner_net_worth

router = APIRouter(prefix="/full/phase3", tags=["club-legacy"])


@router.get("/{club_id}/page")
def read_page(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        return club_page(session, club_id)

    return run_legacy(session, go)


@router.get("/{club_id}/net-worth")
def read_net_worth(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        worth = owner_net_worth(session, user.id)
        from app.club_legacy.operations import club_valuation

        worth["club_valuation"] = str(club_valuation(session, club_id))
        return worth

    return run_legacy(session, go)


@router.get("/{club_id}/finance")
def read_finance(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        return {"club_id": club_id, "entries": financial_history(session, club_id)}

    return run_legacy(session, go)


@router.get("/{club_id}/showroom")
def read_showroom(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        page = club_page(session, club_id)
        return page["showroom"]

    return run_legacy(session, go)
