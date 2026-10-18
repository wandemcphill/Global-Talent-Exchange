"""Unauthenticated club card.

The owner showroom in ``app.club_legacy.operations.showroom`` stays the
GLB exhibit and still requires the owner. This card is a separate public
page. It returns only the fields a logged-out caller is allowed to see.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.owner_console.models import OwnerCompetition, OwnerCompetitionEntry
from app.owner_console.service import OwnerError

PUBLIC_SHOWROOM_KEYS = (
    "club_name",
    "short_name",
    "city",
    "country_code",
    "primary_color",
    "secondary_color",
    "founded",
    "crest_url",
    "trophies",
)


def public_showroom(session: Session, code: str) -> dict[str, Any]:
    """Return the public card for a club slug.

    ``code`` is the club profile slug. An unknown slug is a 404. Finances,
    sponsors, facilities, fans, prestige, players, staff, and asset inventory
    are never read into the response.
    """
    profile = session.scalar(select(ClubProfile).where(ClubProfile.slug == code))
    if profile is None or profile.visibility != "public":
        raise OwnerError("showroom_not_found", 404, "Showroom not found.")
    finishes = session.execute(
        select(
            OwnerCompetitionEntry.final_position,
            OwnerCompetition.name,
            OwnerCompetition.tier,
            OwnerCompetitionEntry.created_at,
        )
        .join(OwnerCompetition, OwnerCompetition.id == OwnerCompetitionEntry.competition_id)
        .where(
            OwnerCompetitionEntry.club_id == profile.id,
            OwnerCompetitionEntry.final_position.is_not(None),
            OwnerCompetitionEntry.final_position <= 3,
        )
    ).all()
    card = {
        "club_name": profile.club_name,
        "short_name": profile.short_name,
        "city": profile.city_name,
        "country_code": profile.country_code,
        "primary_color": profile.primary_color,
        "secondary_color": profile.secondary_color,
        "founded": profile.founded_at.year if profile.founded_at else None,
        "crest_url": profile.crest_asset_ref,
        "trophies": [
            {
                "competition": name,
                "tier": tier,
                "position": position,
                "year": created.year if created else None,
            }
            for position, name, tier, created in sorted(finishes, key=lambda row: (row[0], row[1]))
        ],
    }
    return {key: card[key] for key in PUBLIC_SHOWROOM_KEYS}
