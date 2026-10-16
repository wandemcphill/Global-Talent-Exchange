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
from app.competition_engine.match_dispatcher import MatchDispatcher, scale_strength_rating
from app.competition_engine.scheduler import CompetitionScheduler, CompetitionWindowResolver
from app.fast_cups.models.domain import FastCup, FastCupBracket, FastCupMatch, FastCupRound


@dataclass(slots=True)
class FastCupCompetitionEngineService:
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)
    dispatcher: MatchDispatcher = field(default_factory=MatchDispatcher)

    def build_batch(self, cup: FastCup, bracket: FastCupBracket) -> CompetitionEngineBatch:
        rounds = tuple(round_entry for round_entry in bracket.rounds if round_entry.matches)
        matches_by_date: dict[date, list[FastCupMatch]] = defaultdict(list)
        for round_entry in rounds:
            for match in round_entry.matches:
                if match.home is None or match.away is None:
                    continue
                matches_by_date[match.scheduled_at.date()].append(match)
        ratings = [
            entrant.rating
            for day_matches in matches_by_date.values()
            for match in day_matches
            for entrant in (match.home, match.away)
            if entrant is not None
        ]
        minimum_rating = min(ratings)
        maximum_rating = max(ratings)
        plan = self.scheduler.build_schedule(
            tuple(
                CompetitionScheduleRequest(
                    competition_id=cup.cup_id,
                    competition_type=CompetitionType.FAST_CUP,
                    requested_dates=(match_date,),
                    required_windows=len(day_matches),
                    priority=40,
                )
                for match_date, day_matches in sorted(matches_by_date.items())
            )
        )
        resolver = CompetitionWindowResolver.from_plan(plan, competition_id=cup.cup_id)
        scheduled: list[ScheduledFixture] = []
        dispatch_requests: list[CompetitionDispatchRequest] = []

        for match_date, day_matches in sorted(matches_by_date.items()):
            ordered_matches = sorted(day_matches, key=lambda item: (item.scheduled_at, item.tie_id))
            for index, match in enumerate(ordered_matches):
                window, slot_sequence = resolver.slot_for(match_date, index)
                fixture = ScheduledFixture(
                    fixture_id=match.tie_id,
                    competition_id=cup.cup_id,
                    competition_type=CompetitionType.FAST_CUP,
                    round_number=match.round_number,
                    home_club_id=match.home.club_id,
                    away_club_id=match.away.club_id,
                    match_date=match_date,
                    window=window,
                    slot_sequence=slot_sequence,
                    stage_name=match.stage.value,
                    replay_visibility=ReplayVisibility.PUBLIC,
                    is_cup_match=True,
                    allow_penalties=match.penalties_if_tied,
                )
                scheduled.append(fixture)
                dispatch_requests.append(
                    CompetitionDispatchRequest(
                        fixture=fixture,
                        competition_name=cup.title,
                        stage_name=match.stage.value,
                        scheduled_kickoff_at=match.scheduled_at,
                        home_club_name=match.home.club_name,
                        away_club_name=match.away.club_name,
                        home_strength_rating=scale_strength_rating(
                            match.home.rating,
                            minimum=minimum_rating,
                            maximum=maximum_rating,
                        ),
                        away_strength_rating=scale_strength_rating(
                            match.away.rating,
                            minimum=minimum_rating,
                            maximum=maximum_rating,
                        ),
                        is_final=match.stage.value == "final",
                    )
                )

        return CompetitionEngineBatch(
            competition_id=cup.cup_id,
            competition_type=CompetitionType.FAST_CUP,
            schedule_plan=plan,
            fixtures=tuple(scheduled),
            dispatch_requests=tuple(dispatch_requests),
        )

    def dispatch_bracket(self, cup: FastCup, bracket: FastCupBracket):
        batch = self.build_batch(cup, bracket)
        return self.dispatcher.dispatch_batch(batch)
