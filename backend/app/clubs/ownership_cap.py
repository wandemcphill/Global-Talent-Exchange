"""Controlling-ownership cap for GTEX club empires.

A single user may own up to three clubs (conglomerate feel). Token/DAO
shareholdings are a different domain and are not counted here.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubLifecycleStatus, ClubProfile

MAX_OWNED_CLUBS = 3


class ClubOwnershipCapError(ValueError):
    """Raised when a create/buy would exceed [MAX_OWNED_CLUBS]."""

    def __init__(self, *, owned: int, limit: int = MAX_OWNED_CLUBS) -> None:
        self.owned = owned
        self.limit = limit
        self.reason = "club_ownership_cap_reached"
        super().__init__(
            f"You already own {owned} clubs. GTEX caps controlling ownership at {limit}."
        )


def count_owned_clubs(session: Session, owner_user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ClubProfile)
            .where(ClubProfile.owner_user_id == owner_user_id)
            .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
        )
        or 0
    )


def list_owned_club_ids(session: Session, owner_user_id: str) -> list[str]:
    rows = session.scalars(
        select(ClubProfile.id)
        .where(ClubProfile.owner_user_id == owner_user_id)
        .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
        .order_by(ClubProfile.created_at.asc())
    ).all()
    return [str(item) for item in rows]


def assert_can_acquire_club(session: Session, owner_user_id: str) -> int:
    """Ensure the user can take controlling ownership of one more club."""
    owned = count_owned_clubs(session, owner_user_id)
    if owned >= MAX_OWNED_CLUBS:
        raise ClubOwnershipCapError(owned=owned)
    return owned


__all__ = [
    "MAX_OWNED_CLUBS",
    "ClubOwnershipCapError",
    "assert_can_acquire_club",
    "count_owned_clubs",
    "list_owned_club_ids",
]
