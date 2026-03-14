from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.national_team import (
    NationalTeamCompetition,
    NationalTeamEntry,
    NationalTeamManagerHistory,
    NationalTeamSquadMember,
)
from backend.app.models.user import User
from backend.app.story_feed_engine.service import StoryFeedService


class NationalTeamEngineError(ValueError):
    pass


@dataclass(slots=True)
class NationalTeamEngineService:
    session: Session

    def create_competition(self, *, payload, actor: User) -> NationalTeamCompetition:
        existing = self.session.scalar(select(NationalTeamCompetition).where(NationalTeamCompetition.key == payload.key.strip().lower()))
        if existing is not None:
            raise NationalTeamEngineError("National team competition key already exists.")
        competition = NationalTeamCompetition(
            key=payload.key.strip().lower(),
            title=payload.title.strip(),
            season_label=payload.season_label.strip(),
            region_type=payload.region_type.strip().lower(),
            age_band=payload.age_band.strip().lower(),
            format_type=payload.format_type.strip().lower(),
            status=payload.status.strip().lower(),
            notes=payload.notes.strip() if payload.notes else None,
            created_by_user_id=actor.id,
        )
        self.session.add(competition)
        self.session.flush()
        StoryFeedService(self.session).publish(
            story_type="national_team_launch",
            title=f"{competition.title} launched",
            body=f"{competition.title} ({competition.season_label}) is now available on GTEX.",
            subject_type="national_team_competition",
            subject_id=competition.id,
            metadata_json={"competition_key": competition.key, "age_band": competition.age_band},
            published_by_user_id=actor.id,
            featured=True,
        )
        return competition

    def list_competitions(self, *, active_only: bool = True, limit: int = 100) -> list[NationalTeamCompetition]:
        stmt = select(NationalTeamCompetition)
        if active_only:
            stmt = stmt.where(NationalTeamCompetition.active.is_(True))
        stmt = stmt.order_by(NationalTeamCompetition.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_competition(self, competition_id: str) -> NationalTeamCompetition | None:
        stmt = select(NationalTeamCompetition).where(NationalTeamCompetition.id == competition_id).options(selectinload(NationalTeamCompetition.entries))
        return self.session.scalar(stmt)

    def upsert_entry(self, *, competition_id: str, payload, actor: User) -> NationalTeamEntry:
        competition = self.session.get(NationalTeamCompetition, competition_id)
        if competition is None:
            raise NationalTeamEngineError("National team competition was not found.")
        country_code = payload.country_code.strip().upper()
        entry = self.session.scalar(
            select(NationalTeamEntry).where(
                NationalTeamEntry.competition_id == competition_id,
                NationalTeamEntry.country_code == country_code,
            )
        )
        is_new = entry is None
        if entry is None:
            entry = NationalTeamEntry(
                competition_id=competition_id,
                country_code=country_code,
                country_name=payload.country_name.strip(),
                manager_user_id=payload.manager_user_id,
                metadata_json=payload.metadata_json,
            )
            self.session.add(entry)
        else:
            entry.country_name = payload.country_name.strip()
            entry.manager_user_id = payload.manager_user_id
            entry.metadata_json = payload.metadata_json
        self.session.flush()
        if payload.manager_user_id:
            self.session.add(
                NationalTeamManagerHistory(
                    entry_id=entry.id,
                    user_id=payload.manager_user_id,
                    action_type="appointed" if is_new else "updated",
                    note=f"Manager assigned for {entry.country_name} in {competition.title}",
                )
            )
        self.session.flush()
        if is_new:
            StoryFeedService(self.session).publish(
                story_type="national_team_entry",
                title=f"{entry.country_name} joined {competition.title}",
                body=f"{entry.country_name} has been entered into {competition.title} for {competition.season_label}.",
                subject_type="national_team_entry",
                subject_id=entry.id,
                country_code=entry.country_code,
                metadata_json={"competition_key": competition.key, "country_code": entry.country_code},
                published_by_user_id=actor.id,
            )
        return entry

    def upsert_squad(self, *, entry_id: str, members: list, actor: User) -> NationalTeamEntry:
        entry = self.session.scalar(
            select(NationalTeamEntry)
            .where(NationalTeamEntry.id == entry_id)
            .options(
                selectinload(NationalTeamEntry.squad_members),
                selectinload(NationalTeamEntry.manager_history),
                selectinload(NationalTeamEntry.competition),
            )
        )
        if entry is None:
            raise NationalTeamEngineError("National team entry was not found.")
        existing_by_user = {item.user_id: item for item in entry.squad_members}
        retained_user_ids: set[str] = set()
        created_count = 0
        for member in members:
            user = self.session.get(User, member.user_id)
            if user is None or not user.is_active:
                raise NationalTeamEngineError(f"Squad member user '{member.user_id}' was not found.")
            retained_user_ids.add(member.user_id)
            record = existing_by_user.get(member.user_id)
            if record is None:
                created_count += 1
                record = NationalTeamSquadMember(
                    entry_id=entry.id,
                    user_id=member.user_id,
                    player_name=member.player_name.strip(),
                    shirt_number=member.shirt_number,
                    role_label=member.role_label,
                    status=member.status.strip().lower(),
                )
                self.session.add(record)
            else:
                record.player_name = member.player_name.strip()
                record.shirt_number = member.shirt_number
                record.role_label = member.role_label
                record.status = member.status.strip().lower()
        for record in list(entry.squad_members):
            if record.user_id not in retained_user_ids:
                self.session.delete(record)
        self.session.flush()
        refreshed = self.session.scalar(
            select(NationalTeamEntry)
            .where(NationalTeamEntry.id == entry.id)
            .options(selectinload(NationalTeamEntry.squad_members), selectinload(NationalTeamEntry.manager_history))
        )
        assert refreshed is not None
        refreshed.squad_size = len(refreshed.squad_members)
        self.session.flush()
        if created_count:
            StoryFeedService(self.session).publish(
                story_type="national_team_callup",
                title=f"{created_count} new call-up(s) for {refreshed.country_name}",
                body=f"{refreshed.country_name} updated its squad for {entry.competition.title}.",
                subject_type="national_team_entry",
                subject_id=refreshed.id,
                country_code=refreshed.country_code,
                metadata_json={"squad_size": refreshed.squad_size},
                published_by_user_id=actor.id,
            )
        return refreshed

    def get_entry_detail(self, entry_id: str) -> NationalTeamEntry | None:
        return self.session.scalar(
            select(NationalTeamEntry)
            .where(NationalTeamEntry.id == entry_id)
            .options(selectinload(NationalTeamEntry.squad_members), selectinload(NationalTeamEntry.manager_history))
        )

    def user_history(self, *, user: User) -> dict[str, list]:
        managed_entries = list(self.session.scalars(select(NationalTeamEntry).where(NationalTeamEntry.manager_user_id == user.id).order_by(NationalTeamEntry.updated_at.desc())).all())
        squad_memberships = list(self.session.scalars(select(NationalTeamSquadMember).where(NationalTeamSquadMember.user_id == user.id).order_by(NationalTeamSquadMember.updated_at.desc())).all())
        return {"managed_entries": managed_entries, "squad_memberships": squad_memberships}
