from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import Player
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.regen import RegenAward, RegenLegacyRecord, RegenProfile
from backend.app.services.club_hall_of_fame_service import ClubHallOfFameService


LEGEND_SCORE_THRESHOLD = 120.0


@dataclass(slots=True)
class RegenLegacyService:
    session: Session

    def snapshot_legacy(
        self,
        regen_id: str,
        *,
        club_id: str | None = None,
        retired_on: date | None = None,
    ) -> RegenLegacyRecord:
        regen = self.session.get(RegenProfile, regen_id)
        if regen is None:
            raise ValueError("regen_not_found")
        player = self.session.get(Player, regen.player_id)
        if player is None:
            raise ValueError("player_not_found")

        career_entries = list(
            self.session.scalars(
                select(PlayerCareerEntry).where(PlayerCareerEntry.player_id == regen.player_id)
            )
        )
        appearances_total = sum(entry.appearances for entry in career_entries)
        goals_total = sum(entry.goals for entry in career_entries)
        assists_total = sum(entry.assists for entry in career_entries)
        seasons_total = len({entry.season_label for entry in career_entries if entry.season_label})
        awards_total = int(
            self.session.scalar(
                select(func.count(RegenAward.id)).where(RegenAward.regen_id == regen.id)
            )
            or 0
        )
        legacy_score = round(
            (appearances_total * 0.35)
            + (goals_total * 0.8)
            + (assists_total * 0.5)
            + (awards_total * 6)
            + (seasons_total * 2),
            2,
        )
        is_legend = legacy_score >= LEGEND_SCORE_THRESHOLD
        tier = "legend" if is_legend else "standard"

        record = self.session.scalar(
            select(RegenLegacyRecord).where(RegenLegacyRecord.regen_id == regen.id)
        )
        if record is None:
            record = RegenLegacyRecord(
                regen_id=regen.id,
                player_id=regen.player_id,
                club_id=club_id,
            )
            self.session.add(record)

        record.club_id = club_id or record.club_id
        record.retired_on = retired_on or record.retired_on
        record.appearances_total = appearances_total
        record.goals_total = goals_total
        record.assists_total = assists_total
        record.awards_total = awards_total
        record.seasons_total = seasons_total
        record.legacy_score = legacy_score
        record.legacy_tier = tier
        record.is_legend = is_legend
        record.narrative_summary = (
            record.narrative_summary
            or ("Club legend who shaped a generation." if is_legend else "Respected club contributor.")
        )
        record.metadata_json = {
            "player_name": player.full_name,
            "last_club_id": club_id,
            "career_entries": len(career_entries),
        }
        self.session.flush()

        if is_legend and club_id is not None:
            ClubHallOfFameService(self.session).auto_induct_regen(regen_id=regen.id, club_id=club_id, legacy=record)
        return record


__all__ = ["RegenLegacyService", "LEGEND_SCORE_THRESHOLD"]
