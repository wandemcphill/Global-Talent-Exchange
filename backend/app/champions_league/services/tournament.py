from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from hashlib import sha256

from app.champions_league.models.domain import (
    AdvancementStatus,
    ChampionsLeagueValidationError,
    ClubCandidate,
    ClubSeed,
    KnockoutBracket,
    KnockoutTie,
    LeagueMatchResult,
    LeaguePhaseTable,
    LeagueStandingRow,
    MatchStage,
    PlayoffBracket,
    PrizeSettlementPreview,
    QualificationMap,
    QualificationRegionSummary,
    QualificationStatus,
    QualifiedClub,
    SettlementEventPlan,
    TierAllocation,
)
from app.config.competition_constants import (
    CHAMPIONS_LEAGUE_DIRECT_SLOTS,
    CHAMPIONS_LEAGUE_FUND_PCT,
    CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS,
    CHAMPIONS_LEAGUE_PLATFORM_PCT,
    CHAMPIONS_LEAGUE_PLAYOFF_SLOTS,
    CHAMPIONS_LEAGUE_TOTAL_QUALIFIERS,
    CHAMPIONS_LEAGUE_WINNER_PCT,
    FINAL_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MAX_MINUTES,
)

_FOUR_PLACES = Decimal("0.0001")
_MATCH_FEE_SOURCE = "champions_league_match_fee"
# RewardSettlement.competition_key is 64 chars, and the ledger idempotency key
# also embeds that value. 45 keeps `reward-settlement:{key}:{user}:{source}` <= 128.
_MAX_COMPETITION_KEY_LEN = 45
_STAGE_BONUS_KEYS = ("round_of_16", "quarterfinal", "semifinal", "runner_up", "champion")


class RegionalQualificationService:
    def build(self, clubs: list[ClubCandidate]) -> QualificationMap:
        if len(clubs) < CHAMPIONS_LEAGUE_TOTAL_QUALIFIERS:
            raise ChampionsLeagueValidationError(
                f"Champions League qualification requires at least {CHAMPIONS_LEAGUE_TOTAL_QUALIFIERS} clubs"
            )

        unique_ids = {club.club_id for club in clubs}
        if len(unique_ids) != len(clubs):
            raise ChampionsLeagueValidationError("Club ids must be unique within qualification input")

        ordered_clubs = sorted(clubs, key=_candidate_sort_key)
        direct = self._select_stage(ordered_clubs, CHAMPIONS_LEAGUE_DIRECT_SLOTS, stage="direct")
        remaining = [club for club in ordered_clubs if club.club_id not in {entry.club_id for entry in direct[0]}]
        playoff = self._select_stage(remaining, CHAMPIONS_LEAGUE_PLAYOFF_SLOTS, stage="playoff")

        direct_qualifiers = [
            QualifiedClub(
                club_id=club.club_id,
                club_name=club.club_name,
                region=club.region,
                tier=club.tier,
                seed=index,
                status=QualificationStatus.DIRECT,
                display_color=_qualification_color(QualificationStatus.DIRECT),
            )
            for index, club in enumerate(direct[0], start=1)
        ]
        playoff_qualifiers = [
            QualifiedClub(
                club_id=club.club_id,
                club_name=club.club_name,
                region=club.region,
                tier=club.tier,
                seed=index,
                status=QualificationStatus.PLAYOFF,
                display_color=_qualification_color(QualificationStatus.PLAYOFF),
            )
            for index, club in enumerate(playoff[0], start=1)
        ]

        selected_ids = {club.club_id for club in direct_qualifiers + playoff_qualifiers}
        eliminated = [
            QualifiedClub(
                club_id=club.club_id,
                club_name=club.club_name,
                region=club.region,
                tier=club.tier,
                seed=0,
                status=QualificationStatus.ELIMINATED,
                display_color=_qualification_color(QualificationStatus.ELIMINATED),
            )
            for club in ordered_clubs
            if club.club_id not in selected_ids
        ]

        entries = [
            *direct_qualifiers,
            *playoff_qualifiers,
            *eliminated,
        ]
        return QualificationMap(
            entries=entries,
            direct_qualifiers=direct_qualifiers,
            playoff_qualifiers=playoff_qualifiers,
            tier_allocations=[*direct[1], *playoff[1]],
            region_summaries=_build_region_summaries(entries),
        )

    def _select_stage(
        self,
        clubs: list[ClubCandidate],
        slot_count: int,
        *,
        stage: str,
    ) -> tuple[list[ClubCandidate], list[TierAllocation]]:
        tier_buckets: dict[str, list[ClubCandidate]] = defaultdict(list)
        for club in clubs:
            tier_buckets[club.tier].append(club)

        if not tier_buckets:
            raise ChampionsLeagueValidationError(f"No clubs were available to fill the {stage} stage")

        weighted_total = sum(_tier_weight(tier) * len(bucket) for tier, bucket in tier_buckets.items())
        if weighted_total <= 0:
            raise ChampionsLeagueValidationError("Tier weighting failed because no weighted candidates were found")

        allocations: dict[str, int] = {tier: 0 for tier in tier_buckets}
        remainders: list[tuple[Decimal, int, str]] = []
        assigned = 0
        for tier, bucket in tier_buckets.items():
            raw_target = (Decimal(slot_count) * Decimal(_tier_weight(tier) * len(bucket))) / Decimal(weighted_total)
            whole = int(raw_target.to_integral_value(rounding=ROUND_DOWN))
            base = min(whole, len(bucket))
            allocations[tier] = base
            assigned += base
            remainders.append((raw_target - Decimal(whole), _tier_weight(tier), tier))

        remaining_slots = slot_count - assigned
        for _remainder, _weight, tier in sorted(remainders, key=lambda item: (item[0], item[1], item[2]), reverse=True):
            if remaining_slots <= 0:
                break
            if allocations[tier] >= len(tier_buckets[tier]):
                continue
            allocations[tier] += 1
            remaining_slots -= 1

        selected: list[ClubCandidate] = []
        for tier, bucket in sorted(tier_buckets.items()):
            stage_selection = bucket[: allocations[tier]]
            selected.extend(stage_selection)

        if remaining_slots > 0:
            selected_ids = {club.club_id for club in selected}
            spillover = [club for club in clubs if club.club_id not in selected_ids]
            selected.extend(spillover[:remaining_slots])
            for club in spillover[:remaining_slots]:
                allocations[club.tier] = allocations.get(club.tier, 0) + 1

        if len(selected) != slot_count:
            raise ChampionsLeagueValidationError(
                f"Expected {slot_count} clubs for the {stage} stage but selected {len(selected)}"
            )

        selected.sort(key=_candidate_sort_key)
        allocation_rows = [
            TierAllocation(stage=stage, tier=tier, slot_count=slot_total)
            for tier, slot_total in sorted(allocations.items())
            if slot_total > 0
        ]
        return selected, allocation_rows


class LeaguePhaseTableService:
    def build_table(
        self,
        clubs: list[ClubSeed],
        matches: list[LeagueMatchResult],
    ) -> LeaguePhaseTable:
        if len({club.club_id for club in clubs}) != len(clubs):
            raise ChampionsLeagueValidationError("League phase club ids must be unique")

        rows = {
            club.club_id: LeagueStandingRow(
                club_id=club.club_id,
                club_name=club.club_name,
                seed=club.seed,
            )
            for club in clubs
        }

        seen_matches: set[str] = set()
        for match in matches:
            if match.match_id in seen_matches:
                raise ChampionsLeagueValidationError(f"Duplicate league match id detected: {match.match_id}")
            seen_matches.add(match.match_id)
            if match.home_club_id == match.away_club_id:
                raise ChampionsLeagueValidationError("A club cannot play itself in league phase input")
            if match.home_club_id not in rows or match.away_club_id not in rows:
                raise ChampionsLeagueValidationError("All league matches must reference known league phase clubs")
            if match.home_goals < 0 or match.away_goals < 0:
                raise ChampionsLeagueValidationError("League match goals cannot be negative")

            home = rows[match.home_club_id]
            away = rows[match.away_club_id]

            home.played += 1
            away.played += 1
            home.goals_for += match.home_goals
            home.goals_against += match.away_goals
            away.goals_for += match.away_goals
            away.goals_against += match.home_goals

            if match.home_goals > match.away_goals:
                home.wins += 1
                home.points += 3
                away.losses += 1
            elif match.home_goals < match.away_goals:
                away.wins += 1
                away.points += 3
                home.losses += 1
            else:
                home.draws += 1
                away.draws += 1
                home.points += 1
                away.points += 1

            if home.played > 6 or away.played > 6:
                raise ChampionsLeagueValidationError("League phase clubs cannot exceed six matches")

        ordered_rows = sorted(
            rows.values(),
            key=lambda row: (-row.points, -(row.goals_for - row.goals_against), -row.goals_for, -row.wins, row.seed),
        )
        ranked_rows: list[LeagueStandingRow] = []
        for index, row in enumerate(ordered_rows, start=1):
            row.goal_difference = row.goals_for - row.goals_against
            row.rank = index
            if index <= 8:
                row.advancement_status = AdvancementStatus.ROUND_OF_16
            elif index <= 24:
                row.advancement_status = AdvancementStatus.KNOCKOUT_PLAYOFF
            else:
                row.advancement_status = AdvancementStatus.ELIMINATED
            ranked_rows.append(row)

        is_complete = bool(ranked_rows) and all(row.played == 6 for row in ranked_rows)
        return LeaguePhaseTable(rows=ranked_rows, is_complete=is_complete)


class KnockoutBracketService:
    def build_qualification_playoff(
        self,
        qualification_map: QualificationMap,
        winner_overrides: dict[str, str] | None = None,
    ) -> PlayoffBracket:
        winner_overrides = winner_overrides or {}
        playoff_ties = self._pair_seeds(
            stage=MatchStage.QUALIFICATION_PLAYOFF,
            seeds=[
                ClubSeed(
                    club_id=club.club_id, club_name=club.club_name, seed=club.seed, region=club.region, tier=club.tier
                )
                for club in qualification_map.playoff_qualifiers
            ],
            winner_overrides=winner_overrides,
        )
        advancing = [
            ClubSeed(
                club_id=club.club_id,
                club_name=club.club_name,
                seed=index,
                region=club.region,
                tier=club.tier,
            )
            for index, club in enumerate(
                [
                    *qualification_map.direct_qualifiers,
                    *[tie.winner for tie in playoff_ties],
                ],
                start=1,
            )
        ]
        return PlayoffBracket(
            qualification=qualification_map,
            ties=playoff_ties,
            advancing_clubs=advancing,
        )

    def build_knockout_bracket(
        self,
        standings: list[LeagueStandingRow],
        *,
        knockout_playoff_winners: dict[str, str] | None = None,
        round_of_16_winners: dict[str, str] | None = None,
        quarterfinal_winners: dict[str, str] | None = None,
        semifinal_winners: dict[str, str] | None = None,
        final_winner: dict[str, str] | None = None,
    ) -> KnockoutBracket:
        if len(standings) < CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS:
            raise ChampionsLeagueValidationError(
                f"Knockout generation requires {CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS} league phase rows"
            )

        ordered = sorted(standings, key=lambda row: row.rank)
        top_eight = [_standing_to_seed(row) for row in ordered[:8]]
        knockout_playoff_pool = [_standing_to_seed(row) for row in ordered[8:24]]
        if len(knockout_playoff_pool) != 16:
            raise ChampionsLeagueValidationError("Knockout playoff generation requires ranks 9 through 24")

        knockout_playoff = self._pair_seeds(
            stage=MatchStage.KNOCKOUT_PLAYOFF,
            seeds=knockout_playoff_pool,
            winner_overrides=knockout_playoff_winners or {},
        )

        round_of_16_pairs = [
            (top_eight[0], knockout_playoff[7].winner),
            (top_eight[1], knockout_playoff[6].winner),
            (top_eight[2], knockout_playoff[5].winner),
            (top_eight[3], knockout_playoff[4].winner),
            (top_eight[4], knockout_playoff[3].winner),
            (top_eight[5], knockout_playoff[2].winner),
            (top_eight[6], knockout_playoff[1].winner),
            (top_eight[7], knockout_playoff[0].winner),
        ]
        round_of_16 = self._build_round(
            MatchStage.ROUND_OF_16,
            round_of_16_pairs,
            round_of_16_winners or {},
        )

        quarterfinals = self._build_round(
            MatchStage.QUARTERFINAL,
            [
                (round_of_16[0].winner, round_of_16[1].winner),
                (round_of_16[2].winner, round_of_16[3].winner),
                (round_of_16[4].winner, round_of_16[5].winner),
                (round_of_16[6].winner, round_of_16[7].winner),
            ],
            quarterfinal_winners or {},
        )
        semifinals = self._build_round(
            MatchStage.SEMIFINAL,
            [
                (quarterfinals[0].winner, quarterfinals[1].winner),
                (quarterfinals[2].winner, quarterfinals[3].winner),
            ],
            semifinal_winners or {},
        )
        final = self._build_round(
            MatchStage.FINAL,
            [(semifinals[0].winner, semifinals[1].winner)],
            final_winner or {},
        )[0]
        return KnockoutBracket(
            knockout_playoff=knockout_playoff,
            round_of_16=round_of_16,
            quarterfinals=quarterfinals,
            semifinals=semifinals,
            final=final,
            champion=final.winner,
        )

    def _pair_seeds(
        self,
        *,
        stage: MatchStage,
        seeds: list[ClubSeed],
        winner_overrides: dict[str, str],
    ) -> list[KnockoutTie]:
        ordered = sorted(seeds, key=lambda seed: seed.seed)
        pairings = list(zip(ordered[: len(ordered) // 2], reversed(ordered[len(ordered) // 2 :])))
        return self._build_round(stage, pairings, winner_overrides)

    def _build_round(
        self,
        stage: MatchStage,
        pairings: list[tuple[ClubSeed, ClubSeed]],
        winner_overrides: dict[str, str],
    ) -> list[KnockoutTie]:
        ties: list[KnockoutTie] = []
        for index, (home_club, away_club) in enumerate(pairings, start=1):
            tie_id = f"{stage.value}-{index:02d}"
            winner = _select_winner(home_club, away_club, winner_overrides.get(tie_id))
            ties.append(
                KnockoutTie(
                    tie_id=tie_id,
                    stage=stage,
                    home_club=home_club,
                    away_club=away_club,
                    winner=winner,
                    penalties_if_tied=True,
                    extra_time_allowed=False,
                    presentation_max_minutes=(
                        FINAL_PRESENTATION_MAX_MINUTES if stage is MatchStage.FINAL else MATCH_PRESENTATION_MAX_MINUTES
                    ),
                )
            )
        return ties


class PrizePoolService:
    def preview(
        self,
        *,
        season_id: str,
        league_leftover_allocation: Decimal,
        champion_club_id: str | None,
        champion_club_name: str | None,
        currency: str,
    ) -> PrizeSettlementPreview:
        if league_leftover_allocation < 0:
            raise ChampionsLeagueValidationError("League leftover allocation cannot be negative")

        funded_pool = _money(league_leftover_allocation * Decimal(str(CHAMPIONS_LEAGUE_FUND_PCT)))
        champion_share = _money(funded_pool * Decimal(str(CHAMPIONS_LEAGUE_WINNER_PCT)))
        platform_share = _money(funded_pool * Decimal(str(CHAMPIONS_LEAGUE_PLATFORM_PCT)))

        events = [
            SettlementEventPlan(
                event_key=f"{season_id}:champions-league:funded",
                event_type="champions_league.prize_pool_funded",
                aggregate_id=season_id,
                amount=funded_pool,
                currency=currency,
                payload={
                    "season_id": season_id,
                    "recipient": "champions_league_pool",
                },
            ),
            SettlementEventPlan(
                event_key=f"{season_id}:champions-league:champion-award",
                event_type="champions_league.champion_awarded",
                aggregate_id=season_id,
                amount=champion_share,
                currency=currency,
                payload={
                    "season_id": season_id,
                    "champion_club_id": champion_club_id or "pending",
                    "champion_club_name": champion_club_name or "pending",
                },
            ),
            SettlementEventPlan(
                event_key=f"{season_id}:champions-league:platform-share",
                event_type="champions_league.platform_awarded",
                aggregate_id=season_id,
                amount=platform_share,
                currency=currency,
                payload={
                    "season_id": season_id,
                    "recipient": "platform",
                },
            ),
        ]
        return PrizeSettlementPreview(
            season_id=season_id,
            champion_club_id=champion_club_id,
            champion_club_name=champion_club_name,
            league_leftover_allocation=_money(league_leftover_allocation),
            funded_pool=funded_pool,
            champion_share=champion_share,
            platform_share=platform_share,
            currency=currency,
            events=events,
            match_fee_schedule=_champions_league_match_fees(),
        )


class ChampionsLeagueService:
    def __init__(self) -> None:
        self.qualification = RegionalQualificationService()
        self.league_phase = LeaguePhaseTableService()
        self.knockout = KnockoutBracketService()
        self.prize_pool = PrizePoolService()

    def build_qualification_map(self, clubs: list[ClubCandidate]) -> QualificationMap:
        return self.qualification.build(clubs)

    def build_playoff_bracket(
        self,
        clubs: list[ClubCandidate],
        *,
        winner_overrides: dict[str, str] | None = None,
    ) -> PlayoffBracket:
        qualification_map = self.build_qualification_map(clubs)
        return self.knockout.build_qualification_playoff(
            qualification_map,
            winner_overrides=winner_overrides,
        )

    def build_league_phase_table(
        self,
        clubs: list[ClubSeed],
        matches: list[LeagueMatchResult],
    ) -> LeaguePhaseTable:
        if len(clubs) != CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS:
            raise ChampionsLeagueValidationError(
                f"Champions League league phase requires {CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS} clubs"
            )
        return self.league_phase.build_table(clubs, matches)

    def build_knockout_bracket(
        self,
        standings: list[LeagueStandingRow],
        *,
        knockout_playoff_winners: dict[str, str] | None = None,
        round_of_16_winners: dict[str, str] | None = None,
        quarterfinal_winners: dict[str, str] | None = None,
        semifinal_winners: dict[str, str] | None = None,
        final_winner: dict[str, str] | None = None,
    ) -> KnockoutBracket:
        if len(standings) != CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS:
            raise ChampionsLeagueValidationError(
                f"Champions League knockout seeding requires {CHAMPIONS_LEAGUE_LEAGUE_PHASE_TEAMS} standings rows"
            )
        return self.knockout.build_knockout_bracket(
            standings,
            knockout_playoff_winners=knockout_playoff_winners,
            round_of_16_winners=round_of_16_winners,
            quarterfinal_winners=quarterfinal_winners,
            semifinal_winners=semifinal_winners,
            final_winner=final_winner,
        )

    def build_prize_pool_preview(
        self,
        *,
        season_id: str,
        league_leftover_allocation: Decimal,
        champion_club_id: str | None,
        champion_club_name: str | None,
        currency: str = "credit",
    ) -> PrizeSettlementPreview:
        return self.prize_pool.preview(
            season_id=season_id,
            league_leftover_allocation=league_leftover_allocation,
            champion_club_id=champion_club_id,
            champion_club_name=champion_club_name,
            currency=currency,
        )

    def plan_match_fees(
        self,
        *,
        season_id: str,
        matches: list[LeagueMatchResult],
        stage_reached: dict[str, str] | None = None,
    ) -> list[SettlementEventPlan]:
        """Per-club win, draw, loss, and round coin. This does not change the champion pool."""
        return _plan_champions_league_match_fees(
            season_id=season_id,
            matches=matches,
            stage_reached=stage_reached,
        )

    def remember_played_match(
        self,
        *,
        session,
        season_id: str,
        match: LeagueMatchResult,
        club_user_ids: dict[str, str],
        stage_reached: dict[str, str] | None = None,
    ):
        """Store the result before coin is paid. A failed payment leaves the row owed."""
        from sqlalchemy import select

        from app.models.champions_league_played_match import ChampionsLeaguePlayedMatch

        row = session.scalar(
            select(ChampionsLeaguePlayedMatch).where(
                ChampionsLeaguePlayedMatch.season_id == season_id,
                ChampionsLeaguePlayedMatch.match_id == match.match_id,
            )
        )
        stage = {str(club_id): str(name) for club_id, name in dict(stage_reached or {}).items()}
        users = {str(club_id): str(user_id) for club_id, user_id in club_user_ids.items() if user_id}
        if row is None:
            row = ChampionsLeaguePlayedMatch(
                season_id=season_id,
                match_id=match.match_id,
                home_club_id=match.home_club_id,
                away_club_id=match.away_club_id,
                home_goals=int(match.home_goals),
                away_goals=int(match.away_goals),
                stage_reached=stage,
                club_user_ids=users,
                fee_status="owed",
            )
            session.add(row)
        else:
            row.home_club_id = match.home_club_id
            row.away_club_id = match.away_club_id
            row.home_goals = int(match.home_goals)
            row.away_goals = int(match.away_goals)
            if stage:
                row.stage_reached = {**dict(row.stage_reached or {}), **stage}
            if users:
                row.club_user_ids = {**dict(row.club_user_ids or {}), **users}
        session.flush()
        return row

    def record_match_and_pay(
        self,
        *,
        session,
        actor,
        season_id: str,
        match: LeagueMatchResult,
        club_user_ids: dict[str, str],
        stage_reached: dict[str, str] | None = None,
        stage_name: str | None = None,
        is_final: bool = False,
        winner_club_id: str | None = None,
    ) -> list:
        """Store this result, pay any owed results, then pay this match.

        The same match pays once. A later match pays again. Qualification coin
        uses one key per club per season, so two matches cannot both attach it.
        If payment fails, the stored row stays owed and this method raises.
        """
        from sqlalchemy import select

        from app.models.champions_league_played_match import ChampionsLeaguePlayedMatch

        if stage_reached is None:
            resolved_stage = _stage_reached_from_fixture(
                match=match,
                stage_name=stage_name,
                is_final=is_final,
                winner_club_id=winner_club_id,
            )
        else:
            resolved_stage = stage_reached
        current = self.remember_played_match(
            session=session,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
            stage_reached=resolved_stage,
        )
        owed = list(
            session.scalars(
                select(ChampionsLeaguePlayedMatch).where(
                    ChampionsLeaguePlayedMatch.season_id == season_id,
                    ChampionsLeaguePlayedMatch.fee_status == "owed",
                    ChampionsLeaguePlayedMatch.match_id != match.match_id,
                )
            ).all()
        )
        settled: list = []
        for row in owed:
            settled.extend(self._settle_played_row(session=session, actor=actor, season_id=season_id, row=row))
            row.fee_status = "settled"
        settled.extend(
            self.settle_match_fees(
                session=session,
                actor=actor,
                season_id=season_id,
                matches=[match],
                club_user_ids=club_user_ids,
                stage_reached=resolved_stage or None,
            )
        )
        current.fee_status = "settled"
        session.flush()
        return settled

    def _settle_played_row(self, *, session, actor, season_id: str, row) -> list:
        stored_match = LeagueMatchResult(
            match_id=row.match_id,
            home_club_id=row.home_club_id,
            away_club_id=row.away_club_id,
            home_goals=int(row.home_goals),
            away_goals=int(row.away_goals),
        )
        return self.settle_match_fees(
            session=session,
            actor=actor,
            season_id=season_id,
            matches=[stored_match],
            club_user_ids={str(club_id): str(user_id) for club_id, user_id in dict(row.club_user_ids or {}).items()},
            stage_reached={str(club_id): str(name) for club_id, name in dict(row.stage_reached or {}).items()} or None,
        )

    def settle_match_fees(
        self,
        *,
        session,
        actor,
        season_id: str,
        matches: list[LeagueMatchResult],
        club_user_ids: dict[str, str],
        stage_reached: dict[str, str] | None = None,
    ) -> list:
        """Credit each club owner from the promo pool.

        Each match has its own competition key, so a later match in the season
        still pays. Repeating a match returns the existing settlements.
        Qualification coin is paid once per club per season. The deepest stage
        bonus is topped up to the single stage amount, not summed across rounds.
        """
        from app.models.wallet import LedgerUnit
        from app.reward_engine.service import RewardEngineService

        # Keeps the aggregate fee schedule on the same path as plan_match_fees.
        self.plan_match_fees(season_id=season_id, matches=matches, stage_reached=stage_reached)
        fees = _champions_league_match_fees()
        qualification = Decimal(fees["qualification_guaranteed_coin"])
        win_coin = Decimal(fees["win"])
        draw_coin = Decimal(fees["draw"])
        loss_coin = Decimal(fees["loss"])
        engine = RewardEngineService(session)
        settled = []
        seen_clubs: set[str] = set()
        for match in _dedupe_matches(matches):
            for club_id, goals, opponent_goals in (
                (match.home_club_id, match.home_goals, match.away_goals),
                (match.away_club_id, match.away_goals, match.home_goals),
            ):
                user_id = club_user_ids.get(club_id)
                if not user_id:
                    continue
                if club_id not in seen_clubs:
                    seen_clubs.add(club_id)
                    settled.append(
                        engine.settle_reward(
                            actor=actor,
                            user_id=user_id,
                            competition_key=_qualification_competition_key(season_id, club_id),
                            title=f"Champions League qualification {club_id}",
                            gross_amount=qualification.quantize(_FOUR_PLACES),
                            reward_source=_MATCH_FEE_SOURCE,
                            note=f"kind=qualification;season={season_id};club={club_id};qualification=1",
                            ledger_unit=LedgerUnit.COIN,
                        )
                    )
                if goals > opponent_goals:
                    coin, wins, draws, losses = win_coin, 1, 0, 0
                elif goals == opponent_goals:
                    coin, wins, draws, losses = draw_coin, 0, 1, 0
                else:
                    coin, wins, draws, losses = loss_coin, 0, 0, 1
                amount = coin.quantize(_FOUR_PLACES)
                if amount <= 0:
                    continue
                settled.append(
                    engine.settle_reward(
                        actor=actor,
                        user_id=user_id,
                        competition_key=_match_fee_competition_key(season_id, match.match_id, club_id),
                        title=f"Champions League match fee {match.match_id} {club_id}",
                        gross_amount=amount,
                        reward_source=_MATCH_FEE_SOURCE,
                        note=(
                            f"kind=match;season={season_id};club={club_id};match={match.match_id};"
                            f"qualification=0;"
                            f"{wins} wins, {draws} draws, {losses} losses"
                        ),
                        ledger_unit=LedgerUnit.COIN,
                    )
                )
        settled.extend(
            _settle_stage_bonuses(
                engine,
                actor=actor,
                season_id=season_id,
                club_user_ids=club_user_ids,
                stage_reached=stage_reached or {},
                fees=fees,
            )
        )
        return settled


def _candidate_sort_key(club: ClubCandidate) -> tuple[int, int, str, str]:
    return (-club.ranking_points, club.domestic_rank, club.region, club.club_id)


def _champions_league_match_fees() -> dict[str, str]:
    from app.national_team_engine.competition_profiles import default_reward_structure_for

    reward = default_reward_structure_for("world_cup", "senior")
    per_match = dict(reward["per_match_coin"])
    stages = dict(reward["stage_progression_coin"])
    return {
        "reward_mode": "match_and_stage",
        "qualification_guaranteed_coin": str(reward["qualification_guaranteed_coin"]),
        "win": str(per_match["win"]),
        "draw": str(per_match["draw"]),
        "loss": str(per_match["loss"]),
        "round_of_16": str(stages.get("round_of_16", "0.0000")),
        "quarterfinal": str(stages.get("quarterfinal", "0.0000")),
        "semifinal": str(stages.get("semifinal", "0.0000")),
        "runner_up": str(stages.get("runner_up", "0.0000")),
        "champion": str(stages.get("champion", "0.0000")),
    }


def _plan_champions_league_match_fees(
    *,
    season_id: str,
    matches: list[LeagueMatchResult],
    stage_reached: dict[str, str] | None = None,
) -> list[SettlementEventPlan]:
    fees = _champions_league_match_fees()
    qualification = Decimal(fees["qualification_guaranteed_coin"])
    win_coin = Decimal(fees["win"])
    draw_coin = Decimal(fees["draw"])
    loss_coin = Decimal(fees["loss"])
    totals: dict[str, dict[str, Decimal | int]] = {}
    for match in matches:
        for club_id, goals, opponent_goals in (
            (match.home_club_id, match.home_goals, match.away_goals),
            (match.away_club_id, match.away_goals, match.home_goals),
        ):
            row = totals.setdefault(
                club_id,
                {"wins": 0, "draws": 0, "losses": 0, "coin": qualification},
            )
            if goals > opponent_goals:
                row["wins"] = int(row["wins"]) + 1
                row["coin"] = Decimal(row["coin"]) + win_coin
            elif goals == opponent_goals:
                row["draws"] = int(row["draws"]) + 1
                row["coin"] = Decimal(row["coin"]) + draw_coin
            else:
                row["losses"] = int(row["losses"]) + 1
                row["coin"] = Decimal(row["coin"]) + loss_coin
    reached = stage_reached or {}
    plans: list[SettlementEventPlan] = []
    for club_id, row in sorted(totals.items()):
        stage = str(reached.get(club_id) or "")
        stage_coin = Decimal(fees[stage]) if stage in fees else Decimal("0")
        amount = (Decimal(row["coin"]) + stage_coin).quantize(_FOUR_PLACES)
        plans.append(
            SettlementEventPlan(
                event_key=f"{season_id}:champions-league:match-fee:{club_id}",
                event_type="champions_league.match_fee",
                aggregate_id=season_id,
                amount=amount,
                currency="coin",
                payload={
                    "season_id": season_id,
                    "club_id": club_id,
                    "wins": str(row["wins"]),
                    "draws": str(row["draws"]),
                    "losses": str(row["losses"]),
                    "stage": stage,
                },
            )
        )
    return plans


def _dedupe_matches(matches: list[LeagueMatchResult]) -> list[LeagueMatchResult]:
    order: list[str] = []
    by_id: dict[str, LeagueMatchResult] = {}
    for match in matches:
        if match.match_id not in by_id:
            order.append(match.match_id)
        by_id[match.match_id] = match
    return [by_id[match_id] for match_id in order]


def _bounded_competition_key(visible: str, raw: str) -> str:
    if len(raw) <= _MAX_COMPETITION_KEY_LEN:
        return raw
    digest = sha256(raw.encode("utf-8")).hexdigest()[:16]
    room = _MAX_COMPETITION_KEY_LEN - len("cl:") - 1 - len(digest)
    fragment = visible[:room] if room > 0 else ""
    if fragment:
        return f"cl:{fragment}:{digest}"[:_MAX_COMPETITION_KEY_LEN]
    return f"cl:{digest}"[:_MAX_COMPETITION_KEY_LEN]


def _match_fee_competition_key(season_id: str, match_id: str, club_id: str) -> str:
    return _bounded_competition_key(match_id, f"{season_id}:cl:{match_id}:{club_id}")


def _qualification_competition_key(season_id: str, club_id: str) -> str:
    return _bounded_competition_key(club_id, f"{season_id}:cl:qual:{club_id}")


def _stage_bonus_competition_key(season_id: str, club_id: str, stage: str) -> str:
    return _bounded_competition_key(stage, f"{season_id}:cl:stg:{club_id}:{stage}")


def _stage_coin_already_paid(session, *, season_id: str, club_id: str) -> Decimal:
    from sqlalchemy import select

    from app.models.reward_settlement import RewardSettlement

    prefix = f"kind=stage;season={season_id};club={club_id};"
    notes = session.scalars(
        select(RewardSettlement.note).where(
            RewardSettlement.reward_source == _MATCH_FEE_SOURCE,
            RewardSettlement.note.like("kind=stage;%"),
        )
    ).all()
    paid = Decimal("0")
    for note in notes:
        if not note or not note.startswith(prefix):
            continue
        marker = "amount="
        index = note.rfind(marker)
        if index < 0:
            continue
        raw = note[index + len(marker) :].split(";", 1)[0]
        try:
            paid += Decimal(raw)
        except InvalidOperation:
            continue
    return paid.quantize(_FOUR_PLACES)


def _settle_stage_bonuses(
    engine,
    *,
    actor,
    season_id: str,
    club_user_ids: dict[str, str],
    stage_reached: dict[str, str],
    fees: dict[str, str],
) -> list:
    from app.models.wallet import LedgerUnit

    settled = []
    for club_id, raw_stage in stage_reached.items():
        user_id = club_user_ids.get(club_id)
        stage = str(raw_stage or "").strip().lower()
        if not user_id or stage not in _STAGE_BONUS_KEYS or stage not in fees:
            continue
        target = Decimal(fees[stage]).quantize(_FOUR_PLACES)
        paid = _stage_coin_already_paid(engine.session, season_id=season_id, club_id=club_id)
        delta = (target - paid).quantize(_FOUR_PLACES)
        if delta <= 0:
            continue
        settled.append(
            engine.settle_reward(
                actor=actor,
                user_id=user_id,
                competition_key=_stage_bonus_competition_key(season_id, club_id, stage),
                title=f"Champions League {stage} bonus for {club_id}",
                gross_amount=delta,
                reward_source=_MATCH_FEE_SOURCE,
                note=(f"kind=stage;season={season_id};club={club_id};stage={stage};amount={delta}"),
                ledger_unit=LedgerUnit.COIN,
            )
        )
    return settled


def _stage_reached_from_fixture(
    *,
    match: LeagueMatchResult,
    stage_name: str | None,
    is_final: bool,
    winner_club_id: str | None,
) -> dict[str, str]:
    stage = (stage_name or "").strip().lower()
    home = match.home_club_id
    away = match.away_club_id
    if is_final or stage == "final":
        winner = winner_club_id
        if winner == home:
            return {home: "champion", away: "runner_up"}
        if winner == away:
            return {away: "champion", home: "runner_up"}
        if match.home_goals > match.away_goals:
            return {home: "champion", away: "runner_up"}
        if match.away_goals > match.home_goals:
            return {away: "champion", home: "runner_up"}
        return {}
    if stage in _STAGE_BONUS_KEYS and stage not in {"runner_up", "champion"}:
        return {home: stage, away: stage}
    return {}


def _qualification_color(status: QualificationStatus) -> str:
    if status is QualificationStatus.DIRECT:
        return "emerald"
    if status is QualificationStatus.PLAYOFF:
        return "amber"
    return "slate"


def _tier_weight(tier: str) -> int:
    normalized = tier.strip().lower().replace(" ", "_")
    if normalized in {"tier_1", "elite", "platinum", "legacy"}:
        return 4
    if normalized in {"tier_2", "challenger", "gold"}:
        return 3
    if normalized in {"tier_3", "contender", "silver"}:
        return 2
    return 1


def _build_region_summaries(entries: list[QualifiedClub]) -> list[QualificationRegionSummary]:
    summary: dict[str, dict[QualificationStatus, int]] = defaultdict(lambda: defaultdict(int))
    for entry in entries:
        summary[entry.region][entry.status] += 1
    return [
        QualificationRegionSummary(
            region=region,
            direct_count=counts[QualificationStatus.DIRECT],
            playoff_count=counts[QualificationStatus.PLAYOFF],
            eliminated_count=counts[QualificationStatus.ELIMINATED],
        )
        for region, counts in sorted(summary.items())
    ]


def _standing_to_seed(row: LeagueStandingRow) -> ClubSeed:
    return ClubSeed(
        club_id=row.club_id,
        club_name=row.club_name,
        seed=row.rank,
    )


def _select_winner(home_club: ClubSeed, away_club: ClubSeed, override: str | None) -> ClubSeed:
    if override is not None:
        if override == home_club.club_id:
            return home_club
        if override == away_club.club_id:
            return away_club
        raise ChampionsLeagueValidationError(
            f"Winner override {override} does not belong to tie between {home_club.club_id} and {away_club.club_id}"
        )
    return home_club if home_club.seed <= away_club.seed else away_club


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(_FOUR_PLACES)
