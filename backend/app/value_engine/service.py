from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone
import json
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from backend.app.core.config import LiquidityBand as LiquidityBandConfig
from backend.app.core.config import LiquidityBandsConfig, Settings, get_settings
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.ingestion.models import (
    Competition,
    CompetitionContext,
    InjuryStatus,
    InternalLeague,
    Match,
    MarketSignal,
    NormalizedAwardEvent,
    NormalizedMatchEvent,
    NormalizedTransferEvent,
    Player,
    PlayerEventWindow,
    PlayerMatchStat,
    PlayerSeasonStat,
)
from backend.app.ingestion.pipeline import NormalizedMatchEventPipeline
from backend.app.models.base import utcnow
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.players.service import PlayerSummaryProjector
from backend.app.value_engine.jobs import ValueSnapshotJob
from backend.app.value_engine.models import (
    DemandSignal,
    EGameSignal,
    HistoricalValuePoint,
    MarketPulse,
    PlayerProfileContext,
    PlayerValueInput,
    ReferenceValueContext,
    ScoutingSignal,
    TradePrint,
    ValueSnapshot,
)
from backend.app.value_engine.read_models import (
    PlayerValueAdminAuditRecord,
    PlayerValueDailyCloseRecord,
    PlayerValueRecomputeCandidateRecord,
    PlayerValueRunRecord,
    PlayerValueSnapshotRecord,
)
from backend.app.value_engine.scoring import ValueEngine, credits_from_real_world_value


POSITION_BASE_VALUES_EUR = {
    "goalkeeper": 8_000_000.0,
    "defender": 12_000_000.0,
    "midfielder": 18_000_000.0,
    "forward": 22_000_000.0,
}
REFERENCE_MARKET_VALUE_SIGNAL_TYPES = {"reference_market_value_eur", "market_value_eur"}
CURRENT_CREDITS_SIGNAL_TYPES = {"current_credits", "credits"}
MID_PRICE_SIGNAL_TYPES = {"market_mid_price_credits", "mid_price_credits", "snapshot_mid_price_credits", "index_price_credits"}
BID_PRICE_SIGNAL_TYPES = {"best_bid_price_credits", "best_bid_credits", "bid_price_credits"}
ASK_PRICE_SIGNAL_TYPES = {"best_ask_price_credits", "best_ask_credits", "ask_price_credits", "listing_price_credits"}
LAST_TRADE_PRICE_SIGNAL_TYPES = {"last_trade_price_credits", "last_sale_price_credits", "recent_trade_price_credits"}
TRADE_PRINT_SIGNAL_TYPES = {
    "trade_print",
    "trade_execution",
    "trade_print_price_credits",
    "trade_execution_price_credits",
}
SHADOW_IGNORED_TRADE_SIGNAL_TYPES = {
    "shadow_ignored_trade_print",
    "shadow_ignored_trade_execution",
    "shadow_ignored_trade_print_price_credits",
    "shadow_ignored_trade_execution_price_credits",
}
HOLDER_COUNT_SIGNAL_TYPES = {"holder_count", "holder_total", "holder_total_count"}
TOP_HOLDER_SHARE_SIGNAL_TYPES = {"top_holder_share_pct", "top_holder_share_ratio"}
TOP_3_HOLDER_SHARE_SIGNAL_TYPES = {"top_3_holder_share_pct", "top3_holder_share_pct", "top_3_holder_share_ratio"}
DEMAND_SIGNAL_FIELDS = frozenset(DemandSignal.__dataclass_fields__.keys())
SCOUTING_SIGNAL_FIELDS = frozenset(ScoutingSignal.__dataclass_fields__.keys())
EGAME_SIGNAL_FIELDS = frozenset(EGameSignal.__dataclass_fields__.keys())
SCOUTING_SIGNAL_ALIASES = {
    "watchlist_adds": {"watchlist_adds", "watchlist_interest"},
    "shortlist_adds": {"shortlist_adds", "shortlist_interest"},
    "transfer_room_adds": {"transfer_room_adds", "transfer_room_entries", "transfer_room_interest"},
    "scouting_activity": {"scouting_activity", "scouting_activity_events", "scouting_reports", "scout_reports"},
    "suspicious_watchlist_adds": {"suspicious_watchlist_adds"},
    "suspicious_shortlist_adds": {"suspicious_shortlist_adds"},
    "suspicious_transfer_room_adds": {"suspicious_transfer_room_adds"},
    "suspicious_scouting_activity": {"suspicious_scouting_activity"},
}
EGAME_SIGNAL_ALIASES = {
    "selection_count": {"egame_selection_count", "competition_selection_count", "selection_count", "fantasy_selection_count"},
    "captain_count": {"egame_captain_count", "captain_count", "boost_selection_count"},
    "contest_win_count": {"egame_contest_win_count", "contest_win_count", "creator_competition_win_count"},
    "spotlight_count": {"egame_spotlight_count", "spotlight_count", "featured_competition_count"},
    "featured_performance_count": {"egame_featured_performance_count", "featured_performance_count", "platform_spotlight_performance"},
    "suspicious_selection_count": {"suspicious_egame_selection_count", "suspicious_selection_count"},
    "suspicious_contest_count": {"suspicious_egame_contest_count", "suspicious_contest_count"},
    "suspicious_spotlight_count": {"suspicious_egame_spotlight_count", "suspicious_spotlight_count"},
}
TRANSFER_EVENT_TYPES = {"transfer_bid_accepted", "transfer_bid_rejected"}
INJURY_EVENT_TYPES = {"injury_created", "injury_recovered"}
FAST_EVENT_NAMES = {
    "orders.executed",
    "market.execution.recorded",
    "market.offer.accepted",
    "competition.replay.archived",
}
HOURLY_EVENT_NAMES = {
    "orders.accepted",
    "market.listing.created",
    "market.listing.cancelled",
    "market.offer.created",
    "market.offer.countered",
    "market.trade_intent.created",
    "market.trade_intent.withdrawn",
    "competition.match.result.generated",
}
DAILY_EVENT_NAMES = {
    "competition.season.settlement.completed",
}


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_signal_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(slots=True)
class IngestionValueSnapshotRepository:
    session: Session
    pipeline: NormalizedMatchEventPipeline = field(default_factory=NormalizedMatchEventPipeline)
    player_ids: frozenset[str] | None = None
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    summary_projector: PlayerSummaryProjector | None = None
    settings: Settings | None = None
    liquidity_bands: LiquidityBandsConfig | None = None
    baseline_eur_per_credit: int | None = None
    snapshot_type: str = "intraday"
    candidate_reasons_by_player: dict[str, tuple[str, ...]] = field(default_factory=dict)
    saved_snapshots: list[ValueSnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        resolved_settings = self.settings or get_settings()
        if self.liquidity_bands is None:
            self.liquidity_bands = resolved_settings.liquidity_bands
        if self.baseline_eur_per_credit is None:
            self.baseline_eur_per_credit = resolved_settings.value_engine_weighting.baseline_eur_per_credit

    def list_player_ids(self, as_of: datetime) -> Sequence[str]:
        statement = select(Player.id).order_by(Player.full_name.asc(), Player.id.asc())
        ids = [player_id for player_id in self.session.scalars(statement)]
        if self.player_ids is None:
            return ids
        return [player_id for player_id in ids if player_id in self.player_ids]

    def load_player_value_input(self, player_id: str, as_of: datetime, lookback_days: int) -> PlayerValueInput:
        as_of = _coerce_utc(as_of)
        player = self.session.scalar(
            select(Player)
            .options(
                selectinload(Player.match_stats).selectinload(PlayerMatchStat.match).selectinload(Match.competition),
                selectinload(Player.match_stats).selectinload(PlayerMatchStat.match).selectinload(Match.season),
                selectinload(Player.match_stats).selectinload(PlayerMatchStat.match).selectinload(Match.home_club),
                selectinload(Player.match_stats).selectinload(PlayerMatchStat.match).selectinload(Match.away_club),
                selectinload(Player.current_club),
                selectinload(Player.current_competition).selectinload(Competition.internal_league),
                selectinload(Player.current_competition).selectinload(Competition.country),
                selectinload(Player.internal_league),
                selectinload(Player.season_stats),
                selectinload(Player.injury_statuses),
                selectinload(Player.market_signals),
                selectinload(Player.liquidity_band),
            )
            .where(Player.id == player_id)
        )
        if player is None:
            raise KeyError(f"Player {player_id} was not found.")

        window_start = as_of - timedelta(days=lookback_days)
        match_events = [
            self._build_match_event(player, stat)
            for stat in player.match_stats
            if stat.match is not None
            and stat.match.kickoff_at is not None
            and window_start <= _coerce_utc(stat.match.kickoff_at) <= as_of
        ]
        player_windows = self.pipeline.build_player_windows(match_events)
        player_window = player_windows.get(player.id)
        latest_season_stat = self._latest_season_stat(player.season_stats)
        previous_snapshot = self._latest_snapshot(player_id=player.id, before_as_of=as_of)
        historical_values = self._historical_values(player.id, before_as_of=as_of)
        current_credits = self._current_credits(player.market_signals, as_of=as_of)
        reference_market_value_eur = self._estimate_reference_market_value_eur(
            player=player,
            season_stat=latest_season_stat,
            as_of=as_of,
            player_window=player_window,
        )
        reference_context = self._build_reference_context(
            player=player,
            reference_market_value_eur=reference_market_value_eur,
            as_of=as_of,
        )
        profile_context = self._build_player_profile_context(
            player=player,
            season_stat=latest_season_stat,
            player_window=player_window,
            as_of=as_of,
        )

        return PlayerValueInput(
            player_id=player.id,
            player_name=player.full_name,
            as_of=as_of,
            reference_market_value_eur=reference_market_value_eur,
            current_credits=current_credits,
            previous_ftv_credits=(
                previous_snapshot.football_truth_value_credits
                if previous_snapshot is not None
                else current_credits
            ),
            previous_pcv_credits=(
                previous_snapshot.target_credits
                if previous_snapshot is not None
                else current_credits
            ),
            previous_gsi_score=self._previous_global_scouting_index(previous_snapshot),
            liquidity_band=self._resolve_liquidity_band(
                player=player,
                current_credits=current_credits,
                baseline_credits=credits_from_real_world_value(
                    reference_market_value_eur,
                    eur_per_credit=self.baseline_eur_per_credit,
                ),
            ),
            match_events=player_window.events if player_window is not None else (),
            transfer_events=self._build_transfer_events(player_id=player.id, window_start=window_start, as_of=as_of),
            award_events=self._build_award_events(player.market_signals, window_start=window_start, as_of=as_of),
            demand_signal=self._build_demand_signal(player.market_signals, window_start=window_start, as_of=as_of),
            scouting_signal=self._build_scouting_signal(player.market_signals, window_start=window_start, as_of=as_of),
            egame_signal=self._build_egame_signal(player.market_signals, window_start=window_start, as_of=as_of),
            market_pulse=self._build_market_pulse(player.market_signals, window_start=window_start, as_of=as_of),
            profile_context=profile_context,
            reference_context=reference_context,
            historical_values=historical_values,
            snapshot_type=self.snapshot_type,
            candidate_reasons=self.candidate_reasons_by_player.get(player.id, ()),
        )

    def save_snapshot(self, snapshot: ValueSnapshot) -> None:
        statement = select(PlayerValueSnapshotRecord).where(
            PlayerValueSnapshotRecord.player_id == snapshot.player_id,
            PlayerValueSnapshotRecord.as_of == snapshot.as_of,
            PlayerValueSnapshotRecord.snapshot_type == snapshot.snapshot_type,
        )
        snapshot_record = self.session.scalar(statement)
        breakdown_payload = asdict(snapshot.breakdown)
        breakdown_payload["global_scouting_index"] = snapshot.global_scouting_index
        breakdown_payload["previous_global_scouting_index"] = snapshot.previous_global_scouting_index
        breakdown_payload["global_scouting_index_movement_pct"] = snapshot.global_scouting_index_movement_pct
        breakdown_payload["global_scouting_index_breakdown"] = asdict(snapshot.global_scouting_index_breakdown)
        if snapshot_record is None:
            snapshot_record = PlayerValueSnapshotRecord(
                player_id=snapshot.player_id,
                player_name=snapshot.player_name,
                as_of=snapshot.as_of,
                snapshot_type=snapshot.snapshot_type,
                previous_credits=snapshot.previous_credits,
                target_credits=snapshot.target_credits,
                movement_pct=snapshot.movement_pct,
                football_truth_value_credits=snapshot.football_truth_value_credits,
                market_signal_value_credits=snapshot.market_signal_value_credits,
                scouting_signal_value_credits=snapshot.scouting_signal_value_credits,
                egame_signal_value_credits=snapshot.egame_signal_value_credits,
                confidence_score=snapshot.confidence_score,
                confidence_tier=snapshot.confidence_tier,
                liquidity_tier=snapshot.liquidity_tier,
                market_integrity_score=snapshot.market_integrity_score,
                signal_trust_score=snapshot.signal_trust_score,
                trend_7d_pct=snapshot.trend_7d_pct,
                trend_30d_pct=snapshot.trend_30d_pct,
                trend_direction=snapshot.trend_direction,
                trend_confidence=snapshot.trend_confidence,
                config_version=snapshot.config_version,
                breakdown_json=breakdown_payload,
                drivers_json=list(snapshot.drivers),
                reason_codes_json=list(snapshot.reason_codes),
            )
            self.session.add(snapshot_record)
        else:
            snapshot_record.player_name = snapshot.player_name
            snapshot_record.snapshot_type = snapshot.snapshot_type
            snapshot_record.previous_credits = snapshot.previous_credits
            snapshot_record.target_credits = snapshot.target_credits
            snapshot_record.movement_pct = snapshot.movement_pct
            snapshot_record.football_truth_value_credits = snapshot.football_truth_value_credits
            snapshot_record.market_signal_value_credits = snapshot.market_signal_value_credits
            snapshot_record.scouting_signal_value_credits = snapshot.scouting_signal_value_credits
            snapshot_record.egame_signal_value_credits = snapshot.egame_signal_value_credits
            snapshot_record.confidence_score = snapshot.confidence_score
            snapshot_record.confidence_tier = snapshot.confidence_tier
            snapshot_record.liquidity_tier = snapshot.liquidity_tier
            snapshot_record.market_integrity_score = snapshot.market_integrity_score
            snapshot_record.signal_trust_score = snapshot.signal_trust_score
            snapshot_record.trend_7d_pct = snapshot.trend_7d_pct
            snapshot_record.trend_30d_pct = snapshot.trend_30d_pct
            snapshot_record.trend_direction = snapshot.trend_direction
            snapshot_record.trend_confidence = snapshot.trend_confidence
            snapshot_record.config_version = snapshot.config_version
            snapshot_record.breakdown_json = breakdown_payload
            snapshot_record.drivers_json = list(snapshot.drivers)
            snapshot_record.reason_codes_json = list(snapshot.reason_codes)

        self.session.flush()
        self._upsert_daily_close(snapshot)
        self._mark_candidate_completed(snapshot.player_id, processed_at=snapshot.as_of)
        if self.summary_projector is not None:
            self.summary_projector.project(
                self.session,
                snapshot=snapshot,
                snapshot_record=snapshot_record,
            )
        self.event_publisher.publish(
            DomainEvent(
                name="value.snapshot.computed",
                payload={
                    "player_id": snapshot.player_id,
                    "player_name": snapshot.player_name,
                    "as_of": snapshot.as_of.isoformat(),
                    "target_credits": snapshot.target_credits,
                    "snapshot_type": snapshot.snapshot_type,
                    "confidence_tier": snapshot.confidence_tier,
                    "market_integrity_score": snapshot.market_integrity_score,
                },
            )
        )
        self.saved_snapshots.append(snapshot)

    def _latest_season_stat(self, season_stats: Sequence[PlayerSeasonStat]) -> PlayerSeasonStat | None:
        if not season_stats:
            return None
        return max(season_stats, key=lambda item: (item.updated_at, item.created_at, item.id))

    def _estimate_reference_market_value_eur(
        self,
        *,
        player: Player,
        season_stat: PlayerSeasonStat | None,
        as_of: datetime,
        player_window: PlayerEventWindow | None,
    ) -> float:
        explicit_value = self._latest_signal_score(player.market_signals, REFERENCE_MARKET_VALUE_SIGNAL_TYPES, as_of=as_of)
        if explicit_value is not None and explicit_value > 0:
            return round(explicit_value, 2)
        if player.market_value_eur is not None and player.market_value_eur > 0:
            return round(player.market_value_eur, 2)

        base_value = POSITION_BASE_VALUES_EUR[self._position_bucket(player)]
        appearances = (season_stat.appearances if season_stat is not None and season_stat.appearances is not None else 0)
        goals = (season_stat.goals if season_stat is not None and season_stat.goals is not None else 0)
        assists = (season_stat.assists if season_stat is not None and season_stat.assists is not None else 0)
        minutes = (season_stat.minutes if season_stat is not None and season_stat.minutes is not None else 0)
        rating = 6.5
        if season_stat is not None and season_stat.average_rating is not None:
            rating = season_stat.average_rating
        elif player_window is not None and player_window.average_rating > 0:
            rating = player_window.average_rating

        if player_window is not None:
            goals = max(goals, player_window.total_goals)
            assists = max(assists, player_window.total_assists)
            minutes = max(minutes, player_window.total_minutes)

        multiplier = (
            1.0
            + min(appearances, 38) * 0.02
            + min(goals, 35) * 0.03
            + min(assists, 25) * 0.02
            + min(minutes / 900.0, 5.0) * 0.04
            + max(rating - 6.5, 0.0) * 0.18
        )
        if player_window is not None:
            multiplier += min(player_window.big_moment_count, 5) * 0.05

        return round(max(base_value * multiplier, 5_000_000.0), 2)

    def _current_credits(self, market_signals: Sequence[MarketSignal], *, as_of: datetime) -> float | None:
        latest_value = self._latest_signal_score(market_signals, CURRENT_CREDITS_SIGNAL_TYPES, as_of=as_of)
        if latest_value is None or latest_value < 0:
            return None
        return round(latest_value, 2)

    def _latest_snapshot(self, *, player_id: str, before_as_of: datetime) -> PlayerValueSnapshotRecord | None:
        statement = (
            select(PlayerValueSnapshotRecord)
            .where(
                PlayerValueSnapshotRecord.player_id == player_id,
                PlayerValueSnapshotRecord.as_of < before_as_of,
            )
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def _historical_values(self, player_id: str, *, before_as_of: datetime) -> tuple[HistoricalValuePoint, ...]:
        window_start = before_as_of - timedelta(days=35)
        statement = (
            select(PlayerValueSnapshotRecord)
            .where(
                PlayerValueSnapshotRecord.player_id == player_id,
                PlayerValueSnapshotRecord.as_of >= window_start,
                PlayerValueSnapshotRecord.as_of < before_as_of,
            )
            .order_by(PlayerValueSnapshotRecord.as_of.asc(), PlayerValueSnapshotRecord.created_at.asc())
        )
        history = [
            HistoricalValuePoint(
                as_of=snapshot.as_of,
                published_value_credits=snapshot.target_credits,
                football_truth_value_credits=snapshot.football_truth_value_credits,
                market_signal_value_credits=snapshot.market_signal_value_credits,
                confidence_score=snapshot.confidence_score,
                snapshot_type=snapshot.snapshot_type,
            )
            for snapshot in self.session.scalars(statement)
        ]
        return tuple(history)

    def _build_reference_context(
        self,
        *,
        player: Player,
        reference_market_value_eur: float,
        as_of: datetime,
    ) -> ReferenceValueContext:
        weighting = self.settings.value_engine_weighting if self.settings is not None else get_settings().value_engine_weighting
        stale_days_threshold = weighting.reference_stale_days
        explicit_value_signal = self._latest_signal(player.market_signals, REFERENCE_MARKET_VALUE_SIGNAL_TYPES, as_of=as_of)
        if explicit_value_signal is not None and explicit_value_signal.score > 0:
            staleness_days = max((as_of - _coerce_utc(explicit_value_signal.as_of)).days, 0)
            confidence_tier = "direct_verified_reference"
            confidence_score = 88.0
            if staleness_days >= stale_days_threshold:
                confidence_tier = "inferred_reference"
                confidence_score = max(88.0 - (staleness_days * 0.75), 52.0)
            return ReferenceValueContext(
                market_value_eur=round(explicit_value_signal.score, 2),
                source=_normalize_signal_type(explicit_value_signal.signal_type),
                confidence_tier=confidence_tier,
                confidence_score=round(confidence_score, 2),
                staleness_days=staleness_days,
                is_stale=staleness_days >= stale_days_threshold,
                blended_with_profile_baseline=staleness_days >= stale_days_threshold,
            )

        if player.market_value_eur is not None and player.market_value_eur > 0:
            staleness_anchor = _coerce_utc(player.last_synced_at) if player.last_synced_at is not None else as_of
            staleness_days = max((as_of - staleness_anchor).days, 0)
            confidence_tier = "direct_verified_reference" if staleness_days < stale_days_threshold else "inferred_reference"
            confidence_score = 82.0 if confidence_tier == "direct_verified_reference" else 64.0
            return ReferenceValueContext(
                market_value_eur=round(player.market_value_eur, 2),
                source="player.market_value_eur",
                confidence_tier=confidence_tier,
                confidence_score=confidence_score,
                staleness_days=staleness_days,
                is_stale=confidence_tier != "direct_verified_reference",
                blended_with_profile_baseline=confidence_tier != "direct_verified_reference",
            )

        return ReferenceValueContext(
            market_value_eur=round(reference_market_value_eur, 2),
            source="heuristic_profile_baseline",
            confidence_tier="heuristic_only",
            confidence_score=38.0,
            staleness_days=0,
            is_stale=False,
            blended_with_profile_baseline=True,
        )

    def _build_player_profile_context(
        self,
        *,
        player: Player,
        season_stat: PlayerSeasonStat | None,
        player_window: PlayerEventWindow | None,
        as_of: datetime,
    ) -> PlayerProfileContext:
        current_competition = player.current_competition
        internal_league = current_competition.internal_league if current_competition is not None else player.internal_league
        competition_strength = None
        if current_competition is not None and current_competition.competition_strength is not None:
            competition_strength = float(current_competition.competition_strength)
        elif internal_league is not None:
            competition_strength = float(internal_league.competition_multiplier)

        recent_form_rating = None
        if season_stat is not None and season_stat.average_rating is not None:
            recent_form_rating = float(season_stat.average_rating)
        elif player_window is not None and player_window.average_rating > 0:
            recent_form_rating = float(player_window.average_rating)

        injury_absence_days = self._current_injury_absence_days(player.injury_statuses, as_of=as_of)
        appearances = season_stat.appearances if season_stat is not None and season_stat.appearances is not None else 0
        starts = season_stat.starts if season_stat is not None and season_stat.starts is not None else 0
        minutes_played = season_stat.minutes if season_stat is not None and season_stat.minutes is not None else 0
        goals = season_stat.goals if season_stat is not None and season_stat.goals is not None else 0
        assists = season_stat.assists if season_stat is not None and season_stat.assists is not None else 0
        clean_sheets = season_stat.clean_sheets if season_stat is not None and season_stat.clean_sheets is not None else 0
        saves = season_stat.saves if season_stat is not None and season_stat.saves is not None else 0
        if player_window is not None:
            minutes_played = max(minutes_played, player_window.total_minutes)
            goals = max(goals, player_window.total_goals)
            assists = max(assists, player_window.total_assists)

        return PlayerProfileContext(
            age_years=self._player_age_years(player.date_of_birth, as_of=as_of),
            position_family=self._position_family(player.normalized_position or player.position),
            position_subrole=self._position_subrole(player.normalized_position or player.position),
            club_tier=(current_competition.name if current_competition is not None else None),
            competition_tier=(internal_league.code if internal_league is not None else None),
            competition_strength=competition_strength,
            club_prestige=float(player.current_club.popularity_score) if player.current_club is not None and player.current_club.popularity_score is not None else 50.0,
            continental_visibility=float(internal_league.visibility_weight) if internal_league is not None else 1.0,
            appearances=appearances,
            starts=starts,
            minutes_played=minutes_played,
            recent_form_rating=recent_form_rating,
            goals=goals,
            assists=assists,
            clean_sheets=clean_sheets,
            saves=saves,
            captaincy_flag=False,
            leadership_flag=False,
            injury_absence_days=injury_absence_days,
            transfer_interest_score=float(self._latest_signal_score(player.market_signals, {"transfer_interest_score", "transfer_room_adds", "transfer_room_interest"}, as_of=as_of) or 0.0),
            profile_completeness_score=float(player.profile_completeness_score or 55.0),
            player_class=self._player_class(player=player, season_stat=season_stat, as_of=as_of),
        )

    def _build_transfer_events(
        self,
        *,
        player_id: str,
        window_start: datetime,
        as_of: datetime,
    ) -> tuple[NormalizedTransferEvent, ...]:
        statement = (
            select(PlayerLifecycleEvent)
            .where(
                PlayerLifecycleEvent.player_id == player_id,
                PlayerLifecycleEvent.event_type.in_(tuple(TRANSFER_EVENT_TYPES)),
                PlayerLifecycleEvent.occurred_on >= window_start.date(),
                PlayerLifecycleEvent.occurred_on <= as_of.date(),
            )
            .order_by(PlayerLifecycleEvent.occurred_on.asc(), PlayerLifecycleEvent.created_at.asc())
        )
        events: list[NormalizedTransferEvent] = []
        for event in self.session.scalars(statement):
            details = event.details_json or {}
            status = "completed" if event.event_type == "transfer_bid_accepted" else "advanced"
            reported_fee_eur = self._coerce_float(details.get("bid_amount_eur") or details.get("bid_amount"))
            events.append(
                NormalizedTransferEvent(
                    source="player_lifecycle",
                    source_event_id=event.id,
                    player_id=player_id,
                    player_name=str(details.get("player_name") or event.summary or player_id),
                    occurred_at=datetime.combine(event.occurred_on, datetime.min.time(), tzinfo=UTC),
                    from_club=str(details.get("selling_club_name") or details.get("from_club") or "Unknown"),
                    to_club=str(details.get("buying_club_name") or details.get("to_club") or "Unknown"),
                    from_competition=str(details.get("from_competition")) if details.get("from_competition") is not None else None,
                    to_competition=str(details.get("to_competition")) if details.get("to_competition") is not None else None,
                    reported_fee_eur=reported_fee_eur,
                    status=status,
                )
            )
        return tuple(events)

    def _build_award_events(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> tuple[NormalizedAwardEvent, ...]:
        awards: list[NormalizedAwardEvent] = []
        for signal in market_signals:
            signal_as_of = _coerce_utc(signal.as_of)
            if signal_as_of < window_start or signal_as_of > as_of:
                continue
            signal_type = _normalize_signal_type(signal.signal_type)
            if not signal_type.startswith("award_"):
                continue
            notes_payload = self._parse_market_signal_notes(signal.notes)
            awards.append(
                NormalizedAwardEvent(
                    source="market_signal",
                    source_event_id=signal.id,
                    player_id=signal.player_id,
                    player_name=str(notes_payload.get("player_name") or signal.player_id),
                    occurred_at=signal_as_of,
                    award_code=signal_type.removeprefix("award_"),
                    award_name=str(notes_payload.get("award_name") or signal_type.removeprefix("award_")),
                    rank=int(notes_payload["rank"]) if notes_payload.get("rank") is not None else None,
                    category=str(notes_payload["category"]) if notes_payload.get("category") is not None else None,
                )
            )
        return tuple(awards)

    def _build_egame_signal(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> EGameSignal:
        counts = {field_name: 0 for field_name in EGAME_SIGNAL_FIELDS}
        for signal in market_signals:
            signal_as_of = _coerce_utc(signal.as_of)
            if signal_as_of < window_start or signal_as_of > as_of:
                continue
            signal_type = _normalize_signal_type(signal.signal_type)
            target_field = self._resolve_egame_signal_field(signal_type)
            if target_field is None:
                continue
            counts[target_field] += max(int(round(signal.score)), 0)
        return EGameSignal(**counts)

    def _latest_signal_score(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime | None = None,
    ) -> float | None:
        latest_signal = self._latest_signal(market_signals, signal_types, as_of=as_of)
        if latest_signal is None:
            return None
        return latest_signal.score

    def _build_market_pulse(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> MarketPulse:
        return MarketPulse(
            midpoint_price_credits=self._positive_signal_score(market_signals, MID_PRICE_SIGNAL_TYPES, as_of=as_of),
            best_bid_price_credits=self._positive_signal_score(market_signals, BID_PRICE_SIGNAL_TYPES, as_of=as_of),
            best_ask_price_credits=self._positive_signal_score(market_signals, ASK_PRICE_SIGNAL_TYPES, as_of=as_of),
            last_trade_price_credits=self._positive_signal_score(
                market_signals,
                LAST_TRADE_PRICE_SIGNAL_TYPES,
                as_of=as_of,
            ),
            trade_prints=self._build_trade_prints(
                market_signals,
                window_start=window_start,
                as_of=as_of,
            ),
            holder_count=self._integer_signal_score(market_signals, HOLDER_COUNT_SIGNAL_TYPES, as_of=as_of),
            top_holder_share_pct=self._share_signal_score(market_signals, TOP_HOLDER_SHARE_SIGNAL_TYPES, as_of=as_of),
            top_3_holder_share_pct=self._share_signal_score(
                market_signals,
                TOP_3_HOLDER_SHARE_SIGNAL_TYPES,
                as_of=as_of,
            ),
        )

    def _positive_signal_score(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime,
    ) -> float | None:
        score = self._latest_signal_score(market_signals, signal_types, as_of=as_of)
        if score is None or score <= 0:
            return None
        return round(score, 2)

    def _integer_signal_score(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime,
    ) -> int | None:
        score = self._latest_signal_score(market_signals, signal_types, as_of=as_of)
        if score is None or score < 0:
            return None
        return max(int(round(score)), 0)

    def _share_signal_score(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime,
    ) -> float | None:
        score = self._latest_signal_score(market_signals, signal_types, as_of=as_of)
        if score is None or score < 0:
            return None
        normalized_score = score / 100.0 if score > 1 else score
        return round(min(max(normalized_score, 0.0), 1.0), 4)

    def _build_trade_prints(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> tuple[TradePrint, ...]:
        trade_prints: list[TradePrint] = []
        trade_signal_types = TRADE_PRINT_SIGNAL_TYPES | SHADOW_IGNORED_TRADE_SIGNAL_TYPES
        for signal in market_signals:
            signal_as_of = _coerce_utc(signal.as_of)
            if signal_as_of < window_start or signal_as_of > as_of:
                continue
            signal_type = _normalize_signal_type(signal.signal_type)
            if signal_type not in trade_signal_types:
                continue
            if signal.score <= 0:
                continue
            notes_payload = self._parse_market_signal_notes(signal.notes)
            seller_user_id = str(
                notes_payload.get("seller_user_id")
                or notes_payload.get("seller_id")
                or ""
            ).strip()
            buyer_user_id = str(
                notes_payload.get("buyer_user_id")
                or notes_payload.get("buyer_id")
                or ""
            ).strip()
            if not seller_user_id or not buyer_user_id:
                continue
            quantity = self._coerce_trade_quantity(notes_payload.get("quantity"))
            trade_id = str(notes_payload.get("trade_id") or signal.provider_external_id).strip()
            if not trade_id:
                continue
            trade_prints.append(
                TradePrint(
                    trade_id=trade_id,
                    seller_user_id=seller_user_id,
                    buyer_user_id=buyer_user_id,
                    price_credits=round(signal.score, 2),
                    occurred_at=signal_as_of,
                    quantity=quantity,
                    shadow_ignored=(
                        signal_type in SHADOW_IGNORED_TRADE_SIGNAL_TYPES
                        or bool(notes_payload.get("shadow_ignored"))
                        or bool(notes_payload.get("ignore_for_pricing"))
                        or bool(notes_payload.get("suspicious"))
                    ),
                )
            )
        trade_prints.sort(key=lambda trade: (trade.occurred_at, trade.trade_id))
        return tuple(trade_prints)

    def _parse_market_signal_notes(self, notes: str | None) -> dict[str, object]:
        if notes is None:
            return {}
        raw_notes = notes.strip()
        if not raw_notes.startswith("{"):
            return {}
        try:
            payload = json.loads(raw_notes)
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _coerce_trade_quantity(self, value: object) -> int:
        try:
            quantity = int(value) if value is not None else 1
        except (TypeError, ValueError):
            quantity = 1
        return max(quantity, 1)

    def _build_demand_signal(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> DemandSignal:
        counts = {field_name: 0 for field_name in DEMAND_SIGNAL_FIELDS}
        for signal in market_signals:
            signal_as_of = _coerce_utc(signal.as_of)
            if signal_as_of < window_start or signal_as_of > as_of:
                continue
            signal_type = _normalize_signal_type(signal.signal_type)
            if signal_type not in counts:
                continue
            counts[signal_type] += max(int(round(signal.score)), 0)
        return DemandSignal(**counts)

    def _build_scouting_signal(
        self,
        market_signals: Sequence[MarketSignal],
        *,
        window_start: datetime,
        as_of: datetime,
    ) -> ScoutingSignal:
        counts = {field_name: 0 for field_name in SCOUTING_SIGNAL_FIELDS}
        for signal in market_signals:
            signal_as_of = _coerce_utc(signal.as_of)
            if signal_as_of < window_start or signal_as_of > as_of:
                continue
            signal_type = _normalize_signal_type(signal.signal_type)
            target_field = self._resolve_scouting_signal_field(signal_type)
            if target_field is None:
                continue
            counts[target_field] += max(int(round(signal.score)), 0)
        return ScoutingSignal(**counts)

    def _build_match_event(self, player: Player, stat: PlayerMatchStat) -> NormalizedMatchEvent:
        match = stat.match
        assert match is not None

        team = match.home_club
        opponent = match.away_club
        if stat.club_id == match.away_club_id:
            team = match.away_club
            opponent = match.home_club

        won_match = stat.club_id is not None and match.winner_club_id == stat.club_id
        stage = match.stage or "regular season"
        goals = stat.goals or 0
        assists = stat.assists or 0
        saves = stat.saves or 0

        competition_context = CompetitionContext(
            competition_id=match.competition_id,
            name=match.competition.name if match.competition is not None else "Unknown Competition",
            stage=stage,
            season=match.season.label if match.season is not None else None,
            country=match.competition.country.name if match.competition is not None and match.competition.country is not None else None,
        )
        team_id = team.id if team is not None else (stat.club_id or player.current_club_id or "")
        team_name = team.name if team is not None else (player.current_club.name if player.current_club is not None else "")
        opponent_id = opponent.id if opponent is not None else ""
        opponent_name = opponent.name if opponent is not None else ""
        big_moment = goals >= 2 or assists >= 2 or (won_match and "final" in stage.lower() and (goals > 0 or assists > 0))

        return NormalizedMatchEvent(
            source=stat.source_provider,
            source_event_id=stat.provider_external_id,
            match_id=match.provider_external_id,
            player_id=player.id,
            player_name=player.full_name,
            team_id=team_id,
            team_name=team_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            competition=competition_context,
            occurred_at=_coerce_utc(match.kickoff_at) if match.kickoff_at is not None else utcnow(),
            minutes=stat.minutes or 0,
            rating=stat.rating or 0.0,
            goals=goals,
            assists=assists,
            saves=saves,
            clean_sheet=bool(stat.clean_sheet),
            started=bool(stat.starts),
            won_match=bool(won_match),
            won_final=bool(won_match and "final" in stage.lower()),
            big_moment=big_moment,
        )

    def _previous_global_scouting_index(self, snapshot: PlayerValueSnapshotRecord | None) -> float | None:
        if snapshot is None:
            return None
        breakdown_json = snapshot.breakdown_json or {}
        score = breakdown_json.get("global_scouting_index")
        if score is not None:
            return float(score)
        breakdown = breakdown_json.get("global_scouting_index_breakdown") or {}
        target_score = breakdown.get("target_score")
        if target_score is None:
            return None
        return float(target_score)

    def _resolve_scouting_signal_field(self, signal_type: str) -> str | None:
        for field_name, aliases in SCOUTING_SIGNAL_ALIASES.items():
            if signal_type in aliases:
                return field_name
        return None

    def _resolve_egame_signal_field(self, signal_type: str) -> str | None:
        for field_name, aliases in EGAME_SIGNAL_ALIASES.items():
            if signal_type in aliases:
                return field_name
        return None

    def _current_injury_absence_days(self, injuries: Sequence[InjuryStatus], *, as_of: datetime) -> int:
        active_days = 0
        for injury in injuries:
            if injury.expected_return_at is None:
                continue
            delta = (injury.expected_return_at - as_of.date()).days
            if delta > active_days:
                active_days = delta
        return max(active_days, 0)

    def _player_age_years(self, birth_date: date | None, *, as_of: datetime) -> float | None:
        if birth_date is None:
            return None
        return round((as_of.date() - birth_date).days / 365.25, 2)

    def _player_class(self, *, player: Player, season_stat: PlayerSeasonStat | None, as_of: datetime) -> str:
        age_years = self._player_age_years(player.date_of_birth, as_of=as_of)
        minutes = season_stat.minutes if season_stat is not None and season_stat.minutes is not None else 0
        market_value = float(player.market_value_eur or 0.0)
        if age_years is not None and age_years <= 23 and (minutes < 2_000 or market_value < 40_000_000):
            return "prospect"
        if age_years is not None and age_years >= 32:
            return "veteran"
        return "established"

    def _position_family(self, position: str | None) -> str:
        normalized = _normalize_signal_type(position or "midfielder")
        if "goal" in normalized:
            return "goalkeeper"
        if "def" in normalized or "back" in normalized:
            return "defender"
        if "wing" in normalized or "forward" in normalized or "striker" in normalized or "attack" in normalized:
            return "forward"
        return "midfielder"

    def _position_subrole(self, position: str | None) -> str | None:
        normalized = _normalize_signal_type(position or "")
        if not normalized:
            return None
        if "wingback" in normalized or "fullback" in normalized:
            return "fullback"
        if "defensive_mid" in normalized or normalized in {"dm", "cdm"}:
            return "defensive_midfielder"
        if "attacking_mid" in normalized or normalized in {"cam", "am"}:
            return "attacking_midfielder"
        if "wing" in normalized:
            return "winger"
        return normalized

    def _coerce_float(self, value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _latest_signal(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime | None = None,
    ) -> MarketSignal | None:
        matching_signals = [
            signal
            for signal in market_signals
            if _normalize_signal_type(signal.signal_type) in signal_types
            and (as_of is None or _coerce_utc(signal.as_of) <= as_of)
        ]
        if not matching_signals:
            return None
        return max(
            matching_signals,
            key=lambda item: (_coerce_utc(item.as_of), _coerce_utc(item.created_at), item.id),
        )

    def _upsert_daily_close(self, snapshot: ValueSnapshot) -> None:
        close_date = snapshot.as_of.date()
        statement = select(PlayerValueDailyCloseRecord).where(
            PlayerValueDailyCloseRecord.player_id == snapshot.player_id,
            PlayerValueDailyCloseRecord.close_date == close_date,
        )
        close_record = self.session.scalar(statement)
        breakdown_payload = asdict(snapshot.breakdown)
        if close_record is None:
            close_record = PlayerValueDailyCloseRecord(
                player_id=snapshot.player_id,
                player_name=snapshot.player_name,
                close_date=close_date,
                close_credits=snapshot.target_credits,
                football_truth_value_credits=snapshot.football_truth_value_credits,
                market_signal_value_credits=snapshot.market_signal_value_credits,
                scouting_signal_value_credits=snapshot.scouting_signal_value_credits,
                egame_signal_value_credits=snapshot.egame_signal_value_credits,
                confidence_score=snapshot.confidence_score,
                confidence_tier=snapshot.confidence_tier,
                liquidity_tier=snapshot.liquidity_tier,
                trend_7d_pct=snapshot.trend_7d_pct,
                trend_30d_pct=snapshot.trend_30d_pct,
                trend_direction=snapshot.trend_direction,
                trend_confidence=snapshot.trend_confidence,
                reason_codes_json=list(snapshot.reason_codes),
                breakdown_json=breakdown_payload,
            )
            self.session.add(close_record)
            return
        close_record.player_name = snapshot.player_name
        close_record.close_credits = snapshot.target_credits
        close_record.football_truth_value_credits = snapshot.football_truth_value_credits
        close_record.market_signal_value_credits = snapshot.market_signal_value_credits
        close_record.scouting_signal_value_credits = snapshot.scouting_signal_value_credits
        close_record.egame_signal_value_credits = snapshot.egame_signal_value_credits
        close_record.confidence_score = snapshot.confidence_score
        close_record.confidence_tier = snapshot.confidence_tier
        close_record.liquidity_tier = snapshot.liquidity_tier
        close_record.trend_7d_pct = snapshot.trend_7d_pct
        close_record.trend_30d_pct = snapshot.trend_30d_pct
        close_record.trend_direction = snapshot.trend_direction
        close_record.trend_confidence = snapshot.trend_confidence
        close_record.reason_codes_json = list(snapshot.reason_codes)
        close_record.breakdown_json = breakdown_payload

    def _mark_candidate_completed(self, player_id: str, *, processed_at: datetime) -> None:
        candidate = self.session.scalar(
            select(PlayerValueRecomputeCandidateRecord).where(
                PlayerValueRecomputeCandidateRecord.player_id == player_id
            )
        )
        if candidate is None:
            return
        candidate.status = "completed"
        candidate.processed_at = processed_at
        candidate.last_error = None

    def _resolve_liquidity_band(
        self,
        *,
        player: Player,
        current_credits: float | None,
        baseline_credits: float,
    ) -> str | None:
        if player.liquidity_band is not None:
            return player.liquidity_band.code or player.liquidity_band.name
        price_point = current_credits if current_credits is not None else baseline_credits
        band = self._liquidity_band_for_price(price_point)
        if band is None:
            return None
        return band.name

    def _liquidity_band_for_price(self, price_credits: float) -> LiquidityBandConfig | None:
        for band in self.liquidity_bands.bands:
            max_price = band.max_price_credits
            if price_credits < band.min_price_credits:
                continue
            if max_price is None or price_credits <= max_price:
                return band
        return None

    def _position_bucket(self, player: Player) -> str:
        position = (player.normalized_position or player.position or "").strip().lower()
        if "goal" in position:
            return "goalkeeper"
        if "def" in position or "back" in position:
            return "defender"
        if "wing" in position or "forward" in position or "striker" in position or "attack" in position:
            return "forward"
        return "midfielder"


@dataclass(slots=True)
class IngestionValueEngineBridge:
    session_factory: sessionmaker[Session]
    pipeline: NormalizedMatchEventPipeline = field(default_factory=NormalizedMatchEventPipeline)
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    summary_projector: PlayerSummaryProjector | None = None
    settings: Settings | None = None
    default_lookback_days: int = 7
    last_run_snapshots: list[ValueSnapshot] = field(default_factory=list)
    event_subscription_enabled: bool = False

    def run(
        self,
        *,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        player_ids: Sequence[str] | None = None,
        snapshot_type: str = "intraday",
        run_type: str = "manual_rebuild",
        triggered_by: str = "system",
        actor_user_id: str | None = None,
        notes: dict[str, object] | None = None,
    ) -> list[ValueSnapshot]:
        snapshot_time = _coerce_utc(as_of or utcnow())
        resolved_settings = self.settings or get_settings()
        with self.session_factory() as session:
            run_record = self._create_run_record(
                session,
                run_type=run_type,
                triggered_by=triggered_by,
                actor_user_id=actor_user_id,
                as_of=snapshot_time,
                notes=notes or {},
            )
            repository = IngestionValueSnapshotRepository(
                session=session,
                pipeline=self.pipeline,
                player_ids=frozenset(player_ids) if player_ids is not None else None,
                event_publisher=self.event_publisher,
                summary_projector=self.summary_projector,
                settings=resolved_settings,
                snapshot_type=snapshot_type,
            )
            resolved_player_ids = list(player_ids) if player_ids is not None else list(repository.list_player_ids(snapshot_time))
            run_record.candidate_count = len(resolved_player_ids)
            try:
                snapshots = ValueSnapshotJob(
                    engine=ValueEngine(config=resolved_settings.value_engine_weighting),
                    lookback_days=lookback_days or self.default_lookback_days,
                ).run(
                    repository,
                    snapshot_time,
                )
            except Exception as exc:
                run_record.status = "failed"
                run_record.processed_count = 0
                run_record.snapshot_count = 0
                run_record.completed_at = utcnow()
                run_record.error_message = str(exc)
                session.commit()
                raise
            run_record.status = "success"
            run_record.processed_count = len(resolved_player_ids)
            run_record.snapshot_count = len(snapshots)
            run_record.completed_at = snapshot_time
            session.commit()
        self.last_run_snapshots = snapshots
        return snapshots

    def run_fast_reconciliation(
        self,
        *,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        limit: int = 25,
        actor_user_id: str | None = None,
    ) -> list[ValueSnapshot]:
        return self._run_candidate_tempo(
            tempo="fast",
            as_of=as_of,
            lookback_days=lookback_days,
            limit=limit,
            snapshot_type="intraday",
            run_type="fast_reconciliation",
            actor_user_id=actor_user_id,
        )

    def run_hourly_reconciliation(
        self,
        *,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        limit: int = 100,
        actor_user_id: str | None = None,
    ) -> list[ValueSnapshot]:
        return self._run_candidate_tempo(
            tempo="hourly",
            as_of=as_of,
            lookback_days=lookback_days,
            limit=limit,
            snapshot_type="intraday",
            run_type="hourly_reconciliation",
            actor_user_id=actor_user_id,
        )

    def run_daily_rebase(
        self,
        *,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        limit: int | None = None,
        actor_user_id: str | None = None,
    ) -> list[ValueSnapshot]:
        return self._run_candidate_tempo(
            tempo="daily",
            as_of=as_of,
            lookback_days=lookback_days,
            limit=limit,
            snapshot_type="daily_close",
            run_type="daily_rebase",
            actor_user_id=actor_user_id,
        )

    def handle_event(self, event: DomainEvent) -> None:
        if event.name not in FAST_EVENT_NAMES | HOURLY_EVENT_NAMES | DAILY_EVENT_NAMES:
            return
        if self._uses_sqlite():
            return
        try:
            with self.session_factory() as session:
                self._ingest_event_signals(session, event)
                player_ids = self._player_ids_from_event(event)
                tempo = "daily"
                if event.name in FAST_EVENT_NAMES:
                    tempo = "fast"
                elif event.name in HOURLY_EVENT_NAMES:
                    tempo = "hourly"
                for player_id in player_ids:
                    self._mark_recompute_candidate(
                        session,
                        player_id=player_id,
                        tempo=tempo,
                        reason_codes=(event.name,),
                        priority=self._event_priority(tempo),
                        event_time=_coerce_utc(event.occurred_at),
                        metadata={"source_event": event.name},
                    )
                session.commit()
        except OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise

    def ensure_event_subscription(self) -> None:
        if self.event_subscription_enabled:
            return
        self.event_publisher.subscribe(self.handle_event)
        self.event_subscription_enabled = True

    def preview_player(
        self,
        session: Session,
        *,
        player_id: str,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        snapshot_type: str = "intraday",
    ) -> ValueSnapshot:
        snapshot_time = _coerce_utc(as_of or utcnow())
        resolved_settings = self.settings or get_settings()
        repository = IngestionValueSnapshotRepository(
            session=session,
            pipeline=self.pipeline,
            player_ids=frozenset((player_id,)),
            event_publisher=self.event_publisher,
            summary_projector=self.summary_projector,
            settings=resolved_settings,
            snapshot_type=snapshot_type,
        )
        payload = repository.load_player_value_input(
            player_id=player_id,
            as_of=snapshot_time,
            lookback_days=lookback_days or self.default_lookback_days,
        )
        return ValueEngine(config=resolved_settings.value_engine_weighting).build_snapshot(payload)

    def record_admin_action(
        self,
        session: Session,
        *,
        action_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        payload: dict[str, object],
        target_player_id: str | None = None,
        is_override: bool = False,
    ) -> PlayerValueAdminAuditRecord:
        record = PlayerValueAdminAuditRecord(
            action_type=action_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            config_version=(self.settings or get_settings()).value_engine_weighting.config_version,
            target_player_id=target_player_id,
            payload_json=payload,
            is_override=is_override,
        )
        session.add(record)
        session.flush()
        return record

    def list_run_history(self, session: Session, limit: int = 20) -> list[PlayerValueRunRecord]:
        statement = (
            select(PlayerValueRunRecord)
            .order_by(PlayerValueRunRecord.created_at.desc())
            .limit(limit)
        )
        return list(session.scalars(statement))

    def list_candidates(self, session: Session, limit: int = 100) -> list[PlayerValueRecomputeCandidateRecord]:
        statement = (
            select(PlayerValueRecomputeCandidateRecord)
            .order_by(
                PlayerValueRecomputeCandidateRecord.priority.desc(),
                PlayerValueRecomputeCandidateRecord.last_event_at.desc(),
                PlayerValueRecomputeCandidateRecord.updated_at.desc(),
            )
            .limit(limit)
        )
        return list(session.scalars(statement))

    def list_admin_audits(self, session: Session, limit: int = 50) -> list[PlayerValueAdminAuditRecord]:
        statement = (
            select(PlayerValueAdminAuditRecord)
            .order_by(PlayerValueAdminAuditRecord.created_at.desc())
            .limit(limit)
        )
        return list(session.scalars(statement))

    def inspect_player(self, session: Session, player_id: str) -> dict[str, object]:
        latest_snapshot = ValueSnapshotQueryService(session).get_latest(player_id)
        candidate = session.scalar(
            select(PlayerValueRecomputeCandidateRecord).where(PlayerValueRecomputeCandidateRecord.player_id == player_id)
        )
        history = ValueSnapshotQueryService(session).list_history(player_id=player_id, limit=20)
        daily_closes = ValueSnapshotQueryService(session).list_daily_closes(player_id=player_id, limit=14)
        return {
            "latest_snapshot": latest_snapshot,
            "candidate": candidate,
            "history": history,
            "daily_closes": daily_closes,
        }

    def _run_candidate_tempo(
        self,
        *,
        tempo: str,
        as_of: datetime | None,
        lookback_days: int | None,
        limit: int | None,
        snapshot_type: str,
        run_type: str,
        actor_user_id: str | None,
    ) -> list[ValueSnapshot]:
        snapshot_time = _coerce_utc(as_of or utcnow())
        with self.session_factory() as session:
            player_ids = self._candidate_player_ids(session, tempo=tempo, limit=limit)
        if not player_ids:
            return []
        return self.run(
            as_of=snapshot_time,
            lookback_days=lookback_days,
            player_ids=player_ids,
            snapshot_type=snapshot_type,
            run_type=run_type,
            triggered_by="admin" if actor_user_id else "system",
            actor_user_id=actor_user_id,
            notes={"tempo": tempo, "candidate_limit": limit},
        )

    def _candidate_player_ids(self, session: Session, *, tempo: str, limit: int | None) -> list[str]:
        statement = (
            select(PlayerValueRecomputeCandidateRecord)
            .where(
                PlayerValueRecomputeCandidateRecord.status.in_(("pending", "completed")),
                PlayerValueRecomputeCandidateRecord.requested_tempo.in_(self._tempo_filter(tempo)),
            )
            .order_by(
                PlayerValueRecomputeCandidateRecord.priority.desc(),
                PlayerValueRecomputeCandidateRecord.last_event_at.desc(),
                PlayerValueRecomputeCandidateRecord.updated_at.desc(),
            )
        )
        if limit is not None:
            statement = statement.limit(limit)
        candidates = list(session.scalars(statement))
        for candidate in candidates:
            candidate.status = "processing"
            candidate.claimed_at = utcnow()
        session.commit()
        return [candidate.player_id for candidate in candidates]

    def _tempo_filter(self, tempo: str) -> tuple[str, ...]:
        if tempo == "daily":
            return ("fast", "hourly", "daily")
        if tempo == "hourly":
            return ("fast", "hourly")
        return ("fast",)

    def _mark_recompute_candidate(
        self,
        session: Session,
        *,
        player_id: str,
        tempo: str,
        reason_codes: tuple[str, ...],
        priority: int,
        event_time: datetime,
        metadata: dict[str, object] | None = None,
        player_name: str | None = None,
    ) -> None:
        candidate = session.scalar(
            select(PlayerValueRecomputeCandidateRecord).where(
                PlayerValueRecomputeCandidateRecord.player_id == player_id
            )
        )
        metadata_payload = metadata or {}
        if candidate is None:
            candidate = PlayerValueRecomputeCandidateRecord(
                player_id=player_id,
                player_name=player_name,
                status="pending",
                requested_tempo=tempo,
                priority=priority,
                trigger_count=1,
                signal_delta_score=float(priority),
                last_event_at=event_time,
                last_requested_at=utcnow(),
                reason_codes_json=list(dict.fromkeys(reason_codes)),
                metadata_json=metadata_payload,
            )
            session.add(candidate)
            return
        candidate.player_name = player_name or candidate.player_name
        candidate.status = "pending"
        candidate.requested_tempo = self._dominant_tempo(candidate.requested_tempo, tempo)
        candidate.priority = max(candidate.priority, priority)
        candidate.trigger_count += 1
        candidate.signal_delta_score = float(candidate.priority)
        candidate.last_event_at = event_time
        candidate.last_requested_at = utcnow()
        candidate.reason_codes_json = list(dict.fromkeys([*candidate.reason_codes_json, *reason_codes]))
        candidate.metadata_json = {**(candidate.metadata_json or {}), **metadata_payload}

    def _event_priority(self, tempo: str) -> int:
        return {"fast": 95, "hourly": 70, "daily": 50}.get(tempo, 50)

    def _dominant_tempo(self, current: str, incoming: str) -> str:
        ordering = {"daily": 0, "hourly": 1, "fast": 2}
        return incoming if ordering.get(incoming, 0) >= ordering.get(current, 0) else current

    def _create_run_record(
        self,
        session: Session,
        *,
        run_type: str,
        triggered_by: str,
        actor_user_id: str | None,
        as_of: datetime,
        notes: dict[str, object],
    ) -> PlayerValueRunRecord:
        run_record = PlayerValueRunRecord(
            run_type=run_type,
            status="running",
            as_of=as_of,
            config_version=(self.settings or get_settings()).value_engine_weighting.config_version,
            triggered_by=triggered_by,
            actor_user_id=actor_user_id,
            started_at=utcnow(),
            notes_json=notes,
        )
        session.add(run_record)
        session.flush()
        return run_record

    def _uses_sqlite(self) -> bool:
        bind = self.session_factory.kw.get("bind")
        return bool(bind is not None and bind.dialect.name == "sqlite")

    def _player_ids_from_event(self, event: DomainEvent) -> tuple[str, ...]:
        payload = event.payload
        player_ids: list[str] = []
        direct_player_id = payload.get("player_id")
        if isinstance(direct_player_id, str) and direct_player_id:
            player_ids.append(direct_player_id)
        asset_id = payload.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            player_ids.append(asset_id)
        if event.name == "competition.replay.archived":
            timeline = payload.get("timeline") or []
            if isinstance(timeline, list):
                for item in timeline:
                    if not isinstance(item, dict):
                        continue
                    player_id = item.get("player_id")
                    if isinstance(player_id, str) and player_id:
                        player_ids.append(player_id)
        return tuple(dict.fromkeys(player_ids))

    def _ingest_event_signals(self, session: Session, event: DomainEvent) -> None:
        payload = event.payload
        now = _coerce_utc(event.occurred_at)
        if event.name in {"orders.executed", "market.execution.recorded"}:
            player_id = payload.get("player_id") or payload.get("asset_id")
            price = payload.get("price")
            if isinstance(player_id, str) and player_id and price is not None:
                signal = MarketSignal(
                    source_provider="value_engine_event_bridge",
                    provider_external_id=str(payload.get("execution_id") or payload.get("offer_id") or f"{player_id}:{now.isoformat()}"),
                    player_id=player_id,
                    signal_type="trade_print_price_credits",
                    score=float(price),
                    as_of=now,
                    notes=json.dumps(
                        {
                            "trade_id": payload.get("execution_id"),
                            "seller_user_id": payload.get("seller_user_id") or payload.get("sell_order_id"),
                            "buyer_user_id": payload.get("buyer_user_id") or payload.get("buy_order_id"),
                            "quantity": payload.get("quantity", 1),
                            "source_event": event.name,
                        }
                    ),
                )
                session.merge(signal)
        if event.name == "competition.replay.archived":
            timeline = payload.get("timeline") or []
            spotlight_by_player: dict[str, int] = {}
            if isinstance(timeline, list):
                for item in timeline:
                    if not isinstance(item, dict):
                        continue
                    player_id = item.get("player_id")
                    if not isinstance(player_id, str) or not player_id:
                        continue
                    spotlight_by_player[player_id] = spotlight_by_player.get(player_id, 0) + 1
            for player_id, count in spotlight_by_player.items():
                signal = MarketSignal(
                    source_provider="value_engine_event_bridge",
                    provider_external_id=f"replay:{payload.get('replay_id')}:{player_id}",
                    player_id=player_id,
                    signal_type="egame_spotlight_count",
                    score=float(count),
                    as_of=now,
                    notes=json.dumps({"source_event": event.name}),
                )
                session.merge(signal)


@dataclass(slots=True)
class ValueSnapshotQueryService:
    session: Session

    def get_latest(self, player_id: str, *, snapshot_type: str | None = None) -> PlayerValueSnapshotRecord | None:
        statement = select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.player_id == player_id)
        if snapshot_type is not None:
            statement = statement.where(PlayerValueSnapshotRecord.snapshot_type == snapshot_type)
        statement = (
            statement
            .order_by(
                PlayerValueSnapshotRecord.as_of.desc(),
                PlayerValueSnapshotRecord.created_at.desc(),
                PlayerValueSnapshotRecord.id.desc(),
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_latest(self, limit: int = 50, *, snapshot_type: str | None = None) -> list[PlayerValueSnapshotRecord]:
        statement = select(PlayerValueSnapshotRecord)
        if snapshot_type is not None:
            statement = statement.where(PlayerValueSnapshotRecord.snapshot_type == snapshot_type)
        statement = (
            statement
            .order_by(
                PlayerValueSnapshotRecord.as_of.desc(),
                PlayerValueSnapshotRecord.created_at.desc(),
                PlayerValueSnapshotRecord.id.desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_history(
        self,
        *,
        player_id: str,
        limit: int = 50,
        snapshot_type: str | None = None,
    ) -> list[PlayerValueSnapshotRecord]:
        statement = select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.player_id == player_id)
        if snapshot_type is not None:
            statement = statement.where(PlayerValueSnapshotRecord.snapshot_type == snapshot_type)
        statement = (
            statement
            .order_by(
                PlayerValueSnapshotRecord.as_of.desc(),
                PlayerValueSnapshotRecord.created_at.desc(),
                PlayerValueSnapshotRecord.id.desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_daily_closes(self, *, player_id: str, limit: int = 30) -> list[PlayerValueDailyCloseRecord]:
        statement = (
            select(PlayerValueDailyCloseRecord)
            .where(PlayerValueDailyCloseRecord.player_id == player_id)
            .order_by(PlayerValueDailyCloseRecord.close_date.desc(), PlayerValueDailyCloseRecord.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
