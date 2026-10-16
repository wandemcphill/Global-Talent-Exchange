from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Club, Country, Player


@dataclass(slots=True)
class ClubSnapshot:
    id: str
    name: str
    slug: str
    short_name: str | None
    country_name: str | None
    player_count: int
    updated_at: object


@dataclass(slots=True)
class ClubQueryService:
    session: Session

    def get_club(self, club_id: str) -> ClubSnapshot | None:
        club = self.session.get(Club, club_id)
        if club is None:
            return None
        country_name = None
        if club.country_id is not None:
            country = self.session.get(Country, club.country_id)
            country_name = country.name if country is not None else None
        player_count = self.session.scalar(
            select(func.count(Player.id)).where(Player.current_club_id == club_id)
        ) or 0
        return ClubSnapshot(
            id=club.id,
            name=club.name,
            slug=club.slug,
            short_name=club.short_name,
            country_name=country_name,
            player_count=int(player_count),
            updated_at=club.updated_at,
        )
