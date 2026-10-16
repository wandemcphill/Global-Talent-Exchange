from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from app.champions_league.models.domain import KnockoutBracket, KnockoutTie, MatchStage, PlayoffBracket
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
class ChampionsLeagueCompetitionEngineService:
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)
    dispatcher: MatchDispatcher = field(default_factory=MatchDispatcher)

    def build_playoff_batch(
        self,
        *,
        competition_id: str,
        season_id: str,
        match_date: date,
        playoff: PlayoffBracket,
    ) -> CompetitionEngineBatch:
        return self._build_batch(
            competition_id=competition_id,
            season_id=season_id,
            ties=((match_date, tie) for tie in playoff.ties),
        )

    def build_knockout_batch(
        self,
        *,
        competition_id: str,
        season_id: str,
        stage_dates: dict[MatchStage, date],
        bracket: KnockoutBracket,
    ) -> CompetitionEngineBatch:
        stage_map = {
            MatchStage.KNOCKOUT_PLAYOFF: bracket.knockout_playoff,
            MatchStage.ROUND_OF_16: bracket.round_of_16,
            MatchStage.QUARTERFINAL: bracket.quarterfinals,
            MatchStage.SEMIFINAL: bracket.semifinals,
            MatchStage.FINAL: [bracket.final],
        }
        flattened: list[tuple[date, KnockoutTie]] = []
        for stage, ties in stage_map.items():
            match_date = stage_dates[stage]
            flattened.extend((match_date, tie) for tie in ties)
        return self._build_batch(
            competition_id=competition_id,
            season_id=season_id,
            ties=flattened,
        )

    def dispatch_batch(self, batch: CompetitionEngineBatch):
        return self.dispatcher.dispatch_batch(batch)

    def _build_batch(
        self,
        *,
        competition_id: str,
        season_id: str,
        ties: Iterable[tuple[date, KnockoutTie]],
    ) -> CompetitionEngineBatch:
        tie_entries = tuple(ties)
        tie_count_by_date: Counter[date] = Counter(match_date for match_date, _ in tie_entries)
        plan = self.scheduler.build_schedule(
            tuple(
                CompetitionScheduleRequest(
                    competition_id=competition_id,
                    competition_type=CompetitionType.CHAMPIONS_LEAGUE,
                    requested_dates=(match_date,),
                    required_windows=min(
                        tie_count_by_date[match_date],
                        len(CompetitionType.CHAMPIONS_LEAGUE.default_fixture_windows),
                    ),
                    priority=10,
                )
                for match_date in sorted(tie_count_by_date)
            )
        )
        resolver = CompetitionWindowResolver.from_plan(plan, competition_id=competition_id)
        ties_by_date: dict[date, list[KnockoutTie]] = defaultdict(list)
        for match_date, tie in tie_entries:
            ties_by_date[match_date].append(tie)

        scheduled: list[ScheduledFixture] = []
        dispatch_requests: list[CompetitionDispatchRequest] = []
        for match_date in sorted(ties_by_date):
            stage_counts: Counter[MatchStage] = Counter()
            day_ties = sorted(
                ties_by_date[match_date],
                key=lambda tie: (tie.stage.value, tie.tie_id),
            )
            for index, tie in enumerate(day_ties):
                stage_counts[tie.stage] += 1
                window, slot_sequence = resolver.slot_for(match_date, index)
                fixture = ScheduledFixture(
                    fixture_id=tie.tie_id,
                    competition_id=competition_id,
                    competition_type=CompetitionType.CHAMPIONS_LEAGUE,
                    round_number=stage_counts[tie.stage],
                    home_club_id=tie.home_club.club_id,
                    away_club_id=tie.away_club.club_id,
                    match_date=match_date,
                    window=window,
                    slot_sequence=slot_sequence,
                    stage_name=tie.stage.value,
                    replay_visibility=ReplayVisibility.COMPETITION,
                    is_cup_match=True,
                    allow_penalties=tie.penalties_if_tied,
                )
                scheduled.append(fixture)
                dispatch_requests.append(
                    CompetitionDispatchRequest(
                        fixture=fixture,
                        season_id=season_id,
                        competition_name="Champions League",
                        stage_name=tie.stage.value,
                        home_club_name=tie.home_club.club_name,
                        away_club_name=tie.away_club.club_name,
                        is_final=tie.stage is MatchStage.FINAL,
                    )
                )

        return CompetitionEngineBatch(
            competition_id=competition_id,
            competition_type=CompetitionType.CHAMPIONS_LEAGUE,
            schedule_plan=plan,
            fixtures=tuple(scheduled),
            dispatch_requests=tuple(dispatch_requests),
        )
