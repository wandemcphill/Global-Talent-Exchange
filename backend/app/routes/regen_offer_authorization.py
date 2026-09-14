from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole


REGEN_QUOTE_PATH_MARKER = "/api/players/"
REGEN_QUOTE_PATH_SUFFIX = "/regen/contract-offers/quote"


async def authorize_regen_offer_quote(
    request: Request,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    if request.method != "POST":
        return
    path = request.url.path
    if not path.startswith(REGEN_QUOTE_PATH_MARKER) or not path.endswith(REGEN_QUOTE_PATH_SUFFIX):
        return

    if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid regen contract-offer payload is required",
        ) from exc

    offering_club_id = str(payload.get("offering_club_id") or "").strip()
    if not offering_club_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="offering_club_id is required",
        )

    club = session.get(ClubProfile, offering_club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offering club was not found")
    if club.owner_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the offering club owner can quote a regen contract offer",
        )
