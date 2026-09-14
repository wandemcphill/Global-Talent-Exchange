from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.transfer_bid import TransferBid
from app.models.user import User, UserRole


TRANSFER_BID_CREATE_PATH_PREFIX = "/api/transfers/windows/"
TRANSFER_BID_ACCEPT_PATH_MARKER = "/bids/"


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

    if not path.endswith("/bids") and "/bids/" not in path:
        return

    if path.endswith("/bids"):
        payload = await request.json()
        buying_club_id = str(payload.get("buying_club_id") or "").strip()
        if buying_club_id:
            _assert_club_owner(
                session,
                actor=actor,
                club_id=buying_club_id,
                action="buying",
            )
        return

    marker_index = path.find(TRANSFER_BID_ACCEPT_PATH_MARKER)
    if marker_index < 0:
        return
    tail = path[marker_index + len(TRANSFER_BID_ACCEPT_PATH_MARKER) :]
    bid_id = tail.split("/", 1)[0].strip()
    if not bid_id:
        return

    bid = session.get(TransferBid, bid_id)
    if bid is None:
        return
    if bid.selling_club_id is None:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an administrator can directly accept a bid without a selling club",
            )
        return

    _assert_club_owner(
        session,
        actor=actor,
        club_id=bid.selling_club_id,
        action="selling",
    )
