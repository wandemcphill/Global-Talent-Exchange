from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.transfer_bid import TransferBid
from app.models.user import User, UserRole


TRANSFER_BID_CREATE_PATH_PREFIX = "/api/transfers/windows/"
TRANSFER_BID_ACTION_MARKER = "/bids/"


def _assert_club_owner(session: Session, *, actor: User, club_id: str, action: str) -> None:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer club was not found")
    if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return
    if club.owner_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the {action} club owner can perform this transfer action",
        )


async def authorize_transfer_mutation(
    request: Request,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    if request.method != "POST":
        return

    path = request.url.path
    if not path.startswith(TRANSFER_BID_CREATE_PATH_PREFIX):
        return

    if path.endswith("/bids"):
        payload = await request.json()
        buying_club_id = str(payload.get("buying_club_id") or "").strip()
        if not buying_club_id:
            if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only an administrator can create a transfer bid without a buying club",
                )
            return
        _assert_club_owner(
            session,
            actor=actor,
            club_id=buying_club_id,
            action="buying",
        )
        return

    if TRANSFER_BID_ACTION_MARKER not in path:
        return

    marker_index = path.find(TRANSFER_BID_ACTION_MARKER)
    tail = path[marker_index + len(TRANSFER_BID_ACTION_MARKER) :]
    parts = [part.strip() for part in tail.split("/") if part.strip()]
    if not parts:
        return

    bid = session.get(TransferBid, parts[0])
    if bid is None:
        return

    action = parts[1] if len(parts) > 1 else None
    if action not in {"accept", "reject"}:
        return

    if bid.selling_club_id is None:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only an administrator can directly {action} a bid without a selling club",
            )
        return

    _assert_club_owner(
        session,
        actor=actor,
        club_id=bid.selling_club_id,
        action="selling",
    )
