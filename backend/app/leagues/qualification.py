from __future__ import annotations

from dataclasses import replace

from app.leagues.models import LeagueAutoEntrySlot, LeagueStandingRow


class LeagueQualificationService:
    def build_auto_entry_slots(
        self,
        standings: tuple[LeagueStandingRow, ...],
        *,
        opted_out_club_ids: set[str],
    ) -> tuple[LeagueAutoEntrySlot, ...]:
        slot_target = min(4, len(standings))
        slots: list[LeagueAutoEntrySlot] = []
        for row in standings:
            if row.club_id in opted_out_club_ids:
                continue
            slot_number = len(slots) + 1
            slots.append(
                LeagueAutoEntrySlot(
                    slot_number=slot_number,
                    club_id=row.club_id,
                    club_name=row.club_name,
                    final_position=row.position,
                    rolled_over=row.position > slot_number,
                )
            )
            if len(slots) == slot_target:
                break
        return tuple(slots)

    def apply_markers(
        self,
        standings: tuple[LeagueStandingRow, ...],
        *,
        opted_out_club_ids: set[str],
    ) -> tuple[LeagueStandingRow, ...]:
        direct_slots = min(2, len(standings))
        playoff_slots = min(2, max(0, len(standings) - direct_slots))
        auto_entry_ids = {
            slot.club_id
            for slot in self.build_auto_entry_slots(
                standings,
                opted_out_club_ids=opted_out_club_ids,
            )
        }

        enriched: list[LeagueStandingRow] = []
        for row in standings:
            is_direct = row.position <= direct_slots
            is_playoff = direct_slots < row.position <= direct_slots + playoff_slots
            is_auto_entry = row.club_id in auto_entry_ids
            enriched.append(
                replace(
                    row,
                    direct_champions_league=is_direct,
                    champions_league_playoff=is_playoff,
                    next_season_auto_entry=is_auto_entry,
                    table_color="blue" if is_direct else "yellow" if is_playoff else "grey",
                    auto_entry_color="green" if is_auto_entry else None,
                )
            )
        return tuple(enriched)


__all__ = ["LeagueQualificationService"]
