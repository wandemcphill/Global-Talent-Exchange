from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import ClassVar, Mapping, Sequence

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.ultimate_league.matchmaking_engine import (
    EloMatchmakingEngine,
    EloRatingUpdate,
    MatchmakingBatch,
    QueueCompetitor,
)
from app.ultimate_league.tournament_scheduler import (
    TournamentBracket,
    TournamentEntrant,
    TournamentScheduler,
)
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


class LeagueTier(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    LEGEND = "legend"


class UltimateLeagueError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LeagueTierDefinition:
    tier: LeagueTier
    label: str
    min_elo: int
    max_elo: int | None
    promotion_slots: int
    relegation_slots: int
    default_tournament_size: int


@dataclass(frozen=True, slots=True)
class LeagueCompetitor:
    competitor_id: str
    display_name: str
    elo_rating: int
    user_id: str | None = None
    wins: int = 0
    draws: int = 0
    losses: int = 0
    region: str | None = None
    queue_entered_at: datetime | None = None

    @property
    def matches_played(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def league_points(self) -> int:
        return (self.wins * 3) + self.draws

    @property
    def win_rate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return self.wins / self.matches_played


@dataclass(frozen=True, slots=True)
class LeagueStandingEntry:
    rank: int
    tier: LeagueTier
    competitor: LeagueCompetitor
    league_points: int
    matches_played: int
    win_rate: float
    zone: str


@dataclass(frozen=True, slots=True)
class GTexPrizePayout:
    tournament_id: str
    tier: LeagueTier
    placement: int
    competitor_id: str
    display_name: str
    amount: Decimal
    share_percentage: Decimal
    user_id: str | None = None
    unit: LedgerUnit = LedgerUnit.COIN
    source_tag: LedgerSourceTag = LedgerSourceTag.PLATFORM_COMPETITION_REWARD
    reason: LedgerEntryReason = LedgerEntryReason.COMPETITION_REWARD


@dataclass(frozen=True, slots=True)
class LeagueTournamentPlan:
    tournament_id: str
    tier: LeagueTier
    entrants: tuple[TournamentEntrant, ...]
    bracket: TournamentBracket
    recommended_payout_percentages: tuple[Decimal, ...]


@dataclass(slots=True)
class UltimateLeagueService:
    matchmaking_engine: EloMatchmakingEngine = field(default_factory=EloMatchmakingEngine)
    tournament_scheduler: TournamentScheduler = field(default_factory=TournamentScheduler)

    TIER_DEFINITIONS: ClassVar[tuple[LeagueTierDefinition, ...]] = (
        LeagueTierDefinition(LeagueTier.BRONZE, "Bronze", 0, 1200, promotion_slots=2, relegation_slots=0, default_tournament_size=16),
        LeagueTierDefinition(LeagueTier.SILVER, "Silver", 1200, 1400, promotion_slots=2, relegation_slots=2, default_tournament_size=16),
        LeagueTierDefinition(LeagueTier.GOLD, "Gold", 1400, 1600, promotion_slots=2, relegation_slots=2, default_tournament_size=8),
        LeagueTierDefinition(LeagueTier.PLATINUM, "Platinum", 1600, 1800, promotion_slots=2, relegation_slots=2, default_tournament_size=8),
        LeagueTierDefinition(LeagueTier.DIAMOND, "Diamond", 1800, 2000, promotion_slots=2, relegation_slots=2, default_tournament_size=8),
        LeagueTierDefinition(LeagueTier.MASTER, "Master", 2000, 2200, promotion_slots=2, relegation_slots=2, default_tournament_size=4),
        LeagueTierDefinition(LeagueTier.LEGEND, "Legend", 2200, None, promotion_slots=0, relegation_slots=2, default_tournament_size=4),
    )

    def tier_for_rating(self, elo_rating: int) -> LeagueTierDefinition:
        for definition in self.TIER_DEFINITIONS:
            if definition.max_elo is None or elo_rating < definition.max_elo:
                return definition
        return self.TIER_DEFINITIONS[-1]

    def build_tier_tables(
        self,
        competitors: Sequence[LeagueCompetitor],
    ) -> dict[LeagueTier, tuple[LeagueStandingEntry, ...]]:
        grouped: dict[LeagueTier, list[LeagueCompetitor]] = {definition.tier: [] for definition in self.TIER_DEFINITIONS}
        for competitor in competitors:
            grouped[self.tier_for_rating(competitor.elo_rating).tier].append(competitor)

        tables: dict[LeagueTier, tuple[LeagueStandingEntry, ...]] = {}
        for definition in self.TIER_DEFINITIONS:
            ordered = sorted(
                grouped[definition.tier],
                key=lambda competitor: (
                    -competitor.league_points,
                    -competitor.elo_rating,
                    -competitor.wins,
                    competitor.losses,
                    competitor.display_name.lower(),
                ),
            )
            rows: list[LeagueStandingEntry] = []
            for index, competitor in enumerate(ordered, start=1):
                zone = "safe"
                if definition.promotion_slots and index <= definition.promotion_slots:
                    zone = "promotion"
                if zone == "safe" and definition.relegation_slots and index > max(0, len(ordered) - definition.relegation_slots):
                    zone = "relegation"
                rows.append(
                    LeagueStandingEntry(
                        rank=index,
                        tier=definition.tier,
                        competitor=competitor,
                        league_points=competitor.league_points,
                        matches_played=competitor.matches_played,
                        win_rate=competitor.win_rate,
                        zone=zone,
                    )
                )
            tables[definition.tier] = tuple(rows)
        return tables

    def create_matchmaking_batch(
        self,
        competitors: Sequence[LeagueCompetitor],
        *,
        now: datetime | None = None,
        prefer_same_tier: bool = True,
    ) -> MatchmakingBatch:
        queue = tuple(
            QueueCompetitor(
                competitor_id=competitor.competitor_id,
                display_name=competitor.display_name,
                elo_rating=competitor.elo_rating,
                tier_key=self.tier_for_rating(competitor.elo_rating).tier.value,
                region=competitor.region,
                queue_entered_at=competitor.queue_entered_at,
            )
            for competitor in competitors
        )
        return self.matchmaking_engine.build_pairs(queue, now=now, prefer_same_tier=prefer_same_tier)

    def apply_match_result(
        self,
        *,
        home: LeagueCompetitor,
        away: LeagueCompetitor,
        home_score: int,
        away_score: int,
        importance: float = 1.0,
    ) -> tuple[LeagueCompetitor, LeagueCompetitor, EloRatingUpdate]:
        update = self.matchmaking_engine.record_match(
            home=QueueCompetitor(home.competitor_id, home.display_name, home.elo_rating),
            away=QueueCompetitor(away.competitor_id, away.display_name, away.elo_rating),
            home_score=home_score,
            away_score=away_score,
            importance=importance,
        )

        if home_score == away_score:
            updated_home = replace(home, elo_rating=update.home_new_rating, draws=home.draws + 1)
            updated_away = replace(away, elo_rating=update.away_new_rating, draws=away.draws + 1)
        elif home_score > away_score:
            updated_home = replace(home, elo_rating=update.home_new_rating, wins=home.wins + 1)
            updated_away = replace(away, elo_rating=update.away_new_rating, losses=away.losses + 1)
        else:
            updated_home = replace(home, elo_rating=update.home_new_rating, losses=home.losses + 1)
            updated_away = replace(away, elo_rating=update.away_new_rating, wins=away.wins + 1)
        return updated_home, updated_away, update

    def schedule_tier_tournament(
        self,
        *,
        tournament_id: str,
        tier: LeagueTier | str,
        competitors: Sequence[LeagueCompetitor],
        starts_at: datetime,
        field_size: int | None = None,
        round_spacing: timedelta | None = None,
        match_spacing: timedelta | None = None,
        parallel_matches: int | None = None,
    ) -> LeagueTournamentPlan:
        tier_enum = LeagueTier(tier)
        definition = self._tier_definition(tier_enum)
        tier_competitors = [competitor for competitor in competitors if self.tier_for_rating(competitor.elo_rating).tier == tier_enum]
        if len(tier_competitors) < 2:
            raise UltimateLeagueError(f"At least two {definition.label} competitors are required to schedule a tournament.")

        ordered = sorted(
            tier_competitors,
            key=lambda competitor: (
                -competitor.league_points,
                -competitor.elo_rating,
                -competitor.wins,
                competitor.display_name.lower(),
            ),
        )
        selected = ordered[: max(2, field_size or definition.default_tournament_size)]
        entrants = tuple(
            TournamentEntrant(
                competitor_id=competitor.competitor_id,
                display_name=competitor.display_name,
                elo_rating=competitor.elo_rating,
                seed=index,
                tier_key=tier_enum.value,
            )
            for index, competitor in enumerate(selected, start=1)
        )
        bracket = self.tournament_scheduler.build_single_elimination(
            tournament_id=tournament_id,
            entrants=entrants,
            starts_at=starts_at,
            round_spacing=round_spacing,
            match_spacing=match_spacing,
            parallel_matches=parallel_matches,
        )
        return LeagueTournamentPlan(
            tournament_id=tournament_id,
            tier=tier_enum,
            entrants=entrants,
            bracket=bracket,
            recommended_payout_percentages=self.default_payout_percentages(len(entrants)),
        )

    def default_payout_percentages(self, entrant_count: int) -> tuple[Decimal, ...]:
        if entrant_count <= 2:
            return (Decimal("1.0000"),)
        if entrant_count <= 4:
            return (
                Decimal("0.7000"),
                Decimal("0.3000"),
            )
        if entrant_count <= 8:
            return (
                Decimal("0.5500"),
                Decimal("0.2500"),
                Decimal("0.1200"),
                Decimal("0.0800"),
            )
        return (
            Decimal("0.3500"),
            Decimal("0.2000"),
            Decimal("0.1400"),
            Decimal("0.1000"),
            Decimal("0.0800"),
            Decimal("0.0600"),
            Decimal("0.0400"),
            Decimal("0.0300"),
        )

    def distribute_prize_pool(
        self,
        *,
        tournament_id: str,
        tier: LeagueTier | str,
        placements: Sequence[LeagueCompetitor],
        gross_pool_gtex: Decimal | int | float | str,
        entrant_count: int | None = None,
        payout_percentages: Sequence[Decimal | int | float | str] | None = None,
    ) -> tuple[GTexPrizePayout, ...]:
        if not placements:
            raise UltimateLeagueError("At least one placement is required to distribute prize payouts.")

        tier_enum = LeagueTier(tier)
        normalized_pool = self._normalize_amount(gross_pool_gtex)
        field_size = entrant_count or len(placements)
        normalized_percentages = self._normalize_percentages(
            payout_percentages or self.default_payout_percentages(field_size)
        )

        rewarded_placements = min(len(placements), len(normalized_percentages))
        if rewarded_placements == 0:
            return ()

        amounts = [
            (normalized_pool * normalized_percentages[index]).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
            for index in range(rewarded_placements)
        ]
        adjustment = normalized_pool - sum(amounts, start=Decimal("0.0000"))
        amounts[0] += adjustment

        payouts: list[GTexPrizePayout] = []
        for index in range(rewarded_placements):
            competitor = placements[index]
            payouts.append(
                GTexPrizePayout(
                    tournament_id=tournament_id,
                    tier=tier_enum,
                    placement=index + 1,
                    competitor_id=competitor.competitor_id,
                    display_name=competitor.display_name,
                    amount=amounts[index],
                    share_percentage=normalized_percentages[index],
                    user_id=competitor.user_id,
                )
            )
        return tuple(payouts)

    def apply_gtex_payouts(
        self,
        session: Session,
        *,
        payouts: Sequence[GTexPrizePayout],
        user_lookup: Mapping[str, User],
        wallet_service: WalletService | None = None,
        actor: User | None = None,
    ) -> list[LedgerEntry]:
        if not payouts:
            return []

        wallet = wallet_service or WalletService()
        promo_pool_account = wallet.ensure_promo_pool_account(session, LedgerUnit.COIN)
        entries: list[LedgerEntry] = []
        for payout in payouts:
            user = self._resolve_user_for_payout(payout, user_lookup)
            user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
            entries.extend(
                wallet.append_transaction(
                    session,
                    postings=[
                        LedgerPosting(account=user_account, amount=payout.amount, source_tag=payout.source_tag),
                        LedgerPosting(account=promo_pool_account, amount=-payout.amount, source_tag=payout.source_tag),
                    ],
                    reason=payout.reason,
                    source_tag=payout.source_tag,
                    reference=f"ultimate-league:{payout.tournament_id}:{payout.placement}",
                    description=f"Ultimate League {payout.tier.value.title()} placement payout",
                    actor=actor,
                )
            )
        return entries

    def _resolve_user_for_payout(self, payout: GTexPrizePayout, user_lookup: Mapping[str, User]) -> User:
        if payout.competitor_id in user_lookup:
            return user_lookup[payout.competitor_id]
        if payout.user_id and payout.user_id in user_lookup:
            return user_lookup[payout.user_id]
        raise UltimateLeagueError(
            f"Missing user mapping for payout recipient '{payout.competitor_id}'."
        )

    def _tier_definition(self, tier: LeagueTier) -> LeagueTierDefinition:
        for definition in self.TIER_DEFINITIONS:
            if definition.tier == tier:
                return definition
        raise UltimateLeagueError(f"Unknown league tier '{tier}'.")

    def _normalize_amount(self, value: Decimal | int | float | str) -> Decimal:
        amount = Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
        if amount <= Decimal("0.0000"):
            raise UltimateLeagueError("Prize pools must be greater than zero.")
        return amount

    def _normalize_percentages(
        self,
        percentages: Sequence[Decimal | int | float | str],
    ) -> tuple[Decimal, ...]:
        normalized = tuple(Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP) for value in percentages)
        total = sum(normalized, start=Decimal("0.0000"))
        if total == Decimal("100.0000"):
            normalized = tuple((value / Decimal("100")).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP) for value in normalized)
            total = sum(normalized, start=Decimal("0.0000"))
        if total != Decimal("1.0000"):
            raise UltimateLeagueError("Prize distribution percentages must sum to 1.0000 or 100.0000.")
        return normalized


__all__ = [
    "GTexPrizePayout",
    "LeagueCompetitor",
    "LeagueStandingEntry",
    "LeagueTier",
    "LeagueTierDefinition",
    "LeagueTournamentPlan",
    "UltimateLeagueError",
    "UltimateLeagueService",
]
