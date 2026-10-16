from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

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
            seeds=[ClubSeed(club_id=club.club_id, club_name=club.club_name, seed=club.seed, region=club.region, tier=club.tier) for club in qualification_map.playoff_qualifiers],
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
                    presentation_max_minutes=FINAL_PRESENTATION_MAX_MINUTES if stage is MatchStage.FINAL else MATCH_PRESENTATION_MAX_MINUTES,
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


def _candidate_sort_key(club: ClubCandidate) -> tuple[int, int, str, str]:
    return (-club.ranking_points, club.domestic_rank, club.region, club.club_id)


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
