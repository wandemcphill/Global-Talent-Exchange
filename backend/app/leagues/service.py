from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import uuid4

from backend.app.competition_engine import MatchDispatcher, QueuedJobRecord
from backend.app.competitions.models.league_events import (
    LeagueClubOptOutEvent,
    LeagueFixtureCompletedEvent,
    LeaguePlayerStatsRecordedEvent,
    LeagueRegisteredClubEventData,
    LeagueSeasonEvent,
    LeagueSeasonRegisteredEvent,
)
from backend.app.config.competition_constants import (
    LEAGUE_BUY_IN_TIERS,
    LEAGUE_GROUP_SIZE,
    LEAGUE_MATCHES_PER_CLUB,
)
from backend.app.leagues.fixtures import LeagueFixtureGenerationService
from backend.app.leagues.models import LeagueClub, LeagueMatchResult, LeaguePlayerContribution, LeagueSeasonState
from backend.app.leagues.prizes import LeaguePrizeService
from backend.app.leagues.qualification import LeagueQualificationService
from backend.app.leagues.repository import LeagueEventRepository, get_league_event_repository
from backend.app.leagues.standings import LeagueStandingsService
from backend.app.leagues.competition_engine import LeagueCompetitionEngineService


class LeagueValidationError(ValueError):
    pass


class LeagueSeasonNotFoundError(LookupError):
    pass


class LeagueSeasonLifecycleService:
    def __init__(
        self,
        *,
        repository: LeagueEventRepository | None = None,
        fixture_service: LeagueFixtureGenerationService | None = None,
        standings_service: LeagueStandingsService | None = None,
        qualification_service: LeagueQualificationService | None = None,
        prize_service: LeaguePrizeService | None = None,
    ) -> None:
        self.repository = repository or get_league_event_repository()
        self.fixture_service = fixture_service or LeagueFixtureGenerationService()
        self.standings_service = standings_service or LeagueStandingsService()
        self.qualification_service = qualification_service or LeagueQualificationService()
        self.prize_service = prize_service or LeaguePrizeService()

    def register_season(
        self,
        *,
        buy_in_tier: int,
        clubs: tuple[LeagueClub, ...],
        season_start: date,
        season_id: str | None = None,
    ) -> LeagueSeasonState:
        self._validate_registration(buy_in_tier=buy_in_tier, clubs=clubs)
        resolved_season_id = season_id or f"league-{uuid4().hex[:12]}"
        event = LeagueSeasonRegisteredEvent(
            season_id=resolved_season_id,
            buy_in_tier=buy_in_tier,
            season_start=season_start,
            registered_at=datetime.now(timezone.utc),
            clubs=tuple(
                LeagueRegisteredClubEventData(
                    club_id=club.club_id,
                    club_name=club.club_name,
                    strength_rating=club.strength_rating,
                )
                for club in clubs
            ),
        )
        self.repository.append(event)
        return self.get_season_state(resolved_season_id)

    def record_fixture_result(
        self,
        *,
        season_id: str,
        fixture_id: str,
        home_goals: int,
        away_goals: int,
    ) -> LeagueSeasonState:
        if home_goals < 0 or away_goals < 0:
            raise LeagueValidationError("Match results must be non-negative")
        state = self.get_season_state(season_id)
        if fixture_id not in {fixture.fixture_id for fixture in state.fixtures}:
            raise LeagueValidationError(f"Fixture {fixture_id} does not exist in season {season_id}")
        self.repository.append(
            LeagueFixtureCompletedEvent(
                season_id=season_id,
                fixture_id=fixture_id,
                home_goals=home_goals,
                away_goals=away_goals,
                recorded_at=datetime.now(timezone.utc),
            )
        )
        return self.get_season_state(season_id)

    def record_player_stats(
        self,
        *,
        season_id: str,
        player_contributions: tuple[LeaguePlayerContribution, ...],
    ) -> LeagueSeasonState:
        self.get_season_state(season_id)
        for contribution in player_contributions:
            self.repository.append(
                LeaguePlayerStatsRecordedEvent(
                    season_id=season_id,
                    player_id=contribution.player_id,
                    player_name=contribution.player_name,
                    club_id=contribution.club_id,
                    goals=contribution.goals,
                    assists=contribution.assists,
                    recorded_at=datetime.now(timezone.utc),
                )
            )
        return self.get_season_state(season_id)

    def record_club_opt_out(
        self,
        *,
        season_id: str,
        club_id: str,
    ) -> LeagueSeasonState:
        state = self.get_season_state(season_id)
        if club_id not in {club.club_id for club in state.clubs}:
            raise LeagueValidationError(f"Club {club_id} is not registered in season {season_id}")
        self.repository.append(
            LeagueClubOptOutEvent(
                season_id=season_id,
                club_id=club_id,
                recorded_at=datetime.now(timezone.utc),
            )
        )
        return self.get_season_state(season_id)

    def get_season_state(self, season_id: str) -> LeagueSeasonState:
        events = self.repository.list_events(season_id)
        if not events:
            raise LeagueSeasonNotFoundError(f"League season {season_id} was not found")
        return self._reduce(events)

    def _reduce(self, events: tuple[LeagueSeasonEvent, ...]) -> LeagueSeasonState:
        registration = next((event for event in events if isinstance(event, LeagueSeasonRegisteredEvent)), None)
        if registration is None:
            raise LeagueSeasonNotFoundError("League season is missing its registration event")

        clubs = tuple(
            LeagueClub(
                club_id=club.club_id,
                club_name=club.club_name,
                strength_rating=club.strength_rating,
            )
            for club in registration.clubs
        )
        fixtures = self.fixture_service.generate(
            season_id=registration.season_id,
            clubs=clubs,
            season_start=registration.season_start,
        )
        results_by_fixture = {
            event.fixture_id: LeagueMatchResult(home_goals=event.home_goals, away_goals=event.away_goals)
            for event in events
            if isinstance(event, LeagueFixtureCompletedEvent)
        }
        fixtures = tuple(replace(fixture, result=results_by_fixture.get(fixture.fixture_id)) for fixture in fixtures)

        base_standings = self.standings_service.compute(clubs=clubs, fixtures=fixtures)
        opted_out_club_ids = {
            event.club_id
            for event in events
            if isinstance(event, LeagueClubOptOutEvent)
        }
        standings = self.qualification_service.apply_markers(base_standings, opted_out_club_ids=opted_out_club_ids)
        auto_entry_slots = self.qualification_service.build_auto_entry_slots(
            standings,
            opted_out_club_ids=opted_out_club_ids,
        )

        player_contributions = tuple(
            LeaguePlayerContribution(
                player_id=event.player_id,
                player_name=event.player_name,
                club_id=event.club_id,
                goals=event.goals,
                assists=event.assists,
            )
            for event in events
            if isinstance(event, LeaguePlayerStatsRecordedEvent)
        )
        prize_pool, champion_prize, top_scorer_award, top_assist_award = self.prize_service.calculate(
            buy_in_tier=registration.buy_in_tier,
            club_count=len(clubs),
            standings=standings,
            player_contributions=player_contributions,
        )

        completed_fixture_count = sum(1 for fixture in fixtures if fixture.result is not None)
        total_fixture_count = len(fixtures)
        status = "scheduled"
        if completed_fixture_count and completed_fixture_count < total_fixture_count:
            status = "in_progress"
        elif total_fixture_count and completed_fixture_count == total_fixture_count:
            status = "completed"

        scheduled_matches_per_club = (len(clubs) - 1) * 2 if len(clubs) > 1 else 0
        return LeagueSeasonState(
            season_id=registration.season_id,
            buy_in_tier=registration.buy_in_tier,
            season_start=registration.season_start,
            registered_at=registration.registered_at,
            clubs=clubs,
            fixtures=fixtures,
            standings=standings,
            auto_entry_slots=auto_entry_slots,
            opted_out_club_ids=tuple(sorted(opted_out_club_ids)),
            prize_pool=prize_pool,
            champion_prize=champion_prize,
            top_scorer_award=top_scorer_award,
            top_assist_award=top_assist_award,
            status=status,
            completed_fixture_count=completed_fixture_count,
            total_fixture_count=total_fixture_count,
            scheduled_matches_per_club=scheduled_matches_per_club,
            target_matches_per_club=LEAGUE_MATCHES_PER_CLUB,
            group_size_target=LEAGUE_GROUP_SIZE,
            group_is_full=len(clubs) == LEAGUE_GROUP_SIZE,
        )

    def build_match_dispatch_jobs(
        self,
        *,
        season_id: str,
        dispatcher: MatchDispatcher | None = None,
    ) -> tuple[QueuedJobRecord, ...]:
        state = self.get_season_state(season_id)
        engine_service = LeagueCompetitionEngineService(
            dispatcher=dispatcher or MatchDispatcher(),
        )
        return engine_service.dispatch_season(state)

    def _validate_registration(
        self,
        *,
        buy_in_tier: int,
        clubs: tuple[LeagueClub, ...],
    ) -> None:
        if buy_in_tier not in LEAGUE_BUY_IN_TIERS:
            raise LeagueValidationError(f"Unsupported league buy-in tier: {buy_in_tier}")
        if len(clubs) < 2:
            raise LeagueValidationError("At least two clubs are required to create a league season")
        if len(clubs) > LEAGUE_GROUP_SIZE:
            raise LeagueValidationError(f"League groups support at most {LEAGUE_GROUP_SIZE} clubs")
        club_ids = [club.club_id for club in clubs]
        if len(set(club_ids)) != len(club_ids):
            raise LeagueValidationError("Club registrations must be unique within a season")


__all__ = [
    "LeagueSeasonLifecycleService",
    "LeagueSeasonNotFoundError",
    "LeagueValidationError",
]
