from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.common.schemas.competition import (
    CompetitionDispatchRequest,
    CompetitionEngineBatch,
    CompetitionScheduleRequest,
    ScheduledFixture,
)
from backend.app.competition_engine.match_dispatcher import MatchDispatcher, scale_strength_rating
from backend.app.competition_engine.scheduler import CompetitionScheduler, CompetitionWindowResolver
from backend.app.world_super_cup.models import GroupMatch, KnockoutMatch, PlayoffMatch, TournamentPlan


@dataclass(slots=True)
class WorldSuperCupCompetitionEngineService:
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)
    dispatcher: MatchDispatcher = field(default_factory=MatchDispatcher)

    def build_batch(
        self,
        plan: TournamentPlan,
        *,
        competition_id: str = "world-super-cup",
        season_id: str | None = None,
    ) -> CompetitionEngineBatch:
        matches = self._flatten_matches(plan)
        coefficients = [
            club.coefficient_points
            for match in matches
            for club in (match.home_club, match.away_club)
        ]
        minimum_rating = min(coefficients)
        maximum_rating = max(coefficients)
        unique_dates = tuple(sorted({match.kickoff_at.date() for match in matches}))
        schedule_plan = self.scheduler.build_schedule(
            (
                CompetitionScheduleRequest(
                    competition_id=competition_id,
                    competition_type=CompetitionType.WORLD_SUPER_CUP,
                    requested_dates=unique_dates,
                    required_windows=len(CompetitionType.WORLD_SUPER_CUP.default_fixture_windows),
                    priority=0,
                    requires_exclusive_windows=True,
                ),
            )
        )
        resolver = CompetitionWindowResolver.from_plan(schedule_plan, competition_id=competition_id)
        matches_by_date: dict = {}
        for match in matches:
            matches_by_date.setdefault(match.kickoff_at.date(), []).append(match)

        scheduled: list[ScheduledFixture] = []
        dispatch_requests: list[CompetitionDispatchRequest] = []
        for match_date in unique_dates:
            day_matches = sorted(
                matches_by_date[match_date],
                key=lambda item: (item.kickoff_at, item.match_id),
            )
            for index, match in enumerate(day_matches):
                window, slot_sequence = resolver.slot_for(match_date, index)
                fixture = ScheduledFixture(
                    fixture_id=match.match_id,
                    competition_id=competition_id,
                    competition_type=CompetitionType.WORLD_SUPER_CUP,
                    round_number=index + 1,
                    home_club_id=match.home_club.club_id,
                    away_club_id=match.away_club.club_id,
                    match_date=match_date,
                    window=window,
                    slot_sequence=slot_sequence,
                    stage_name=self._stage_name(match),
                    replay_visibility=ReplayVisibility.COMPETITION,
                    is_cup_match=self._is_cup_match(match),
                    allow_penalties=self._allow_penalties(match),
                )
                scheduled.append(fixture)
                dispatch_requests.append(
                    CompetitionDispatchRequest(
                        fixture=fixture,
                        season_id=season_id,
                        competition_name=plan.countdown.tournament_name,
                        stage_name=self._stage_name(match),
                        scheduled_kickoff_at=match.kickoff_at,
                        home_club_name=match.home_club.club_name,
                        away_club_name=match.away_club.club_name,
                        home_strength_rating=scale_strength_rating(
                            match.home_club.coefficient_points,
                            minimum=minimum_rating,
                            maximum=maximum_rating,
                        ),
                        away_strength_rating=scale_strength_rating(
                            match.away_club.coefficient_points,
                            minimum=minimum_rating,
                            maximum=maximum_rating,
                        ),
                        is_final=self._stage_name(match) == "final",
                    )
                )

        return CompetitionEngineBatch(
            competition_id=competition_id,
            competition_type=CompetitionType.WORLD_SUPER_CUP,
            schedule_plan=schedule_plan,
            fixtures=tuple(scheduled),
            dispatch_requests=tuple(dispatch_requests),
        )

    def dispatch_plan(
        self,
        plan: TournamentPlan,
        *,
        competition_id: str = "world-super-cup",
        season_id: str | None = None,
    ):
        batch = self.build_batch(plan, competition_id=competition_id, season_id=season_id)
        return self.dispatcher.dispatch_batch(batch)

    def _flatten_matches(
        self,
        plan: TournamentPlan,
    ) -> tuple[PlayoffMatch | GroupMatch | KnockoutMatch, ...]:
        knockout_matches = tuple(
            match
            for round_entry in plan.knockout.rounds
            for match in round_entry.matches
        )
        return (
            *plan.qualification.playoff_matches,
            *plan.group_stage.matches,
            *knockout_matches,
        )

    def _stage_name(self, match: PlayoffMatch | GroupMatch | KnockoutMatch) -> str:
        if isinstance(match, GroupMatch):
            return f"group_{match.group_name.lower()}_matchday_{match.matchday}"
        if isinstance(match, PlayoffMatch):
            return match.stage
        return match.round_name

    def _is_cup_match(self, match: PlayoffMatch | GroupMatch | KnockoutMatch) -> bool:
        return not isinstance(match, GroupMatch)

    def _allow_penalties(self, match: PlayoffMatch | GroupMatch | KnockoutMatch) -> bool:
        return not isinstance(match, GroupMatch)
