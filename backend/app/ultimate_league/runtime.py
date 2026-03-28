from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Sequence
from uuid import uuid4

from app.ultimate_league.league_service import (
    GTexPrizePayout,
    LeagueCompetitor,
    LeagueStandingEntry,
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


__all__ = [
    "UltimateLeagueNotFoundError",
    "UltimateLeagueRuntime",
]
