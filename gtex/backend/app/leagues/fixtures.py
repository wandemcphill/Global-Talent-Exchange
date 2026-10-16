from __future__ import annotations

from datetime import date, timedelta

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.schemas.competition import CompetitionScheduleRequest
from app.competition_engine.scheduler import CompetitionScheduler
from app.config.competition_constants import LEAGUE_MATCH_WINDOWS_PER_DAY
from app.leagues.models import LeagueClub, LeagueFixture


class LeagueFixtureGenerationService:
    def generate(
        self,
        *,
        season_id: str,
        clubs: tuple[LeagueClub, ...],
        season_start: date,
    ) -> tuple[LeagueFixture, ...]:
        participants: list[LeagueClub | None] = list(clubs)
        if len(participants) % 2 == 1:
            participants.append(None)

        if len(participants) < 2:
            return ()

        rounds: list[list[tuple[LeagueClub, LeagueClub]]] = []
        rotation = participants[:]
        total_rounds = len(rotation) - 1
        half_size = len(rotation) // 2

        for round_offset in range(total_rounds):
            pairings: list[tuple[LeagueClub, LeagueClub]] = []
            for index in range(half_size):
                home_candidate = rotation[index]
                away_candidate = rotation[-(index + 1)]
                if home_candidate is None or away_candidate is None:
                    continue
                if round_offset % 2 == 0:
                    home_club, away_club = home_candidate, away_candidate
                else:
                    home_club, away_club = away_candidate, home_candidate
                pairings.append((home_club, away_club))
            rounds.append(pairings)
            rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

        schedule_plan = self._build_schedule_plan(
            season_id=season_id,
            season_start=season_start,
            total_rounds=total_rounds * 2,
        )
        fixtures: list[LeagueFixture] = []
        for round_index, pairings in enumerate(rounds, start=1):
            fixtures.extend(
                self._build_round(
                    season_id=season_id,
                    schedule_plan=schedule_plan,
                    round_number=round_index,
                    pairings=tuple(pairings),
                )
            )

        reverse_offset = len(rounds)
        for round_index, pairings in enumerate(rounds, start=1):
            reversed_pairings = tuple((away_club, home_club) for home_club, away_club in pairings)
            fixtures.extend(
                self._build_round(
                    season_id=season_id,
                    schedule_plan=schedule_plan,
                    round_number=reverse_offset + round_index,
                    pairings=reversed_pairings,
                )
            )

        return tuple(fixtures)

    def _build_round(
        self,
        *,
        season_id: str,
        schedule_plan: dict[int, tuple[date, FixtureWindow]],
        round_number: int,
        pairings: tuple[tuple[LeagueClub, LeagueClub], ...],
    ) -> tuple[LeagueFixture, ...]:
        kickoff_date, window = schedule_plan[round_number]
        day_number = ((kickoff_date - schedule_plan[1][0]).days) + 1
        window_number = window.display_sequence
        kickoff_at = window.kickoff_at(kickoff_date)

        return tuple(
            LeagueFixture(
                fixture_id=f"{season_id}-r{round_number:02d}-m{match_index:02d}",
                round_number=round_number,
                day_number=day_number,
                window_number=window_number,
                kickoff_at=kickoff_at,
                home_club_id=home_club.club_id,
                home_club_name=home_club.club_name,
                away_club_id=away_club.club_id,
                away_club_name=away_club.club_name,
            )
            for match_index, (home_club, away_club) in enumerate(pairings, start=1)
        )

    def _build_schedule_plan(
        self,
        *,
        season_id: str,
        season_start: date,
        total_rounds: int,
    ) -> dict[int, tuple[date, FixtureWindow]]:
        scheduler = CompetitionScheduler()
        total_days = ((total_rounds - 1) // LEAGUE_MATCH_WINDOWS_PER_DAY) + 1
        requests = tuple(
            CompetitionScheduleRequest(
                competition_id=season_id,
                competition_type=CompetitionType.LEAGUE,
                requested_dates=(season_start + timedelta(days=day_offset),),
                required_windows=min(
                    LEAGUE_MATCH_WINDOWS_PER_DAY,
                    total_rounds - (day_offset * LEAGUE_MATCH_WINDOWS_PER_DAY),
                ),
            )
            for day_offset in range(total_days)
        )
        plan = scheduler.build_schedule(requests)
        assignments_by_date = {assignment.match_date: assignment for assignment in plan.assignments}
        round_schedule: dict[int, tuple[date, FixtureWindow]] = {}

        for round_number in range(1, total_rounds + 1):
            match_date = season_start + timedelta(days=((round_number - 1) // LEAGUE_MATCH_WINDOWS_PER_DAY))
            assignment = assignments_by_date[match_date]
            window_index = (round_number - 1) % LEAGUE_MATCH_WINDOWS_PER_DAY
            round_schedule[round_number] = (match_date, assignment.windows[window_index])

        return round_schedule


__all__ = ["LeagueFixtureGenerationService"]
