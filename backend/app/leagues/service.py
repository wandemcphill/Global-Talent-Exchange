from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.competition_engine import MatchDispatcher, QueuedJobRecord
from app.competitions.models.league_events import (
    LeagueClubHeldEvent,
    LeagueClubOptOutEvent,
    LeagueFixtureCompletedEvent,
    LeaguePlayerStatsRecordedEvent,
    LeagueRegisteredClubEventData,
    LeagueSeasonEvent,
    LeagueSeasonRegisteredEvent,
)
from app.config.competition_constants import (
    LEAGUE_GROUP_SIZE,
    LEAGUE_MATCHES_PER_CLUB,
)
from app.leagues.fixtures import LeagueFixtureGenerationService
from app.leagues.models import (
    LeagueClub,
    LeagueDivisionLinkRecordedEvent,
    LeagueMatchResult,
    LeaguePlayerContribution,
    LeagueSeasonState,
)
from app.leagues.prizes import LeaguePrizeService
from app.leagues.pyramid import (
    DIVISION_LADDER,
    SHORT_CALENDAR_LEVELS,
    DivisionCohort,
    PyramidClub,
    child_level,
    normalize_region,
    parent_level,
    plan_division_cohorts,
    rollover_clubs,
)
from app.leagues.qualification import LeagueQualificationService
from app.leagues.repository import LeagueEventRepository, get_league_event_repository
from app.leagues.standings import LeagueStandingsService
from app.leagues.competition_engine import LeagueCompetitionEngineService


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
        buy_in_tier: int = 0,
        clubs: tuple[LeagueClub, ...],
        season_start: date,
        season_id: str | None = None,
        club_divisions: dict[str, str] | None = None,
        division_level: str = "",
        region_code: str = "",
        cohort_index: int = 0,
        season_label: str = "",
    ) -> LeagueSeasonState:
        _ = buy_in_tier  # Entry is a right of club ownership. The value cannot gate or price a season.
        self._validate_registration(clubs=clubs)
        if club_divisions:
            self._reject_mixed_division(clubs=clubs, club_divisions=club_divisions)
            if all(club.club_id in club_divisions for club in clubs):
                division_level = next(iter({club_divisions[club.club_id] or "foundation" for club in clubs}))
        resolved_season_id = season_id or f"league-{uuid4().hex[:12]}"
        event = LeagueSeasonRegisteredEvent(
            season_id=resolved_season_id,
            buy_in_tier=0,
            season_start=season_start,
            registered_at=datetime.now(timezone.utc),
            single_round=self._uses_foundation_calendar(clubs, club_divisions),
            division_level=division_level,
            region_code=region_code,
            cohort_index=cohort_index,
            season_label=season_label,
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
            double_round=not registration.single_round,
        )
        results_by_fixture = {
            event.fixture_id: LeagueMatchResult(home_goals=event.home_goals, away_goals=event.away_goals)
            for event in events
            if isinstance(event, LeagueFixtureCompletedEvent)
        }
        fixtures = tuple(replace(fixture, result=results_by_fixture.get(fixture.fixture_id)) for fixture in fixtures)

        base_standings = self.standings_service.compute(clubs=clubs, fixtures=fixtures)
        opted_out_club_ids = {event.club_id for event in events if isinstance(event, LeagueClubOptOutEvent)}
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
            division_level=registration.division_level or "foundation",
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

        round_multiplier = 1 if registration.single_round else 2
        scheduled_matches_per_club = (len(clubs) - 1) * round_multiplier if len(clubs) > 1 else 0
        idle_events = [
            event
            for event in events
            if isinstance(event, LeagueFixtureCompletedEvent) and event.fixture_id.endswith("-idle-result")
        ]
        idle_result = None
        if len(clubs) == 1 and idle_events:
            latest_idle = idle_events[-1]
            idle_result = LeagueMatchResult(home_goals=latest_idle.home_goals, away_goals=latest_idle.away_goals)
            status = "completed"
        return LeagueSeasonState(
            season_id=registration.season_id,
            buy_in_tier=0,
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
            division_level=registration.division_level,
            region_code=registration.region_code,
            cohort_index=registration.cohort_index,
            season_label=registration.season_label,
            idle_result=idle_result,
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

    def open_regional_seasons(
        self,
        *,
        clubs: tuple[PyramidClub, ...] | list[PyramidClub],
        season_start: date,
        season_label: str,
    ) -> tuple[tuple[LeagueSeasonState, ...], tuple[DivisionCohort, ...]]:
        """Open one season per full regional division. A lone club gets a stored idle result."""
        cohorts = plan_division_cohorts(clubs)
        for region in sorted({normalize_region(club.region_code) for club in clubs}):
            self._record_region_ladder(region)
        opened: list[LeagueSeasonState] = []
        idle: list[DivisionCohort] = []
        for cohort in cohorts:
            if cohort.idle:
                idle.append(cohort)
                continue
            opened.append(
                self.register_season(
                    season_id=f"{season_label}-{cohort.region_code}-{cohort.division_level}-{cohort.cohort_index}",
                    buy_in_tier=cohort.buy_in_tier,
                    season_start=season_start,
                    clubs=tuple(
                        LeagueClub(
                            club_id=club.club_id,
                            club_name=club.club_name,
                            strength_rating=club.strength_rating,
                        )
                        for club in cohort.clubs
                    ),
                    club_divisions={club.club_id: club.division_level for club in cohort.clubs},
                    division_level=cohort.division_level,
                    region_code=cohort.region_code,
                    cohort_index=cohort.cohort_index,
                    season_label=season_label,
                )
            )
        self._remember_idle_clubs(season_label, idle, season_start=season_start)
        return tuple(opened), tuple(idle)

    def rollover_regional_seasons(
        self,
        seasons: tuple[LeagueSeasonState, ...] | list[LeagueSeasonState],
        idle_cohorts: tuple[DivisionCohort, ...] | list[DivisionCohort] = (),
    ) -> tuple[PyramidClub, ...]:
        """Place finished clubs in the next division. Idle clubs keep their level."""
        refreshed = []
        for season in seasons:
            refreshed.append(season if season.status == "completed" else self.get_season_state(season.season_id))
        return rollover_clubs(refreshed, idle_cohorts)

    def open_next_regional_seasons(
        self,
        seasons: tuple[LeagueSeasonState, ...] | list[LeagueSeasonState],
        idle_cohorts: tuple[DivisionCohort, ...] | list[DivisionCohort] = (),
        *,
        season_start: date,
        season_label: str,
    ) -> tuple[tuple[LeagueSeasonState, ...], tuple[DivisionCohort, ...]]:
        """Open the next year once every named division has a full table."""
        refreshed: list[LeagueSeasonState] = []
        for season in seasons:
            state = season if season.status == "completed" else self.get_season_state(season.season_id)
            if state.status != "completed":
                raise LeagueValidationError("Every division must finish before the next season opens.")
            refreshed.append(state)
        waiting = self._waiting_clubs(refreshed)
        for cohort in idle_cohorts:
            for club in cohort.clubs:
                if club.club_id not in {item.club_id for item in waiting}:
                    waiting.append(club)
        clubs = rollover_clubs(refreshed, waiting=tuple(waiting))
        if not clubs:
            raise LeagueValidationError("No clubs are ready for the next season.")
        return self.open_regional_seasons(clubs=clubs, season_start=season_start, season_label=season_label)

    def _remember_idle_clubs(
        self,
        season_label: str,
        cohorts: tuple[DivisionCohort, ...] | list[DivisionCohort],
        *,
        season_start: date | None = None,
    ) -> None:
        if not season_label:
            return
        bucket = f"pyramid-idle-{season_label}"
        existing = {
            event.club_id for event in self.repository.list_events(bucket) if isinstance(event, LeagueClubHeldEvent)
        }
        now = datetime.now(timezone.utc)
        for cohort in cohorts:
            for club in cohort.clubs:
                if club.club_id in existing:
                    continue
                self.repository.append(
                    LeagueClubHeldEvent(
                        season_id=bucket,
                        club_id=club.club_id,
                        club_name=club.club_name,
                        division_level=club.division_level,
                        region_code=club.region_code,
                        strength_rating=club.strength_rating,
                        recorded_at=now,
                    )
                )
                existing.add(club.club_id)
            if season_start is not None:
                self._record_idle_result(season_label, cohort, season_start)

    def _record_idle_result(self, season_label: str, cohort: DivisionCohort, season_start: date) -> None:
        """One stored result for a club with nobody to play. They stay in this division."""
        if len(cohort.clubs) != 1:
            return
        club = cohort.clubs[0]
        season_id = f"{season_label}-{cohort.region_code}-{cohort.division_level}-idle-{cohort.cohort_index}"
        if any(isinstance(event, LeagueSeasonRegisteredEvent) for event in self.repository.list_events(season_id)):
            return
        now = datetime.now(timezone.utc)
        self.repository.append(
            LeagueSeasonRegisteredEvent(
                season_id=season_id,
                buy_in_tier=0,
                season_start=season_start,
                registered_at=now,
                single_round=True,
                division_level=cohort.division_level,
                region_code=cohort.region_code,
                cohort_index=cohort.cohort_index,
                season_label=season_label,
                clubs=(
                    LeagueRegisteredClubEventData(
                        club_id=club.club_id,
                        club_name=club.club_name,
                        strength_rating=club.strength_rating,
                    ),
                ),
            )
        )
        self.repository.append(
            LeagueFixtureCompletedEvent(
                season_id=season_id,
                fixture_id=f"{season_id}-idle-result",
                home_goals=0,
                away_goals=0,
                recorded_at=now,
            )
        )

    def region_division_chain(self, region_code: str) -> tuple[LeagueDivisionLinkRecordedEvent, ...]:
        bucket = f"pyramid-ladder-{normalize_region(region_code)}"
        return tuple(
            event for event in self.repository.list_events(bucket) if isinstance(event, LeagueDivisionLinkRecordedEvent)
        )

    def _record_region_ladder(self, region_code: str) -> None:
        """Store foundation through division_1 the first time a club is placed in a region.

        Empty divisions are links only. They do not get a fixture list.
        """
        if self.region_division_chain(region_code):
            return
        bucket = f"pyramid-ladder-{region_code}"
        now = datetime.now(timezone.utc)
        for index, level in enumerate(DIVISION_LADDER):
            self.repository.append(
                LeagueDivisionLinkRecordedEvent(
                    season_id=bucket,
                    region_code=region_code,
                    division_level=level,
                    parent_level=parent_level(level),
                    child_level=child_level(level),
                    recorded_at=now + timedelta(microseconds=index),
                )
            )

    def _waiting_clubs(self, seasons: list[LeagueSeasonState]) -> list[PyramidClub]:
        playing = {club.club_id for season in seasons for club in season.clubs}
        waiting: list[PyramidClub] = []
        seen: set[str] = set()
        for label in {season.season_label for season in seasons if season.season_label}:
            for event in self.repository.list_events(f"pyramid-idle-{label}"):
                if not isinstance(event, LeagueClubHeldEvent):
                    continue
                if event.club_id in playing or event.club_id in seen:
                    continue
                seen.add(event.club_id)
                waiting.append(
                    PyramidClub(
                        club_id=event.club_id,
                        club_name=event.club_name,
                        division_level=event.division_level,
                        region_code=event.region_code,
                        strength_rating=event.strength_rating,
                    )
                )
        return waiting

    def _validate_registration(
        self,
        *,
        clubs: tuple[LeagueClub, ...],
    ) -> None:
        if len(clubs) < 2:
            raise LeagueValidationError("At least two clubs are required to create a league season")
        if len(clubs) > LEAGUE_GROUP_SIZE:
            raise LeagueValidationError(f"League groups support at most {LEAGUE_GROUP_SIZE} clubs")
        club_ids = [club.club_id for club in clubs]
        if len(set(club_ids)) != len(club_ids):
            raise LeagueValidationError("Club registrations must be unique within a season")

    @staticmethod
    def _reject_mixed_division(
        *,
        clubs: tuple[LeagueClub, ...],
        club_divisions: dict[str, str],
    ) -> None:
        if any(club.club_id not in club_divisions for club in clubs):
            return
        levels = {club_divisions[club.club_id] or "foundation" for club in clubs}
        if len(levels) != 1:
            raise LeagueValidationError(
                "A league season stays inside one division. Promotion is the only way into the division above."
            )

    @staticmethod
    def _uses_foundation_calendar(
        clubs: tuple[LeagueClub, ...],
        club_divisions: dict[str, str] | None,
    ) -> bool:
        """Foundation and the first step above it play one meeting, not a home-and-away season."""
        if not club_divisions:
            return False
        for club in clubs:
            if club.club_id not in club_divisions:
                return False
            if (club_divisions[club.club_id] or "foundation") not in SHORT_CALENDAR_LEVELS:
                return False
        return True


__all__ = [
    "LeagueSeasonLifecycleService",
    "LeagueSeasonNotFoundError",
    "LeagueValidationError",
]
