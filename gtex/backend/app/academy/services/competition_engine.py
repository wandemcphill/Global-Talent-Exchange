from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.academy.models import AcademySeasonProjection
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


@dataclass(slots=True)
class AcademyCompetitionEngineService:
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)
    dispatcher: MatchDispatcher = field(default_factory=MatchDispatcher)

    def build_batch(self, projection: AcademySeasonProjection) -> CompetitionEngineBatch:
        slot_counts_by_date: dict[date, int] = defaultdict(int)
        for fixture in projection.fixtures:
            slot_counts_by_date[fixture.match_date] = max(
                slot_counts_by_date[fixture.match_date],
                fixture.window_number,
            )
        plan = self.scheduler.build_schedule(
            tuple(
                CompetitionScheduleRequest(
                    competition_id=projection.season_id,
                    competition_type=CompetitionType.ACADEMY,
                    requested_dates=(match_date,),
                    required_windows=slot_count,
                    priority=30,
                )
                for match_date, slot_count in sorted(slot_counts_by_date.items())
            )
        )
        resolver = CompetitionWindowResolver.from_plan(plan, competition_id=projection.season_id)
        fixtures = tuple(
            self._build_scheduled_fixture(
                projection=projection,
                fixture=fixture,
                resolver=resolver,
            )
            for fixture in projection.fixtures
        )
        dispatch_requests = tuple(
            CompetitionDispatchRequest(
                fixture=fixture,
                season_id=projection.season_id,
                competition_name="Academy Competition",
                stage_name=fixture.stage_name,
                home_club_name=source.home_club_name,
                away_club_name=source.away_club_name,
            )
            for fixture, source in zip(fixtures, projection.fixtures, strict=True)
        )
        return CompetitionEngineBatch(
            competition_id=projection.season_id,
            competition_type=CompetitionType.ACADEMY,
            schedule_plan=plan,
            fixtures=fixtures,
            dispatch_requests=dispatch_requests,
        )

    def dispatch_projection(self, projection: AcademySeasonProjection):
        batch = self.build_batch(projection)
        return self.dispatcher.dispatch_batch(batch)

    def _build_scheduled_fixture(
        self,
        *,
        projection: AcademySeasonProjection,
        fixture,
        resolver: CompetitionWindowResolver,
    ) -> ScheduledFixture:
        window, slot_sequence = resolver.slot_for(fixture.match_date, fixture.window_number - 1)
        return ScheduledFixture(
            fixture_id=fixture.fixture_id,
            competition_id=projection.season_id,
            competition_type=CompetitionType.ACADEMY,
            round_number=fixture.round_number,
            home_club_id=fixture.home_club_id,
            away_club_id=fixture.away_club_id,
            match_date=fixture.match_date,
            window=window,
            slot_sequence=slot_sequence,
            stage_name=fixture.stage_name,
            replay_visibility=ReplayVisibility.COMPETITION,
            is_cup_match=fixture.is_cup_match,
            allow_penalties=fixture.allow_penalties,
        )
