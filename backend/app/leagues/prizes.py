from __future__ import annotations

from collections import defaultdict

from backend.app.config.competition_constants import (
    CHAMPIONS_LEAGUE_FUND_PCT,
    LEAGUE_WINNER_PCT,
    TOP_ASSIST_PCT,
    TOP_SCORER_PCT,
)
from backend.app.leagues.models import (
    LeagueAwardResult,
    LeagueAwardWinner,
    LeagueChampionPrize,
    LeaguePlayerContribution,
    LeaguePrizePoolBreakdown,
    LeagueStandingRow,
)


class LeaguePrizeService:
    def calculate(
        self,
        *,
        buy_in_tier: int,
        club_count: int,
        standings: tuple[LeagueStandingRow, ...],
        player_contributions: tuple[LeaguePlayerContribution, ...],
    ) -> tuple[
        LeaguePrizePoolBreakdown,
        LeagueChampionPrize | None,
        LeagueAwardResult,
        LeagueAwardResult,
    ]:
        total_pool = float(buy_in_tier * club_count)
        prize_pool = LeaguePrizePoolBreakdown(
            total_pool=total_pool,
            winner_prize=total_pool * LEAGUE_WINNER_PCT,
            top_scorer_prize=total_pool * TOP_SCORER_PCT,
            top_assist_prize=total_pool * TOP_ASSIST_PCT,
            champions_league_fund=total_pool * CHAMPIONS_LEAGUE_FUND_PCT,
        )

        champion_prize = None
        if standings:
            champion = standings[0]
            champion_prize = LeagueChampionPrize(
                club_id=champion.club_id,
                club_name=champion.club_name,
                amount=prize_pool.winner_prize,
            )

        aggregated = self._aggregate_player_contributions(player_contributions)
        top_scorer_award = self._build_award(
            award="top_scorer",
            prize_pool=prize_pool.top_scorer_prize,
            player_totals=aggregated,
            metric="goals",
        )
        top_assist_award = self._build_award(
            award="top_assist",
            prize_pool=prize_pool.top_assist_prize,
            player_totals=aggregated,
            metric="assists",
        )

        return prize_pool, champion_prize, top_scorer_award, top_assist_award

    def _aggregate_player_contributions(
        self,
        player_contributions: tuple[LeaguePlayerContribution, ...],
    ) -> tuple[LeaguePlayerContribution, ...]:
        totals: dict[str, dict[str, object]] = defaultdict(
            lambda: {
                "player_id": "",
                "player_name": "",
                "club_id": "",
                "goals": 0,
                "assists": 0,
            }
        )
        for contribution in player_contributions:
            record = totals[contribution.player_id]
            record["player_id"] = contribution.player_id
            record["player_name"] = contribution.player_name
            record["club_id"] = contribution.club_id
            record["goals"] = int(record["goals"]) + contribution.goals
            record["assists"] = int(record["assists"]) + contribution.assists
        return tuple(
            LeaguePlayerContribution(
                player_id=str(record["player_id"]),
                player_name=str(record["player_name"]),
                club_id=str(record["club_id"]),
                goals=int(record["goals"]),
                assists=int(record["assists"]),
            )
            for record in totals.values()
        )

    def _build_award(
        self,
        *,
        award: str,
        prize_pool: float,
        player_totals: tuple[LeaguePlayerContribution, ...],
        metric: str,
    ) -> LeagueAwardResult:
        if not player_totals:
            return LeagueAwardResult(award=award, prize_pool=prize_pool, winners=())

        top_value = max(getattr(player, metric) for player in player_totals)
        winners = tuple(player for player in player_totals if getattr(player, metric) == top_value)
        split_amount = prize_pool / len(winners) if winners else 0.0
        return LeagueAwardResult(
            award=award,
            prize_pool=prize_pool,
            winners=tuple(
                LeagueAwardWinner(
                    player_id=player.player_id,
                    player_name=player.player_name,
                    club_id=player.club_id,
                    stat_value=getattr(player, metric),
                    split_amount=split_amount,
                )
                for player in winners
            ),
        )


__all__ = ["LeaguePrizeService"]
