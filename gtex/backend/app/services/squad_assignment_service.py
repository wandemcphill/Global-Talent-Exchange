from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True, slots=True)
class SquadAssignmentProfile:
    primary_position: str | None
    secondary_positions: tuple[str, ...]
    formation_slots: tuple[str, ...]
    role_archetype: str
    squad_eligibility: dict[str, bool]
    formation_ready: bool


class SquadAssignmentService:
    _ARCHETYPE_OPTIONS: dict[str, tuple[str, ...]] = {
        "Goalkeeper": ("shot_stopper", "sweeper_keeper"),
        "Centre-Back": ("ball_playing_centre_back", "stopper", "cover_defender"),
        "Full-Back": ("overlapping_full_back", "inverted_full_back", "wing_back"),
        "Defensive Midfielder": ("anchor", "screening_midfielder", "deep_lying_playmaker"),
        "Central Midfielder": ("box_to_box_midfielder", "controller", "ball_winner"),
        "Attacking Midfielder": ("advanced_playmaker", "chance_creator", "shadow_runner"),
        "Winger": ("inverted_winger", "touchline_winger", "inside_forward"),
        "Striker": ("poacher", "pressing_forward", "target_forward"),
    }

    def build_profile(
        self,
        *,
        player_id: str,
        primary_position: str | None,
        normalized_position: str | None,
        preferred_foot: str | None,
        age: int,
        current_club_id: str | None,
    ) -> SquadAssignmentProfile:
        resolved_position = primary_position or normalized_position or "Central Midfielder"
        secondary_positions = self._secondary_positions(
            player_id=player_id,
            primary_position=resolved_position,
            preferred_foot=preferred_foot,
        )
        formation_slots = self._formation_slots(
            primary_position=resolved_position,
            preferred_foot=preferred_foot,
            secondary_positions=secondary_positions,
        )
        role_archetype = self._role_archetype(player_id=player_id, primary_position=resolved_position)
        is_free_agent = current_club_id is None
        squad_eligibility = {
            "first_team": not is_free_agent,
            "reserve_team": not is_free_agent and age <= 23,
            "academy_team": not is_free_agent and age <= 19,
            "transfer_market": True,
            "free_agent_pool": is_free_agent,
        }
        return SquadAssignmentProfile(
            primary_position=resolved_position,
            secondary_positions=secondary_positions,
            formation_slots=formation_slots,
            role_archetype=role_archetype,
            squad_eligibility=squad_eligibility,
            formation_ready=bool(formation_slots),
        )

    def _secondary_positions(
        self,
        *,
        player_id: str,
        primary_position: str,
        preferred_foot: str | None,
    ) -> tuple[str, ...]:
        candidates: tuple[str, ...]
        if primary_position == "Goalkeeper":
            candidates = ()
        elif primary_position == "Centre-Back":
            candidates = ("Full-Back", "Defensive Midfielder")
        elif primary_position == "Full-Back":
            candidates = ("Centre-Back", "Winger")
        elif primary_position == "Defensive Midfielder":
            candidates = ("Central Midfielder", "Centre-Back")
        elif primary_position == "Central Midfielder":
            candidates = ("Defensive Midfielder", "Attacking Midfielder")
        elif primary_position == "Attacking Midfielder":
            candidates = ("Central Midfielder", "Winger")
        elif primary_position == "Winger":
            candidates = ("Striker", "Attacking Midfielder")
        else:
            candidates = ("Winger", "Attacking Midfielder")

        if not candidates:
            return ()

        digest = self._digest(player_id, primary_position, preferred_foot or "unknown")
        if digest % 7 == 0:
            return ()
        if digest % 3 == 0:
            return candidates[:1]
        return candidates[:2]

    def _formation_slots(
        self,
        *,
        primary_position: str,
        preferred_foot: str | None,
        secondary_positions: tuple[str, ...],
    ) -> tuple[str, ...]:
        slots: list[str] = []
        foot = (preferred_foot or "").lower()
        if primary_position == "Goalkeeper":
            slots.extend(("GK",))
        elif primary_position == "Centre-Back":
            slots.extend(("CB", "LCB", "RCB"))
        elif primary_position == "Full-Back":
            if foot == "left":
                slots.extend(("LB", "LWB"))
            elif foot == "right":
                slots.extend(("RB", "RWB"))
            else:
                slots.extend(("LB", "RB", "LWB", "RWB"))
        elif primary_position == "Defensive Midfielder":
            slots.extend(("DM", "CM"))
        elif primary_position == "Central Midfielder":
            slots.extend(("CM", "DM", "AM"))
        elif primary_position == "Attacking Midfielder":
            slots.extend(("AM", "CM"))
            slots.append("LW" if foot == "left" else "RW" if foot == "right" else "AM")
        elif primary_position == "Winger":
            slots.extend(("LW", "RW"))
            slots.append("ST" if foot == "both" else "AM")
        elif primary_position == "Striker":
            slots.extend(("ST", "CF"))
            slots.append("RW" if foot == "left" else "LW" if foot == "right" else "ST")

        for secondary_position in secondary_positions:
            if secondary_position == "Defensive Midfielder":
                slots.append("DM")
            elif secondary_position == "Central Midfielder":
                slots.append("CM")
            elif secondary_position == "Attacking Midfielder":
                slots.append("AM")
            elif secondary_position == "Winger":
                slots.extend(("LW", "RW"))
            elif secondary_position == "Striker":
                slots.append("ST")
            elif secondary_position == "Full-Back":
                slots.extend(("LB", "RB"))
            elif secondary_position == "Centre-Back":
                slots.append("CB")

        deduped_slots: list[str] = []
        for slot in slots:
            if slot not in deduped_slots:
                deduped_slots.append(slot)
        return tuple(deduped_slots)

    def _role_archetype(self, *, player_id: str, primary_position: str) -> str:
        options = self._ARCHETYPE_OPTIONS.get(primary_position, ("balanced",))
        index = self._digest(player_id, primary_position) % len(options)
        return options[index]

    @staticmethod
    def _digest(*parts: str) -> int:
        joined = "|".join(parts).encode("utf-8")
        return int(hashlib.sha256(joined).hexdigest()[:12], 16)


__all__ = ["SquadAssignmentProfile", "SquadAssignmentService"]
