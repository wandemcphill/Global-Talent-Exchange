from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Competition, Country, Season, TeamStanding


@dataclass(slots=True)
class CompetitionSnapshot:
    id: str
    name: str
    slug: str
    code: str | None
    country_name: str | None
    season_count: int
    club_count: int
    updated_at: object


@dataclass(slots=True)
class CompetitionQueryService:
    session: Session

    def get_competition(self, competition_id: str) -> CompetitionSnapshot | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        country_name = None
        if competition.country_id is not None:
            country = self.session.get(Country, competition.country_id)
            country_name = country.name if country is not None else None
        season_count = self.session.scalar(select(func.count(Season.id)).where(Season.competition_id == competition_id)) or 0
        club_count = self.session.scalar(
            select(func.count(distinct(TeamStanding.club_id))).where(TeamStanding.competition_id == competition_id)
        ) or 0
        return CompetitionSnapshot(
            id=competition.id,
            name=competition.name,
            slug=competition.slug,
            code=competition.code,
            country_name=country_name,
            season_count=int(season_count),
            club_count=int(club_count),
            updated_at=competition.updated_at,
        )
