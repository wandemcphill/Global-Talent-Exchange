from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile


def _profile_identity(club: object | None) -> tuple[str, str] | None:
    owner_user_id = getattr(club, "owner_user_id", None)
    club_id = getattr(club, "id", None)
    if isinstance(owner_user_id, str) and owner_user_id.strip() and isinstance(club_id, str) and club_id.strip():
        return owner_user_id, club_id
    return None


def resolve_gift_recipient_club(session: Session, recipient_club_id: str) -> tuple[str, str | None] | None:
    """Resolve a gift target to an owner profile and an optional club profile id.

    Match rails send owner-console club ids as well as club profile ids. A gift
    can only store a club profile foreign key, so an owner club is translated to
    that owner's profile when one exists, and otherwise to the owner user alone.
    """
    profile = _profile_identity(session.get(ClubProfile, recipient_club_id))
    if profile is not None:
        return profile

    from app.owner_console.models import OwnerClubState

    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == recipient_club_id))
    owner_user_id = getattr(state, "owner_user_id", None)
    if not isinstance(owner_user_id, str) or not owner_user_id.strip():
        return None
    owned_profile = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == owner_user_id).limit(1))
    owned = _profile_identity(owned_profile)
    if owned is not None:
        return owned
    return owner_user_id, None
