from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4

from backend.app.schemas.academy_core import AcademyProgramView, AcademyTrainingCycleView


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcademyTrainingService:
    def create_cycle(self, *, club_id: str, program: AcademyProgramView, cycle_index: int) -> AcademyTrainingCycleView:
        starts_at = _utcnow()
        return AcademyTrainingCycleView(
            id=f"acy-{uuid4().hex[:12]}",
            club_id=club_id,
            program_id=program.id,
            cycle_index=cycle_index,
            focus_attributes=program.focus_attributes,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(weeks=program.cycle_length_weeks),
            player_count=0,
            average_delta=0,
        )

    def refresh_cycle_player_count(self, *, cycle: AcademyTrainingCycleView, players_in_program: int) -> None:
        cycle.player_count = players_in_program

    def register_progress(self, *, cycle: AcademyTrainingCycleView, delta_overall: int) -> None:
        if cycle.player_count <= 1:
            cycle.average_delta = delta_overall
            return
        running_total = (cycle.average_delta * (cycle.player_count - 1)) + delta_overall
        cycle.average_delta = round(running_total / cycle.player_count)


@lru_cache
def get_academy_training_service() -> AcademyTrainingService:
    return AcademyTrainingService()


__all__ = ["AcademyTrainingService", "get_academy_training_service"]
