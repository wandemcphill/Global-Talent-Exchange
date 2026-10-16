from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.competition_status import CompetitionStatus
from app.models.base import utcnow
from app.models.competition import Competition
from app.models.competition_participant import CompetitionParticipant


class CompetitionLockError(ValueError):
    def __init__(
        self,
        detail: str,
        *,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.competition_id = competition_id
        self.club_id = club_id


@dataclass(slots=True)
class CompetitionLockService:
    session: Session

    def activate_live_lock(self, competition: Competition) -> None:
        metadata = dict(competition.metadata_json or {})
        existing = dict(metadata.get("tournament_lock") or {})
        activated_at = competition.launched_at or utcnow()
        metadata["tournament_lock"] = {
            **existing,
            "active": True,
            "reason": "competition_live",
            "competition_id": competition.id,
            "transfers_disabled": True,
            "rentals_disabled": True,
            "activated_at": activated_at.isoformat(),
            "released_at": None,
        }
        competition.metadata_json = metadata

    def release_live_lock(self, competition: Competition) -> None:
        metadata = dict(competition.metadata_json or {})
        existing = dict(metadata.get("tournament_lock") or {})
        if not existing and competition.status == CompetitionStatus.LIVE.value:
            return
        metadata["tournament_lock"] = {
            **existing,
            "active": False,
            "reason": "competition_not_live",
            "competition_id": competition.id,
            "transfers_disabled": False,
            "rentals_disabled": False,
            "released_at": utcnow().isoformat(),
        }
        competition.metadata_json = metadata

    def ensure_transfers_allowed(self, *, club_id: str) -> None:
        competition = self._live_competition_for_club(club_id)
        if competition is None:
            return
        raise CompetitionLockError(
            "Transfers are locked while the club is participating in a live competition.",
            competition_id=competition.id,
            club_id=club_id,
        )

    def ensure_rentals_allowed(self, *, competition_id: str) -> None:
        competition = self.session.get(Competition, competition_id)
        if competition is None or competition.status != CompetitionStatus.LIVE.value:
            return
        raise CompetitionLockError(
            "Rentals are locked while the competition is live.",
            competition_id=competition.id,
        )

    def _live_competition_for_club(self, club_id: str) -> Competition | None:
        return self.session.scalar(
            select(Competition)
            .join(
                CompetitionParticipant,
                CompetitionParticipant.competition_id == Competition.id,
            )
            .where(
                Competition.status == CompetitionStatus.LIVE.value,
                CompetitionParticipant.club_id == club_id,
            )
            .order_by(Competition.launched_at.desc(), Competition.created_at.desc())
        )


__all__ = ["CompetitionLockError", "CompetitionLockService"]
