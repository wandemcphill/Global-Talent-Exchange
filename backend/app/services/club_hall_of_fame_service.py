from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import Player
from backend.app.models.club_hall_of_fame import ClubHallOfFameEntry
from backend.app.models.regen import RegenLegacyRecord, RegenProfile


@dataclass(slots=True)
class ClubHallOfFameService:
    session: Session

    def add_entry(
        self,
        *,
        club_id: str,
        entry_category: str,
        player_id: str | None = None,
        regen_id: str | None = None,
        entry_label: str | None = None,
        entry_rank: int | None = None,
        stat_line: dict[str, object] | None = None,
        era_label: str | None = None,
        narrative_summary: str | None = None,
        source_scope: str = "manual",
        metadata: dict[str, object] | None = None,
    ) -> ClubHallOfFameEntry:
        if player_id is None and regen_id is None:
            raise ValueError("hall_of_fame_requires_player_or_regen")
        label = entry_label
        if label is None and player_id is not None:
            player = self.session.get(Player, player_id)
            label = player.full_name if player is not None else "Unknown Player"
        if label is None and regen_id is not None:
            regen = self.session.get(RegenProfile, regen_id)
            label = regen.regen_id if regen is not None else "Unknown Regen"
        entry = ClubHallOfFameEntry(
            club_id=club_id,
            entry_category=entry_category,
            player_id=player_id,
            regen_id=regen_id,
            entry_label=label or "Unknown",
            entry_rank=entry_rank,
            stat_line_json=stat_line or {},
            era_label=era_label,
            narrative_summary=narrative_summary,
            source_scope=source_scope,
            metadata_json=metadata or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def auto_induct_regen(
        self,
        *,
        regen_id: str,
        club_id: str | None,
        legacy: RegenLegacyRecord,
        category: str | None = None,
    ) -> ClubHallOfFameEntry:
        if club_id is None:
            raise ValueError("hall_of_fame_requires_club")
        resolved_category = category or ("Legends" if legacy.is_legend else "Favorites")
        stat_line = {
            "appearances": legacy.appearances_total,
            "goals": legacy.goals_total,
            "assists": legacy.assists_total,
            "awards": legacy.awards_total,
        }
        narrative = legacy.narrative_summary or (
            "Club legend etched into the hall of fame." if legacy.is_legend else "Beloved figure in club memory."
        )
        return self.add_entry(
            club_id=club_id,
            entry_category=resolved_category,
            regen_id=regen_id,
            entry_label=None,
            stat_line=stat_line,
            era_label=legacy.metadata_json.get("era_label") if legacy.metadata_json else None,
            narrative_summary=narrative,
            source_scope="legacy_service",
            metadata={"legacy_score": legacy.legacy_score, "legacy_tier": legacy.legacy_tier},
        )


__all__ = ["ClubHallOfFameService"]
