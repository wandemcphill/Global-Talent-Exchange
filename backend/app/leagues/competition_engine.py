from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.common.enums.competition_type import CompetitionType
from app.common.enums.replay_visibility import ReplayVisibility
from app.common.schemas.competition import (
    CompetitionDispatchRequest,
    CompetitionEngineBatch,
    CompetitionScheduleRequest,
    ScheduledFixture,
)
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.scheduler import CompetitionScheduler, CompetitionWindowResolver
from app.leagues.models import LeagueFixture, LeagueSeasonState


@dataclass(slots=True)
class LeagueCompetitionEngineService:
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)
    dispatcher: MatchDispatcher = field(default_factory=MatchDispatcher)

    def build_batch(self, state: LeagueSeasonState) -> CompetitionEngineBatch:
        requests = self._build_schedule_requests(state)
        plan = self.scheduler.build_schedule(requests)
        resolver = CompetitionWindowResolver.from_plan(plan, competition_id=state.season_id)
        scheduled_fixtures = self._build_scheduled_fixtures(state, resolver)
        dispatch_requests = self._build_dispatch_requests(state, scheduled_fixtures)
        return CompetitionEngineBatch(
            competition_id=state.season_id,
            competition_type=CompetitionType.LEAGUE,
            schedule_plan=plan,
            fixtures=scheduled_fixtures,
            dispatch_requests=dispatch_requests,
        )

    def dispatch_season(self, state: LeagueSeasonState):
        batch = self.build_batch(state)
        return self.dispatcher.dispatch_batch(batch)

    def _build_schedule_requests(
        self,
        state: LeagueSeasonState,
    ) -> tuple[CompetitionScheduleRequest, ...]:
        windows_by_date: dict[date, set[int]] = defaultdict(set)
        for fixture in state.fixtures:
            windows_by_date[fixture.kickoff_at.date()].add(fixture.window_number)
        return tuple(
            CompetitionScheduleRequest(
                competition_id=state.season_id,
                competition_type=CompetitionType.LEAGUE,
                requested_dates=(match_date,),
                required_windows=len(window_numbers),
                priority=20,
            )
            for match_date, window_numbers in sorted(windows_by_date.items())
        )

    def _build_scheduled_fixtures(
        self,
        state: LeagueSeasonState,
        resolver: CompetitionWindowResolver,
    ) -> tuple[ScheduledFixture, ...]:
        fixtures_by_date: dict[date, list[LeagueFixture]] = defaultdict(list)
        for fixture in state.fixtures:
            fixtures_by_date[fixture.kickoff_at.date()].append(fixture)

        scheduled: list[ScheduledFixture] = []
        for match_date, fixtures in sorted(fixtures_by_date.items()):
            ordered_window_numbers = sorted({fixture.window_number for fixture in fixtures})
            windows = resolver.windows_for_date(match_date)
            window_map = {
                window_number: windows[index]
                for index, window_number in enumerate(ordered_window_numbers)
            }
            for fixture in sorted(fixtures, key=lambda item: (item.window_number, item.fixture_id)):
                scheduled.append(
                    ScheduledFixture(
                        fixture_id=fixture.fixture_id,
                        competition_id=state.season_id,
                        competition_type=CompetitionType.LEAGUE,
                        round_number=fixture.round_number,
                        home_club_id=fixture.home_club_id,
                        away_club_id=fixture.away_club_id,
                        match_date=match_date,
                        window=window_map[fixture.window_number],
                        stage_name="league_round",
                        replay_visibility=ReplayVisibility.COMPETITION,
                        is_cup_match=False,
                        allow_penalties=False,
                    )
                )
        return tuple(scheduled)

    def _build_dispatch_requests(
        self,
        state: LeagueSeasonState,
        fixtures: tuple[ScheduledFixture, ...],
    ) -> tuple[CompetitionDispatchRequest, ...]:
        source_by_id = {fixture.fixture_id: fixture for fixture in state.fixtures}
        club_strengths = {club.club_id: club.strength_rating for club in state.clubs}
        return tuple(
            CompetitionDispatchRequest(
                fixture=fixture,
                season_id=state.season_id,
                competition_name=f"League Tier {state.buy_in_tier}",
                stage_name="league_round",
                scheduled_kickoff_at=source_by_id[fixture.fixture_id].kickoff_at,
                home_club_name=source_by_id[fixture.fixture_id].home_club_name,
                away_club_name=source_by_id[fixture.fixture_id].away_club_name,
                home_strength_rating=club_strengths.get(fixture.home_club_id),
                away_strength_rating=club_strengths.get(fixture.away_club_id),
            )
            for fixture in fixtures
        )
