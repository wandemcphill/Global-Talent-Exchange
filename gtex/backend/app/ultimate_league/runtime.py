from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Sequence
from uuid import uuid4

from app.ultimate_league.league_service import (
    GTexPrizePayout,
    LeagueCompetitor,
    LeagueStandingEntry,
    TacticalPresetListing,
    LeagueTier,
    LeagueTierDefinition,
    LeagueTournamentPlan,
    UltimateLeagueError,
    UltimateLeagueService,
)
from app.ultimate_league.matchmaking_engine import MatchmakingBatch


class UltimateLeagueNotFoundError(UltimateLeagueError):
    pass


@dataclass(slots=True)
class UltimateLeagueRuntime:
    service: UltimateLeagueService = field(default_factory=UltimateLeagueService)
    competitors: dict[str, LeagueCompetitor] = field(default_factory=dict)
    tournaments: dict[str, LeagueTournamentPlan] = field(default_factory=dict)
    tactical_presets: dict[str, TacticalPresetListing] = field(default_factory=dict)
    purchased_preset_ids_by_competitor: dict[str, set[str]] = field(default_factory=dict)

    def upsert_competitor(self, competitor: LeagueCompetitor) -> LeagueCompetitor:
        self.competitors[competitor.competitor_id] = competitor
        return competitor

    def get_competitor(self, competitor_id: str) -> LeagueCompetitor:
        competitor = self.competitors.get(competitor_id)
        if competitor is None:
            raise UltimateLeagueNotFoundError(f"Ultimate League competitor '{competitor_id}' was not found.")
        return competitor

    def list_tiers(self) -> tuple[LeagueTierDefinition, ...]:
        return self.service.TIER_DEFINITIONS

    def standings(self, tier: LeagueTier | str) -> tuple[LeagueStandingEntry, ...]:
        tier_enum = LeagueTier(tier)
        return self.service.build_tier_tables(tuple(self.competitors.values())).get(tier_enum, ())

    def matchmaking(
        self,
        *,
        competitor_ids: Sequence[str] | None = None,
        prefer_same_tier: bool = True,
    ) -> MatchmakingBatch:
        competitors = self._resolve_competitors(competitor_ids)
        return self.service.create_matchmaking_batch(competitors, prefer_same_tier=prefer_same_tier)

    def record_match_result(
        self,
        *,
        home_competitor_id: str,
        away_competitor_id: str,
        home_score: int,
        away_score: int,
        importance: float = 1.0,
    ):
        home = self.get_competitor(home_competitor_id)
        away = self.get_competitor(away_competitor_id)
        updated_home, updated_away, rating_update = self.service.apply_match_result(
            home=home,
            away=away,
            home_score=home_score,
            away_score=away_score,
            importance=importance,
        )
        self.competitors[home_competitor_id] = updated_home
        self.competitors[away_competitor_id] = updated_away
        return updated_home, updated_away, rating_update

    def create_tournament(
        self,
        *,
        tier: LeagueTier | str,
        starts_at,
        competitor_ids: Sequence[str] | None = None,
        tournament_id: str | None = None,
        field_size: int | None = None,
        round_spacing_minutes: int | None = None,
        match_spacing_minutes: int | None = None,
        parallel_matches: int | None = None,
    ) -> LeagueTournamentPlan:
        competitors = self._resolve_competitors(competitor_ids)
        plan = self.service.schedule_tier_tournament(
            tournament_id=tournament_id or f"ultimate-league-{uuid4().hex[:10]}",
            tier=tier,
            competitors=competitors,
            starts_at=starts_at,
            field_size=field_size,
            round_spacing=timedelta(minutes=round_spacing_minutes) if round_spacing_minutes is not None else None,
            match_spacing=timedelta(minutes=match_spacing_minutes) if match_spacing_minutes is not None else None,
            parallel_matches=parallel_matches,
        )
        self.tournaments[plan.tournament_id] = plan
        return plan

    def get_tournament(self, tournament_id: str) -> LeagueTournamentPlan:
        plan = self.tournaments.get(tournament_id)
        if plan is None:
            raise UltimateLeagueNotFoundError(f"Ultimate League tournament '{tournament_id}' was not found.")
        return plan

    def preview_payouts(
        self,
        *,
        tournament_id: str,
        placements: Sequence[str],
        gross_pool_gtex,
        entrant_count: int | None = None,
        payout_percentages=None,
    ) -> tuple[GTexPrizePayout, ...]:
        tournament = self.get_tournament(tournament_id)
        tournament_entrant_ids = {entrant.competitor_id for entrant in tournament.entrants}
        if len(set(placements)) != len(placements):
            raise UltimateLeagueError("Placements must not contain duplicate competitor IDs.")
        invalid_placements = [competitor_id for competitor_id in placements if competitor_id not in tournament_entrant_ids]
        if invalid_placements:
            raise UltimateLeagueError("Payout previews only accept entrants from the selected tournament.")
        ranked_competitors = tuple(self.get_competitor(competitor_id) for competitor_id in placements)
        return self.service.distribute_prize_pool(
            tournament_id=tournament_id,
            tier=tournament.tier,
            placements=ranked_competitors,
            gross_pool_gtex=gross_pool_gtex,
            entrant_count=entrant_count or len(tournament.entrants),
            payout_percentages=payout_percentages,
        )

    def _resolve_competitors(self, competitor_ids: Sequence[str] | None) -> tuple[LeagueCompetitor, ...]:
        if not competitor_ids:
            return tuple(self.competitors.values())
        return tuple(self.get_competitor(competitor_id) for competitor_id in competitor_ids)

    def upsert_tactical_preset(
        self,
        *,
        preset_id: str | None,
        seller_competitor_id: str,
        title: str,
        formation: str,
        style: str,
        price_gtex: Decimal,
        tags: Sequence[str] | None = None,
        fatigue_ceiling: float = 0.75,
        injury_cover_enabled: bool = False,
    ) -> TacticalPresetListing:
        seller = self.get_competitor(seller_competitor_id)
        listing = TacticalPresetListing(
            preset_id=preset_id or f"preset-{uuid4().hex[:12]}",
            seller_competitor_id=seller_competitor_id,
            seller_display_name=seller.display_name,
            title=title.strip(),
            formation=formation.strip(),
            style=style.strip(),
            price_gtex=Decimal(str(price_gtex)).quantize(Decimal("0.0001")),
            tags=tuple(str(tag).strip().lower() for tag in (tags or ()) if str(tag).strip()),
            fatigue_ceiling=float(fatigue_ceiling),
            injury_cover_enabled=bool(injury_cover_enabled),
        )
        self.tactical_presets[listing.preset_id] = listing
        return listing

    def list_tactical_presets(self) -> tuple[TacticalPresetListing, ...]:
        return tuple(sorted(self.tactical_presets.values(), key=lambda item: (item.price_gtex, item.title.lower())))

    def purchase_tactical_preset(self, *, preset_id: str, buyer_competitor_id: str) -> TacticalPresetListing:
        listing = self.tactical_presets.get(preset_id)
        if listing is None:
            raise UltimateLeagueNotFoundError(f"Tactical preset '{preset_id}' was not found.")
        if listing.seller_competitor_id == buyer_competitor_id:
            raise UltimateLeagueError("Competitors cannot purchase their own tactical preset.")
        self.get_competitor(buyer_competitor_id)
        purchases = self.purchased_preset_ids_by_competitor.setdefault(buyer_competitor_id, set())
        purchases.add(preset_id)
        return listing


__all__ = [
    "UltimateLeagueNotFoundError",
    "UltimateLeagueRuntime",
]
