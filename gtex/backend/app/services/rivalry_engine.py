from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RivalryMemory:
    player_id: str
    hated_club: str
    intensity: float
    memory_type: str = "betrayal"

    def as_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "hated_club": self.hated_club,
            "intensity": max(0.0, min(float(self.intensity), 1.0)),
            "memory_type": self.memory_type,
        }


def rivalry_story(player: str, old_club: str, new_club: str) -> dict[str, Any]:
    return {
        "headline": f"{player} set to face former club {old_club}",
        "body": f"Tensions rising ahead of a dramatic reunion with {new_club}.",
        "type": "rivalry",
        "priority": 5,
        "club": new_club,
        "player_name": player,
        "metadata": {
            "rivalry_type": "player_vs_former_club",
            "old_club": old_club,
            "new_club": new_club,
        },
    }


def player_betrayal_memory(player_id: str, hated_club: str, *, intensity: float = 0.75) -> dict[str, Any]:
    return RivalryMemory(
        player_id=player_id,
        hated_club=hated_club,
        intensity=intensity,
        memory_type="player_betrayal",
    ).as_dict()


def revenge_match_story(player: str, club: str, hated_club: str, *, intensity: float = 0.75) -> dict[str, Any]:
    priority = 6 + int(intensity >= 0.8)
    return {
        "headline": f"{player} revenge angle dominates {club} vs {hated_club}",
        "body": "The media tone is sharper than normal, with crowd hostility expected from the first whistle.",
        "type": "rivalry",
        "priority": priority,
        "club": club,
        "player_name": player,
        "metadata": {
            "rivalry_type": "revenge_match",
            "hated_club": hated_club,
            "intensity": max(0.0, min(float(intensity), 1.0)),
            "crowd_hostility": "high" if intensity >= 0.8 else "medium",
        },
    }


def crowd_hostility_story(club: str, hated_club: str, *, intensity: float = 0.75) -> dict[str, Any]:
    return {
        "headline": f"Crowd hostility rising before {club} meet {hated_club}",
        "body": "Security, managers and players all know this fixture carries extra noise.",
        "type": "rivalry",
        "priority": 5 + int(intensity >= 0.8),
        "club": club,
        "player_name": None,
        "metadata": {
            "rivalry_type": "crowd_hostility",
            "hated_club": hated_club,
            "intensity": max(0.0, min(float(intensity), 1.0)),
        },
    }


def club_rivalry_story(left_club: str, right_club: str, *, stakes: str | None = None) -> dict[str, Any]:
    resolved_stakes = stakes or "local bragging rights"
    return {
        "headline": f"{left_club} and {right_club} rivalry heats up",
        "body": f"The next meeting carries {resolved_stakes}, and both fanbases are already talking.",
        "type": "rivalry",
        "priority": 4,
        "club": left_club,
        "player_name": None,
        "metadata": {
            "rivalry_type": "club_vs_club",
            "left_club": left_club,
            "right_club": right_club,
            "stakes": resolved_stakes,
        },
    }


def manager_grudge_story(manager: str, club: str, *, rival_manager: str | None = None) -> dict[str, Any]:
    rival = rival_manager or "the opposing bench"
    return {
        "headline": f"{manager} brings edge to {club}",
        "body": f"The tactical room is watching {manager}'s old grudge with {rival} before kickoff.",
        "type": "manager",
        "priority": 4,
        "club": club,
        "player_name": None,
        "metadata": {
            "rivalry_type": "manager_grudge",
            "manager": manager,
            "club": club,
            "rival_manager": rival_manager,
        },
    }


__all__ = [
    "RivalryMemory",
    "club_rivalry_story",
    "crowd_hostility_story",
    "manager_grudge_story",
    "player_betrayal_memory",
    "revenge_match_story",
    "rivalry_story",
]
