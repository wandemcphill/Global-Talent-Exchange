from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.trophy_type import TrophyType
from app.models.club_profile import ClubProfile
from app.models.club_trophy import ClubTrophy
from app.models.club_trophy_cabinet import ClubTrophyCabinet
from app.schemas.club_trophy_core import ClubTrophyCabinetCore, ClubTrophyCore
from app.services.club_dynasty_service import ClubDynastyService
from app.services.club_reputation_event_service import ClubReputationEventService

_PRESTIGE_WEIGHT_BY_TROPHY_TYPE: dict[TrophyType, int] = {
    TrophyType.LEAGUE_TITLE: 140,
    TrophyType.CUP_TITLE: 110,
    TrophyType.CREATOR_CUP: 100,
    TrophyType.INVITATIONAL_TITLE: 90,
    TrophyType.COMMUNITY_AWARD: 60,
    TrophyType.FAIR_PLAY_AWARD: 70,
    TrophyType.DYNASTY_AWARD: 130,
}


@dataclass(slots=True)
class ClubTrophyService:
    session: Session

    def ensure_cabinet(self, club_id: str) -> ClubTrophyCabinet:
        self._require_club(club_id)
        cabinet = self.session.scalar(
            select(ClubTrophyCabinet).where(ClubTrophyCabinet.club_id == club_id)
        )
        if cabinet is not None:
            return cabinet
        cabinet = ClubTrophyCabinet(club_id=club_id)
        self.session.add(cabinet)
        self.session.flush()
        return cabinet

    def award_trophy(
        self,
        *,
        club_id: str,
        trophy_type: TrophyType,
        trophy_name: str,
        competition_source: str,
        season_label: str,
        competition_id: str | None = None,
        campaign_label: str | None = None,
        awarded_at: datetime | None = None,
        featured: bool = False,
        metadata_json: dict[str, object] | None = None,
    ) -> ClubTrophy:
        cabinet = self.ensure_cabinet(club_id)
        trophy = ClubTrophy(
            club_id=club_id,
            trophy_type=trophy_type.value,
            trophy_name=trophy_name,
            competition_source=competition_source,
            competition_id=competition_id,
            season_label=season_label,
            campaign_label=campaign_label,
            prestige_weight=_PRESTIGE_WEIGHT_BY_TROPHY_TYPE[trophy_type],
            awarded_at=awarded_at or datetime.now(timezone.utc),
            is_featured=featured,
            display_order=len(cabinet.showcase_order_json),
            metadata_json=metadata_json or {},
        )
        self.session.add(trophy)
        self.session.flush()

        cabinet.total_trophies += 1
        cabinet.last_awarded_at = trophy.awarded_at
        cabinet.showcase_order_json = [trophy.id, *cabinet.showcase_order_json]
        if featured or cabinet.featured_trophy_id is None:
            cabinet.featured_trophy_id = trophy.id
            trophy.is_featured = True

        ClubReputationEventService(self.session).record_achievement(
            club_id=club_id,
            achievement_key="trophy_prestige",
            source="trophy_award",
            quantity=trophy.prestige_weight,
            summary=f"{trophy_name} added to trophy cabinet",
            payload={"trophy_type": trophy_type.value, "competition_source": competition_source},
            auto_commit=False,
        )
        ClubDynastyService(self.session).record_trophy(
            club_id=club_id,
            prestige_weight=trophy.prestige_weight,
            auto_commit=False,
        )
        self.session.commit()
        self.session.refresh(trophy)
        return trophy

    def list_trophies(self, club_id: str) -> list[ClubTrophyCore]:
        self._require_club(club_id)
        trophies = self.session.scalars(
            select(ClubTrophy)
            .where(ClubTrophy.club_id == club_id)
            .order_by(ClubTrophy.awarded_at.desc(), ClubTrophy.created_at.desc())
        ).all()
        return [ClubTrophyCore.model_validate(item) for item in trophies]

    def get_trophy_cabinet(self, club_id: str) -> tuple[ClubTrophyCabinetCore, list[ClubTrophyCore]]:
        cabinet = self.ensure_cabinet(club_id)
        return ClubTrophyCabinetCore.model_validate(cabinet), self.list_trophies(club_id)

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        return club
