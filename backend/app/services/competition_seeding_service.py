from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable

from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_seed_rule import CompetitionSeedRule


@dataclass(slots=True)
class CompetitionSeedingService:
    def seed_participants(
        self,
        *,
        participants: Iterable[CompetitionParticipant],
        seed_rule: CompetitionSeedRule,
        manual_seed_order: Iterable[str] | None = None,
        seed_token: str | None = None,
    ) -> list[CompetitionParticipant]:
        participants_list = list(participants)
        if not participants_list:
            return []

        manual = tuple(manual_seed_order or ())
        if manual and seed_rule.allow_admin_override:
            ordered = self._manual_order(participants_list, manual)
        elif seed_rule.seed_method == "ranking":
            ordered = sorted(
                participants_list,
                key=lambda item: (
                    -(item.points or 0),
                    -(item.goal_diff or 0),
                    -(item.goals_for or 0),
                    item.club_id,
                ),
            )
        else:
            ordered = list(participants_list)
            rng = random.Random(seed_token or "competition_seed")
            rng.shuffle(ordered)

        for index, participant in enumerate(ordered, start=1):
            if participant.seed_locked:
                continue
            participant.seed = index
            if seed_rule.lock_after_seed:
                participant.seed_locked = True

        return ordered

    def _manual_order(
        self,
        participants: list[CompetitionParticipant],
        manual_order: tuple[str, ...],
    ) -> list[CompetitionParticipant]:
        by_club = {participant.club_id: participant for participant in participants}
        ordered: list[CompetitionParticipant] = []
        seen: set[str] = set()
        for club_id in manual_order:
            participant = by_club.get(club_id)
            if participant is None:
                continue
            ordered.append(participant)
            seen.add(club_id)
        for participant in participants:
            if participant.club_id not in seen:
                ordered.append(participant)
        return ordered


__all__ = ["CompetitionSeedingService"]
