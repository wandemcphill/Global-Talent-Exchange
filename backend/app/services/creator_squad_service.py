from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.core.config import Settings, get_settings
from backend.app.models.club_infra import ClubFacility
from backend.app.models.club_profile import ClubProfile
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorRegen, CreatorSquad
from backend.app.schemas.regen_core import RegenProfileView
from backend.app.services.regen_service import RegenClubContext, RegenGenerationEngine


class CreatorSquadError(ValueError):
    pass


class CreatorSquadLimitError(CreatorSquadError):
    pass


@dataclass(slots=True)
class CreatorSquadService:
    session: Session
    settings: Settings = field(default_factory=get_settings)
    engine: RegenGenerationEngine | None = None

    def __post_init__(self) -> None:
        if self.engine is None:
            self.engine = RegenGenerationEngine(self.settings)

    def create_starter_squad(
        self,
        *,
        creator_profile: CreatorProfile,
        club: ClubProfile,
        platform: str,
        follower_count: int,
    ) -> tuple[CreatorSquad, CreatorRegen]:
        existing = self.session.scalar(select(CreatorSquad).where(CreatorSquad.creator_profile_id == creator_profile.id))
        if existing is not None:
            creator_regen = self.session.scalar(
                select(CreatorRegen).where(CreatorRegen.creator_profile_id == creator_profile.id)
            )
            if creator_regen is None:
                raise CreatorSquadError("creator_regen_missing")
            return existing, creator_regen

        squad = CreatorSquad(
            club_id=club.id,
            creator_profile_id=creator_profile.id,
            metadata_json={
                "platform": platform,
                "follower_count": follower_count,
                "starter_roster_generated": True,
            },
        )
        self.session.add(squad)
        self.session.flush()

        club_context = self._club_context(club)
        first_team_bundle = self.engine.generate_starter_regens(
            club_id=club.id,
            season_label=self._season_label(),
            club_context=club_context,
            count=squad.first_team_limit,
            used_names=set(),
        )
        academy_bundle = self.engine.generate_academy_intake(
            club_id=club.id,
            season_label=self._season_label(),
            club_context=club_context,
            intake_size=squad.academy_limit,
            used_names={item.display_name for item in first_team_bundle.regens},
        )
        if not first_team_bundle.regens:
            raise CreatorSquadError("creator_starter_regens_missing")

        first_team = [
            self._regen_payload(item, squad_bucket="first_team", squad_slot=index, is_creator_regen=index == 1)
            for index, item in enumerate(first_team_bundle.regens, start=1)
        ]
        academy = [
            self._regen_payload(item, squad_bucket="academy", squad_slot=index, is_creator_regen=False)
            for index, item in enumerate(academy_bundle.regens, start=1)
        ]
        self._replace_rosters(squad, first_team=first_team, academy=academy)

        creator_regen_view = first_team_bundle.regens[0]
        creator_regen = CreatorRegen(
            creator_profile_id=creator_profile.id,
            club_id=club.id,
            display_name=creator_regen_view.display_name,
            primary_position=creator_regen_view.primary_position,
            secondary_positions_json=list(creator_regen_view.secondary_positions),
            current_gsi=creator_regen_view.current_gsi,
            potential_maximum=creator_regen_view.potential_range.maximum,
            squad_bucket="first_team",
            metadata_json={
                "regen_id": creator_regen_view.regen_id,
                "platform": platform,
                "follower_count": follower_count,
            },
        )
        self.session.add(creator_regen)
        self.session.flush()
        return squad, creator_regen

    def add_player_payload(self, *, squad: CreatorSquad, squad_bucket: str, payload: dict[str, object]) -> CreatorSquad:
        first_team = list(squad.first_team_json or [])
        academy = list(squad.academy_json or [])
        normalized_bucket = squad_bucket.strip().lower()
        if normalized_bucket == "first_team":
            first_team.append(payload)
        elif normalized_bucket == "academy":
            academy.append(payload)
        else:
            raise CreatorSquadError("creator_squad_bucket_invalid")
        self._replace_rosters(squad, first_team=first_team, academy=academy)
        return squad

    def _replace_rosters(
        self,
        squad: CreatorSquad,
        *,
        first_team: list[dict[str, object]],
        academy: list[dict[str, object]],
    ) -> None:
        if len(first_team) > squad.first_team_limit:
            raise CreatorSquadLimitError("creator_first_team_limit_exceeded")
        if len(academy) > squad.academy_limit:
            raise CreatorSquadLimitError("creator_academy_limit_exceeded")
        if len(first_team) + len(academy) > squad.total_limit:
            raise CreatorSquadLimitError("creator_total_roster_limit_exceeded")
        squad.first_team_json = first_team
        squad.academy_json = academy
        self.session.flush()

    def _club_context(self, club: ClubProfile) -> RegenClubContext:
        facilities = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club.id))
        reputation = self.session.scalar(
            select(ClubReputationProfile).where(ClubReputationProfile.club_id == club.id)
        )
        return RegenClubContext(
            country_code=club.country_code,
            region_name=club.region_name,
            city_name=club.city_name,
            training_level=float((facilities.training_level if facilities is not None else 2) * 18),
            academy_level=float((facilities.academy_level if facilities is not None else 2) * 18),
            academy_investment=float((facilities.academy_level if facilities is not None else 2) * 15),
            first_team_gsi=55.0,
            club_reputation=float(reputation.current_score if reputation is not None else 20),
            competition_quality=50.0,
            manager_youth_development=55.0,
            urbanicity="urban" if club.city_name else None,
        )

    @staticmethod
    def _regen_payload(
        item: RegenProfileView,
        *,
        squad_bucket: str,
        squad_slot: int,
        is_creator_regen: bool,
    ) -> dict[str, object]:
        return {
            "regen_id": item.regen_id,
            "player_name": item.display_name,
            "primary_position": item.primary_position,
            "secondary_positions": list(item.secondary_positions),
            "current_gsi": item.current_gsi,
            "potential_maximum": item.potential_range.maximum,
            "squad_bucket": squad_bucket,
            "squad_slot": squad_slot,
            "is_creator_regen": is_creator_regen,
            "non_tradable": True,
            "status": "creator_starter_squad",
        }

    @staticmethod
    def _season_label() -> str:
        from datetime import datetime, timezone

        current = datetime.now(timezone.utc)
        start_year = current.year if current.month >= 7 else current.year - 1
        return f"{start_year}/{start_year + 1}"


__all__ = ["CreatorSquadError", "CreatorSquadLimitError", "CreatorSquadService"]
