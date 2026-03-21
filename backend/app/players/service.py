from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.ingestion.models import Match, Player, PlayerMatchStat, PlayerSeasonStat
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.value_engine.models import ValueSnapshot
from backend.app.value_engine.pricing_curve import round_gtex_display_value
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord


@dataclass(slots=True)
class PlayerSummaryProjector:
    def project(self, session: Session, *, snapshot: ValueSnapshot, snapshot_record: PlayerValueSnapshotRecord) -> PlayerSummaryReadModel:
        player = session.scalar(
            select(Player)
            .options(
                selectinload(Player.current_club),
                selectinload(Player.supply_tier),
                selectinload(Player.liquidity_band),
                selectinload(Player.market_signals),
                selectinload(Player.match_stats).selectinload(PlayerMatchStat.match).selectinload(Match.competition),
                selectinload(Player.season_stats),
            )
            .where(Player.id == snapshot.player_id)
        )
        if player is None:
            raise KeyError(f"Player {snapshot.player_id} was not found.")

        latest_match_stat = self._latest_match_stat(player.match_stats)
        latest_season_stat = self._latest_season_stat(player.season_stats)
        competition = None
        if latest_match_stat is not None and latest_match_stat.match is not None:
            competition = latest_match_stat.match.competition

        summary = session.get(PlayerSummaryReadModel, snapshot.player_id)
        if summary is None:
            summary = PlayerSummaryReadModel(
                player_id=snapshot.player_id,
                player_name=snapshot.player_name,
                last_snapshot_at=snapshot.as_of,
                current_value_credits=round_gtex_display_value(snapshot.target_credits) or snapshot.target_credits,
                previous_value_credits=round_gtex_display_value(snapshot.previous_credits) or snapshot.previous_credits,
                movement_pct=snapshot.movement_pct,
                summary_json={},
            )
            session.add(summary)

        summary.player_name = snapshot.player_name
        summary.current_club_id = player.current_club_id
        summary.current_club_name = player.current_club.name if player.current_club is not None else None
        summary.current_competition_id = competition.id if competition is not None else None
        summary.current_competition_name = competition.name if competition is not None else None
        summary.last_snapshot_id = snapshot_record.id
        summary.last_snapshot_at = snapshot.as_of
        summary.current_value_credits = round_gtex_display_value(snapshot.target_credits) or snapshot.target_credits
        summary.previous_value_credits = round_gtex_display_value(snapshot.previous_credits) or snapshot.previous_credits
        summary.movement_pct = snapshot.movement_pct
        summary.average_rating = self._resolve_average_rating(latest_match_stat, latest_season_stat)
        summary.market_interest_score = int(round(sum(max(signal.score, 0.0) for signal in player.market_signals)))
        summary.summary_json = {
            "position": player.normalized_position or player.position,
            "drivers": list(snapshot.drivers),
            "reason_codes": list(snapshot.reason_codes),
            "football_truth_value_credits": round_gtex_display_value(snapshot.football_truth_value_credits),
            "market_signal_value_credits": round_gtex_display_value(snapshot.market_signal_value_credits),
            "scouting_signal_value_credits": round_gtex_display_value(snapshot.scouting_signal_value_credits),
            "egame_signal_value_credits": round_gtex_display_value(snapshot.egame_signal_value_credits),
            "published_card_value_credits": round_gtex_display_value(snapshot.published_card_value_credits),
            "confidence_score": snapshot.confidence_score,
            "confidence_tier": snapshot.confidence_tier,
            "liquidity_tier": snapshot.liquidity_tier,
            "market_integrity_score": snapshot.market_integrity_score,
            "signal_trust_score": snapshot.signal_trust_score,
            "trend_7d_pct": snapshot.trend_7d_pct,
            "trend_30d_pct": snapshot.trend_30d_pct,
            "trend_direction": snapshot.trend_direction,
            "trend_confidence": snapshot.trend_confidence,
            "global_scouting_index": snapshot.global_scouting_index,
            "previous_global_scouting_index": snapshot.previous_global_scouting_index,
            "global_scouting_index_movement_pct": snapshot.global_scouting_index_movement_pct,
            "supply_tier": (
                {
                    "code": player.supply_tier.code,
                    "name": player.supply_tier.name,
                    "circulating_supply": player.supply_tier.circulating_supply,
                    "daily_pack_supply": player.supply_tier.daily_pack_supply,
                    "season_mint_cap": player.supply_tier.season_mint_cap,
                }
                if player.supply_tier is not None
                else None
            ),
            "liquidity_band": (
                {
                    "code": player.liquidity_band.code,
                    "name": player.liquidity_band.name,
                    "max_spread_bps": player.liquidity_band.max_spread_bps,
                    "maker_inventory_target": player.liquidity_band.maker_inventory_target,
                    "instant_sell_fee_bps": player.liquidity_band.instant_sell_fee_bps,
                }
                if player.liquidity_band is not None
                else None
            ),
        }
        session.flush()
        return summary

    def _latest_match_stat(self, match_stats: list[PlayerMatchStat]) -> PlayerMatchStat | None:
        candidates = [
            stat
            for stat in match_stats
            if stat.match is not None and stat.match.kickoff_at is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.match.kickoff_at, item.updated_at))

    def _latest_season_stat(self, season_stats: list[PlayerSeasonStat]) -> PlayerSeasonStat | None:
        if not season_stats:
            return None
        return max(season_stats, key=lambda item: (item.updated_at, item.created_at, item.id))

    def _resolve_average_rating(
        self,
        latest_match_stat: PlayerMatchStat | None,
        latest_season_stat: PlayerSeasonStat | None,
    ) -> float | None:
        if latest_match_stat is not None and latest_match_stat.rating is not None:
            return latest_match_stat.rating
        if latest_season_stat is not None:
            return latest_season_stat.average_rating
        return None


@dataclass(slots=True)
class PlayerSummaryQueryService:
    session: Session

    def get_summary(self, player_id: str) -> PlayerSummaryReadModel | None:
        return self.session.get(PlayerSummaryReadModel, player_id)

    def list_recent(self, limit: int = 20) -> list[PlayerSummaryReadModel]:
        statement = (
            select(PlayerSummaryReadModel)
            .order_by(PlayerSummaryReadModel.last_snapshot_at.desc(), PlayerSummaryReadModel.player_name.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
