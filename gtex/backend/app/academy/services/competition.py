from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from typing import Sequence

from app.academy.models import (
    AcademyAwardAllocation,
    AcademyAwardsLeaders,
    AcademyAwardsPreview,
    AcademyChampionsLeagueFlow,
    AcademyClubRegistration,
    AcademyClubRegistrationRequest,
    AcademyFixture,
    AcademyKnockoutTie,
    AcademyLedgerEvent,
    AcademyLeaguePhaseRow,
    AcademyMatchResult,
    AcademyQualificationEntry,
    AcademyQualificationPlan,
    AcademySeasonProjection,
    AcademySeasonRequest,
    AcademySeasonStatus,
    AcademyStandingRow,
    AcademyValidationError,
)
from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.qualification_status import QualificationStatus
from app.common.schemas.competition import CompetitionScheduleRequest
from app.competition_engine import MatchDispatcher, QueuedJobRecord
from app.competition_engine.scheduler import CompetitionScheduler
from app.config.competition_constants import (
    ACADEMY_BUY_IN_MULTIPLIER,
    CHAMPIONS_LEAGUE_DIRECT_SLOTS,
    CHAMPIONS_LEAGUE_FUND_PCT,
    CHAMPIONS_LEAGUE_TOTAL_QUALIFIERS,
    FINAL_PRESENTATION_MAX_MINUTES,
    LEAGUE_BUY_IN_TIERS,
    LEAGUE_GROUP_SIZE,
    LEAGUE_MATCH_WINDOWS_PER_DAY,
    LEAGUE_WINNER_PCT,
    MATCH_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MIN_MINUTES,
    TOP_ASSIST_PCT,
    TOP_SCORER_PCT,
)
from app.academy.services.competition_engine import AcademyCompetitionEngineService

_CURRENCY_QUANTUM = Decimal("0.01")


@dataclass(slots=True)
class AcademyCompetitionService:
    def build_registration_plan(self, request: AcademySeasonRequest) -> tuple[AcademyClubRegistration, ...]:
        registrations, _ = self._build_registration_bundle(request)
        return registrations

    def build_fixtures(self, request: AcademySeasonRequest) -> tuple[AcademyFixture, ...]:
        registrations, _ = self._build_registration_bundle(request)
        fixtures, _ = self._build_fixtures_bundle(
            season_id=request.season_id,
            start_date=request.start_date,
            registrations=registrations,
        )
        return fixtures

    def build_standings(self, request: AcademySeasonRequest) -> tuple[AcademyStandingRow, ...]:
        _, _, _, standings, _, _, _, _, _ = self._build_projection_parts(request)
        return standings

    def build_match_dispatch_jobs(
        self,
        request: AcademySeasonRequest,
        *,
        dispatcher: MatchDispatcher | None = None,
    ) -> tuple[QueuedJobRecord, ...]:
        projection = self.build_season_projection(request)
        engine_service = AcademyCompetitionEngineService(
            dispatcher=dispatcher or MatchDispatcher(),
        )
        return engine_service.dispatch_projection(projection)

    def build_qualification_plan(self, request: AcademySeasonRequest) -> AcademyChampionsLeagueFlow:
        _, _, _, _, _, flow, _, _, _ = self._build_projection_parts(request)
        return flow

    def build_awards(self, request: AcademySeasonRequest) -> AcademyAwardsPreview:
        _, _, _, _, _, _, awards, _, _ = self._build_projection_parts(request)
        return awards

    def build_season_projection(self, request: AcademySeasonRequest) -> AcademySeasonProjection:
        registrations, fixtures, completed_results, standings, qualification, flow, awards, rollover_clubs, ledger_events = (
            self._build_projection_parts(request)
        )
        completed_fixture_count = len(completed_results)
        status = self._resolve_status(fixtures=fixtures, completed_fixture_count=completed_fixture_count)
        champion = standings[0]
        return AcademySeasonProjection(
            season_id=request.season_id,
            status=status,
            start_date=request.start_date,
            end_date=request.start_date + timedelta(days=6),
            active_during_senior_world_super_cup=(
                request.senior_world_super_cup_active and CompetitionType.ACADEMY.remains_active_during_world_super_cup
            ),
            registrations=registrations,
            fixtures=fixtures,
            completed_fixture_count=completed_fixture_count,
            standings=standings,
            qualification=qualification,
            champions_league=flow,
            awards=awards,
            rollover_clubs=rollover_clubs,
            champion_club_id=champion.club_id,
            champion_club_name=champion.club_name,
            ledger_events=ledger_events,
        )

    def _build_projection_parts(
        self,
        request: AcademySeasonRequest,
    ) -> tuple[
        tuple[AcademyClubRegistration, ...],
        tuple[AcademyFixture, ...],
        tuple[AcademyMatchResult, ...],
        tuple[AcademyStandingRow, ...],
        AcademyQualificationPlan,
        AcademyChampionsLeagueFlow,
        AcademyAwardsPreview,
        tuple[AcademyClubRegistration, ...],
        tuple[AcademyLedgerEvent, ...],
    ]:
        registrations, registration_events = self._build_registration_bundle(request)
        fixtures, fixture_events = self._build_fixtures_bundle(
            season_id=request.season_id,
            start_date=request.start_date,
            registrations=registrations,
        )
        completed_results = self._normalize_results(fixtures=fixtures, results=request.results)
        standings = self._build_standings(registrations=registrations, fixtures=fixtures, results=completed_results)
        qualification = self._build_qualification_entries(standings)
        flow = self._build_champions_league_flow(request.season_id, qualification)
        awards = self._build_awards(registrations, standings, request.awards_leaders)
        rollover_clubs = self._build_rollover_clubs(registrations, standings)
        status = self._resolve_status(fixtures=fixtures, completed_fixture_count=len(completed_results))
        lifecycle_events = (
            AcademyLedgerEvent(
                event_key=f"{request.season_id}:season:status:{status.value}",
                event_type=f"academy.season.{status.value}",
                aggregate_id=request.season_id,
                payload={
                    "completed_fixture_count": len(completed_results),
                    "total_fixture_count": len(fixtures),
                    "senior_world_super_cup_active": request.senior_world_super_cup_active,
                },
            ),
        )
        return (
            registrations,
            fixtures,
            completed_results,
            standings,
            qualification,
            flow,
            awards,
            rollover_clubs,
            registration_events + fixture_events + lifecycle_events,
        )

    def _build_registration_bundle(
        self,
        request: AcademySeasonRequest,
    ) -> tuple[tuple[AcademyClubRegistration, ...], tuple[AcademyLedgerEvent, ...]]:
        self._validate_club_requests(request.clubs)
        registrations = tuple(
            AcademyClubRegistration(
                club_id=club.club_id,
                club_name=club.club_name,
                senior_buy_in_tier=club.senior_buy_in_tier,
                academy_buy_in=self._academy_buy_in(club.senior_buy_in_tier),
                carry_over_from_previous_season=club.carry_over_from_previous_season,
            )
            for club in request.clubs
        )
        events = tuple(
            AcademyLedgerEvent(
                event_key=f"{request.season_id}:registration:{club.club_id}",
                event_type="academy.registration.accepted",
                aggregate_id=request.season_id,
                payload={
                    "club_id": club.club_id,
                    "senior_buy_in_tier": club.senior_buy_in_tier,
                    "carry_over_from_previous_season": club.carry_over_from_previous_season,
                },
            )
            for club in registrations
        )
        return registrations, events

    def _build_fixtures_bundle(
        self,
        *,
        season_id: str,
        start_date: date,
        registrations: Sequence[AcademyClubRegistration],
    ) -> tuple[tuple[AcademyFixture, ...], tuple[AcademyLedgerEvent, ...]]:
        single_round = self._build_single_round_pairings(registrations)
        all_rounds = single_round + [[(away, home) for home, away in matchups] for matchups in single_round]
        round_schedule = self._build_round_schedule(
            season_id=season_id,
            start_date=start_date,
            total_rounds=len(all_rounds),
        )
        fixtures: list[AcademyFixture] = []
        for round_index, matchups in enumerate(all_rounds, start=1):
            match_date, shared_window, window_number = round_schedule[round_index]
            for fixture_index, (home, away) in enumerate(matchups, start=1):
                fixtures.append(
                    AcademyFixture(
                        fixture_id=f"{season_id}:r{round_index:02d}:m{fixture_index:02d}",
                        season_id=season_id,
                        round_number=round_index,
                        match_date=match_date,
                        window_number=window_number,
                        competition_type=CompetitionType.ACADEMY,
                        shared_window=shared_window,
                        home_club_id=home.club_id,
                        home_club_name=home.club_name,
                        away_club_id=away.club_id,
                        away_club_name=away.club_name,
                        stage_name="academy_league",
                        is_cup_match=False,
                        allow_penalties=False,
                        extra_time_allowed=False,
                        presentation_min_minutes=MATCH_PRESENTATION_MIN_MINUTES,
                        presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
                    )
                )
        events = (
            AcademyLedgerEvent(
                event_key=f"{season_id}:fixtures:generated",
                event_type="academy.fixtures.generated",
                aggregate_id=season_id,
                payload={
                    "fixture_count": len(fixtures),
                    "round_count": len(all_rounds),
                    "season_days": 7,
                },
            ),
        )
        return tuple(fixtures), events

    def _build_round_schedule(
        self,
        *,
        season_id: str,
        start_date: date,
        total_rounds: int,
    ) -> dict[int, tuple[date, FixtureWindow, int]]:
        scheduler = CompetitionScheduler()
        total_days = ((total_rounds - 1) // LEAGUE_MATCH_WINDOWS_PER_DAY) + 1
        requests = tuple(
            CompetitionScheduleRequest(
                competition_id=season_id,
                competition_type=CompetitionType.ACADEMY,
                requested_dates=(start_date + timedelta(days=day_offset),),
                required_windows=min(
                    LEAGUE_MATCH_WINDOWS_PER_DAY,
                    total_rounds - (day_offset * LEAGUE_MATCH_WINDOWS_PER_DAY),
                ),
            )
            for day_offset in range(total_days)
        )
        plan = scheduler.build_schedule(requests)
        assignments_by_date = {assignment.match_date: assignment for assignment in plan.assignments}
        round_schedule: dict[int, tuple[date, FixtureWindow, int]] = {}

        for round_number in range(1, total_rounds + 1):
            match_date = start_date + timedelta(days=((round_number - 1) // LEAGUE_MATCH_WINDOWS_PER_DAY))
            assignment = assignments_by_date[match_date]
            slot_index = (round_number - 1) % LEAGUE_MATCH_WINDOWS_PER_DAY
            round_schedule[round_number] = (
                match_date,
                assignment.windows[0],
                assignment.slot_sequences[slot_index],
            )

        return round_schedule

    def _build_single_round_pairings(
        self,
        registrations: Sequence[AcademyClubRegistration],
    ) -> list[list[tuple[AcademyClubRegistration, AcademyClubRegistration]]]:
        rotating = list(registrations)
        rounds: list[list[tuple[AcademyClubRegistration, AcademyClubRegistration]]] = []
        for round_index in range(len(rotating) - 1):
            left = rotating[: len(rotating) // 2]
            right = list(reversed(rotating[len(rotating) // 2 :]))
            matchups: list[tuple[AcademyClubRegistration, AcademyClubRegistration]] = []
            for pairing_index, (club_one, club_two) in enumerate(zip(left, right, strict=True)):
                if (round_index + pairing_index) % 2 == 0:
                    home, away = club_one, club_two
                else:
                    home, away = club_two, club_one
                matchups.append((home, away))
            rounds.append(matchups)
            rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
        return rounds

    def _normalize_results(
        self,
        *,
        fixtures: Sequence[AcademyFixture],
        results: Sequence[AcademyMatchResult],
    ) -> tuple[AcademyMatchResult, ...]:
        fixture_ids = {fixture.fixture_id for fixture in fixtures}
        normalized: dict[str, AcademyMatchResult] = {}
        for result in results:
            if result.fixture_id not in fixture_ids:
                raise AcademyValidationError(f"Result {result.fixture_id} does not match an academy fixture.")
            existing = normalized.get(result.fixture_id)
            if existing is not None and existing != result:
                raise AcademyValidationError(f"Fixture {result.fixture_id} received conflicting score submissions.")
            normalized[result.fixture_id] = result
        return tuple(normalized.values())

    def _build_standings(
        self,
        *,
        registrations: Sequence[AcademyClubRegistration],
        fixtures: Sequence[AcademyFixture],
        results: Sequence[AcademyMatchResult],
    ) -> tuple[AcademyStandingRow, ...]:
        rows = {
            club.club_id: AcademyStandingRow(
                club_id=club.club_id,
                club_name=club.club_name,
                senior_buy_in_tier=club.senior_buy_in_tier,
            )
            for club in registrations
        }
        fixtures_by_id = {fixture.fixture_id: fixture for fixture in fixtures}
        for result in results:
            fixture = fixtures_by_id[result.fixture_id]
            home_row = rows[fixture.home_club_id]
            away_row = rows[fixture.away_club_id]
            home_row.played += 1
            away_row.played += 1
            home_row.goals_for += result.home_goals
            home_row.goals_against += result.away_goals
            away_row.goals_for += result.away_goals
            away_row.goals_against += result.home_goals
            if result.home_goals > result.away_goals:
                home_row.wins += 1
                away_row.losses += 1
                home_row.points += 3
            elif result.home_goals < result.away_goals:
                away_row.wins += 1
                home_row.losses += 1
                away_row.points += 3
            else:
                home_row.draws += 1
                away_row.draws += 1
                home_row.points += 1
                away_row.points += 1
        ordered = sorted(
            rows.values(),
            key=lambda row: (-row.points, -(row.goals_for - row.goals_against), -row.goals_for, row.club_name, row.club_id),
        )
        direct_slots = self._academy_direct_slots()
        total_qualifiers = self._academy_total_qualifiers()
        for rank, row in enumerate(ordered, start=1):
            row.rank = rank
            row.goal_difference = row.goals_for - row.goals_against
            if rank <= direct_slots:
                row.qualification_status = QualificationStatus.DIRECT
            elif rank <= total_qualifiers:
                row.qualification_status = QualificationStatus.PLAYOFF
            else:
                row.qualification_status = QualificationStatus.ELIMINATED
            row.auto_enter_next_season = rank <= 4
        return tuple(ordered)

    def _build_qualification_entries(
        self,
        standings: Sequence[AcademyStandingRow],
    ) -> AcademyQualificationPlan:
        entries = tuple(
            AcademyQualificationEntry(
                club_id=row.club_id,
                club_name=row.club_name,
                league_rank=row.rank,
                senior_buy_in_tier=row.senior_buy_in_tier,
                status=row.qualification_status,
                next_season_auto_entry=row.auto_enter_next_season,
            )
            for row in standings
        )
        direct = tuple(entry for entry in entries if entry.status == QualificationStatus.DIRECT)
        playoff = tuple(entry for entry in entries if entry.status == QualificationStatus.PLAYOFF)
        eliminated = tuple(entry for entry in entries if entry.status == QualificationStatus.ELIMINATED)
        return AcademyQualificationPlan(
            entries=entries,
            direct_qualifiers=direct,
            playoff_qualifiers=playoff,
            eliminated_clubs=eliminated,
        )

    def _build_champions_league_flow(
        self,
        season_id: str,
        qualification: AcademyQualificationPlan,
    ) -> AcademyChampionsLeagueFlow:
        playoff_seeds = sorted(qualification.playoff_qualifiers, key=lambda entry: entry.league_rank)
        if len(playoff_seeds) != 4:
            raise AcademyValidationError("Academy Champions League playoff flow requires four playoff clubs.")
        playoff_ties = (
            self._build_knockout_tie(
                tie_id=f"{season_id}:acl:playoff:1",
                stage_name="qualification_playoff",
                home_club_id=playoff_seeds[0].club_id,
                home_club_name=playoff_seeds[0].club_name,
                home_seed=playoff_seeds[0].league_rank,
                away_club_id=playoff_seeds[3].club_id,
                away_club_name=playoff_seeds[3].club_name,
                away_seed=playoff_seeds[3].league_rank,
                presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
            ),
            self._build_knockout_tie(
                tie_id=f"{season_id}:acl:playoff:2",
                stage_name="qualification_playoff",
                home_club_id=playoff_seeds[1].club_id,
                home_club_name=playoff_seeds[1].club_name,
                home_seed=playoff_seeds[1].league_rank,
                away_club_id=playoff_seeds[2].club_id,
                away_club_name=playoff_seeds[2].club_name,
                away_seed=playoff_seeds[2].league_rank,
                presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
            ),
        )
        winners = tuple(
            next(club for club in playoff_seeds if club.club_id == tie.winner_club_id)
            for tie in playoff_ties
        )
        league_phase_clubs = tuple(sorted([*qualification.direct_qualifiers, *winners], key=lambda club: club.league_rank))
        league_phase_table = self._simulate_league_phase(league_phase_clubs)
        quarterfinals = (
            self._build_knockout_tie(
                tie_id=f"{season_id}:acl:quarterfinal:1",
                stage_name="quarterfinal",
                home_club_id=league_phase_table[2].club_id,
                home_club_name=league_phase_table[2].club_name,
                home_seed=league_phase_table[2].rank,
                away_club_id=league_phase_table[5].club_id,
                away_club_name=league_phase_table[5].club_name,
                away_seed=league_phase_table[5].rank,
                presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
            ),
            self._build_knockout_tie(
                tie_id=f"{season_id}:acl:quarterfinal:2",
                stage_name="quarterfinal",
                home_club_id=league_phase_table[3].club_id,
                home_club_name=league_phase_table[3].club_name,
                home_seed=league_phase_table[3].rank,
                away_club_id=league_phase_table[4].club_id,
                away_club_name=league_phase_table[4].club_name,
                away_seed=league_phase_table[4].rank,
                presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
            ),
        )
        semifinal_one = self._build_knockout_tie(
            tie_id=f"{season_id}:acl:semifinal:1",
            stage_name="semifinal",
            home_club_id=league_phase_table[0].club_id,
            home_club_name=league_phase_table[0].club_name,
            home_seed=league_phase_table[0].rank,
            away_club_id=quarterfinals[1].winner_club_id,
            away_club_name=quarterfinals[1].winner_club_name,
            away_seed=self._league_phase_rank(league_phase_table, quarterfinals[1].winner_club_id),
            presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
        )
        semifinal_two = self._build_knockout_tie(
            tie_id=f"{season_id}:acl:semifinal:2",
            stage_name="semifinal",
            home_club_id=league_phase_table[1].club_id,
            home_club_name=league_phase_table[1].club_name,
            home_seed=league_phase_table[1].rank,
            away_club_id=quarterfinals[0].winner_club_id,
            away_club_name=quarterfinals[0].winner_club_name,
            away_seed=self._league_phase_rank(league_phase_table, quarterfinals[0].winner_club_id),
            presentation_max_minutes=MATCH_PRESENTATION_MAX_MINUTES,
        )
        final = self._build_knockout_tie(
            tie_id=f"{season_id}:acl:final",
            stage_name="final",
            home_club_id=semifinal_one.winner_club_id,
            home_club_name=semifinal_one.winner_club_name,
            home_seed=self._league_phase_rank(league_phase_table, semifinal_one.winner_club_id),
            away_club_id=semifinal_two.winner_club_id,
            away_club_name=semifinal_two.winner_club_name,
            away_seed=self._league_phase_rank(league_phase_table, semifinal_two.winner_club_id),
            presentation_max_minutes=FINAL_PRESENTATION_MAX_MINUTES,
        )
        return AcademyChampionsLeagueFlow(
            qualification=qualification,
            playoff_ties=playoff_ties,
            league_phase_table=league_phase_table,
            quarterfinals=quarterfinals,
            semifinals=(semifinal_one, semifinal_two),
            final=final,
            champion_club_id=final.winner_club_id,
            champion_club_name=final.winner_club_name,
        )

    def _simulate_league_phase(
        self,
        clubs: Sequence[AcademyQualificationEntry],
    ) -> tuple[AcademyLeaguePhaseRow, ...]:
        rows = {
            club.club_id: AcademyLeaguePhaseRow(
                club_id=club.club_id,
                club_name=club.club_name,
                seed=club.league_rank,
            )
            for club in clubs
        }
        ordered_clubs = sorted(clubs, key=lambda club: club.league_rank)
        for home, away in combinations(ordered_clubs, 2):
            home_row = rows[home.club_id]
            away_row = rows[away.club_id]
            home_row.played += 1
            away_row.played += 1
            if away.league_rank - home.league_rank == 1:
                home_goals = 1
                away_goals = 1
                home_row.draws += 1
                away_row.draws += 1
                home_row.points += 1
                away_row.points += 1
            else:
                home_goals = 2
                away_goals = 1 if away.league_rank - home.league_rank == 2 else 0
                home_row.wins += 1
                away_row.losses += 1
                home_row.points += 3
            home_row.goals_for += home_goals
            home_row.goals_against += away_goals
            away_row.goals_for += away_goals
            away_row.goals_against += home_goals
        table = sorted(
            rows.values(),
            key=lambda row: (-row.points, -(row.goals_for - row.goals_against), -row.goals_for, row.seed, row.club_name),
        )
        for rank, row in enumerate(table, start=1):
            row.rank = rank
            row.goal_difference = row.goals_for - row.goals_against
        return tuple(table)

    def _build_knockout_tie(
        self,
        *,
        tie_id: str,
        stage_name: str,
        home_club_id: str,
        home_club_name: str,
        home_seed: int,
        away_club_id: str,
        away_club_name: str,
        away_seed: int,
        presentation_max_minutes: int,
    ) -> AcademyKnockoutTie:
        if home_seed <= away_seed:
            winner_club_id = home_club_id
            winner_club_name = home_club_name
        else:
            winner_club_id = away_club_id
            winner_club_name = away_club_name
        return AcademyKnockoutTie(
            tie_id=tie_id,
            stage_name=stage_name,
            home_club_id=home_club_id,
            home_club_name=home_club_name,
            away_club_id=away_club_id,
            away_club_name=away_club_name,
            winner_club_id=winner_club_id,
            winner_club_name=winner_club_name,
            is_cup_match=True,
            allow_penalties=True,
            extra_time_allowed=False,
            presentation_min_minutes=MATCH_PRESENTATION_MIN_MINUTES,
            presentation_max_minutes=presentation_max_minutes,
        )

    def _build_awards(
        self,
        registrations: Sequence[AcademyClubRegistration],
        standings: Sequence[AcademyStandingRow],
        leaders: AcademyAwardsLeaders | None,
    ) -> AcademyAwardsPreview:
        total_pool = self._quantize(sum((club.academy_buy_in for club in registrations), start=Decimal("0")))
        champion = standings[0]
        club_names = {club.club_id: club.club_name for club in registrations}
        scorer_club_id = leaders.top_scorer_club_id if leaders is not None else None
        assist_club_id = leaders.top_assist_club_id if leaders is not None else None
        scorer_club_id = scorer_club_id or champion.club_id
        assist_club_id = assist_club_id or champion.club_id
        if scorer_club_id not in club_names:
            raise AcademyValidationError(f"Unknown top scorer club {scorer_club_id}.")
        if assist_club_id not in club_names:
            raise AcademyValidationError(f"Unknown top assist club {assist_club_id}.")
        winner_share = self._percentage_amount(total_pool, LEAGUE_WINNER_PCT)
        scorer_share = self._percentage_amount(total_pool, TOP_SCORER_PCT)
        assist_share = self._percentage_amount(total_pool, TOP_ASSIST_PCT)
        champions_league_fund = self._percentage_amount(total_pool, CHAMPIONS_LEAGUE_FUND_PCT)
        return AcademyAwardsPreview(
            total_pool=total_pool,
            league_winner_share=winner_share,
            top_scorer_share=scorer_share,
            top_assist_share=assist_share,
            champions_league_fund_share=champions_league_fund,
            allocations=(
                AcademyAwardAllocation(
                    award_code="league_winner",
                    club_id=champion.club_id,
                    club_name=champion.club_name,
                    amount=winner_share,
                ),
                AcademyAwardAllocation(
                    award_code="top_scorer",
                    club_id=scorer_club_id,
                    club_name=club_names[scorer_club_id],
                    amount=scorer_share,
                ),
                AcademyAwardAllocation(
                    award_code="top_assist",
                    club_id=assist_club_id,
                    club_name=club_names[assist_club_id],
                    amount=assist_share,
                ),
                AcademyAwardAllocation(
                    award_code="champions_league_fund",
                    club_id=None,
                    club_name="Academy Champions League",
                    amount=champions_league_fund,
                ),
            ),
        )

    def _build_rollover_clubs(
        self,
        registrations: Sequence[AcademyClubRegistration],
        standings: Sequence[AcademyStandingRow],
    ) -> tuple[AcademyClubRegistration, ...]:
        registration_map = {club.club_id: club for club in registrations}
        return tuple(
            AcademyClubRegistration(
                club_id=registration_map[row.club_id].club_id,
                club_name=registration_map[row.club_id].club_name,
                senior_buy_in_tier=registration_map[row.club_id].senior_buy_in_tier,
                academy_buy_in=registration_map[row.club_id].academy_buy_in,
                carry_over_from_previous_season=True,
            )
            for row in standings[:4]
        )

    def _resolve_status(
        self,
        *,
        fixtures: Sequence[AcademyFixture],
        completed_fixture_count: int,
    ) -> AcademySeasonStatus:
        if not fixtures:
            return AcademySeasonStatus.REGISTRATION_OPEN
        if completed_fixture_count <= 0:
            return AcademySeasonStatus.FIXTURES_PUBLISHED
        if completed_fixture_count < len(fixtures):
            return AcademySeasonStatus.IN_PROGRESS
        return AcademySeasonStatus.COMPLETED

    def _validate_club_requests(self, clubs: Sequence[AcademyClubRegistrationRequest]) -> None:
        if len(clubs) != LEAGUE_GROUP_SIZE:
            raise AcademyValidationError(
                f"Academy league seasons require exactly {LEAGUE_GROUP_SIZE} clubs; received {len(clubs)}."
            )
        seen_ids: set[str] = set()
        for club in clubs:
            if not club.club_id:
                raise AcademyValidationError("Academy club ids must be non-empty.")
            if club.club_id in seen_ids:
                raise AcademyValidationError(f"Duplicate academy club id {club.club_id}.")
            if club.senior_buy_in_tier not in LEAGUE_BUY_IN_TIERS:
                raise AcademyValidationError(
                    f"Academy club {club.club_id} used unsupported senior buy-in tier {club.senior_buy_in_tier}."
                )
            seen_ids.add(club.club_id)

    def _academy_buy_in(self, senior_buy_in_tier: int) -> Decimal:
        return self._quantize(Decimal(senior_buy_in_tier) * Decimal(str(ACADEMY_BUY_IN_MULTIPLIER)))

    def _academy_direct_slots(self) -> int:
        return max(4, LEAGUE_GROUP_SIZE // 5)

    def _academy_total_qualifiers(self) -> int:
        direct_ratio = Decimal(CHAMPIONS_LEAGUE_DIRECT_SLOTS) / Decimal(CHAMPIONS_LEAGUE_TOTAL_QUALIFIERS)
        direct_slots = self._academy_direct_slots()
        total = int((Decimal(direct_slots) / direct_ratio).to_integral_value(rounding=ROUND_HALF_UP))
        if total % 2 != 0:
            total -= 1
        return max(direct_slots + 4, total)

    def _league_phase_rank(self, table: Sequence[AcademyLeaguePhaseRow], club_id: str) -> int:
        return next(row.rank for row in table if row.club_id == club_id)

    def _percentage_amount(self, total_pool: Decimal, percentage: float) -> Decimal:
        return self._quantize(total_pool * Decimal(str(percentage)))

    def _quantize(self, amount: Decimal) -> Decimal:
        return amount.quantize(_CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
