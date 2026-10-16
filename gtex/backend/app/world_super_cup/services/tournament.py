from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.world_super_cup.models import TournamentPlan
from app.world_super_cup.services.calendar import WorldSuperCupCalendarService
from app.world_super_cup.services.ceremony import TrophyCeremonyService
from app.world_super_cup.services.group_stage import GroupStageService
from app.world_super_cup.services.knockout import KnockoutService
from app.world_super_cup.services.qualification import WorldSuperCupQualificationService
from app.world_super_cup.services.sample_data import build_demo_season_results


@dataclass(slots=True)
class WorldSuperCupService:
    qualification_service: WorldSuperCupQualificationService = field(default_factory=WorldSuperCupQualificationService)
    group_stage_service: GroupStageService = field(default_factory=GroupStageService)
    knockout_service: KnockoutService = field(default_factory=KnockoutService)
    calendar_service: WorldSuperCupCalendarService = field(default_factory=WorldSuperCupCalendarService)
    ceremony_service: TrophyCeremonyService = field(default_factory=TrophyCeremonyService)

    def build_demo_tournament(self, reference_at: datetime | None = None) -> TournamentPlan:
        tournament_start = self.calendar_service.tournament_start(reference_at)
        qualification = self.qualification_service.build_plan(
            build_demo_season_results(),
            tournament_start,
        )
        group_stage = self.group_stage_service.build_snapshot(
            qualification.main_event_clubs,
            tournament_start,
        )
        ceremony = self.ceremony_service.build_metadata()
        knockout = self.knockout_service.build_bracket(
            group_stage.tables,
            tournament_start,
            ceremony,
        )
        countdown = self.calendar_service.build_countdown(
            tournament_start,
            reference_at,
        )
        return TournamentPlan(
            qualification=qualification,
            group_stage=group_stage,
            knockout=knockout,
            countdown=countdown,
        )
