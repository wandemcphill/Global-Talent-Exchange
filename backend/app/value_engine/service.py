from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from backend.app.core.config import LiquidityBand as LiquidityBandConfig
from backend.app.core.config import LiquidityBandsConfig, Settings, get_settings
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.ingestion.models import (
    CompetitionContext,
    Match,
    MarketSignal,
    NormalizedMatchEvent,
    Player,
    PlayerEventWindow,
    PlayerMatchStat,
    PlayerSeasonStat,
)
from backend.app.ingestion.pipeline import NormalizedMatchEventPipeline
from backend.app.models.base import utcnow
from backend.app.players.service import PlayerSummaryProjector
from backend.app.value_engine.jobs import ValueSnapshotJob
from backend.app.value_engine.models import DemandSignal, MarketPulse, PlayerValueInput, ScoutingSignal, TradePrint, ValueSnapshot
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord
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
                selectinload(Player.season_stats),
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
        current_credits = self._current_credits(player.market_signals, as_of=as_of)
        reference_market_value_eur = self._estimate_reference_market_value_eur(
            player=player,
            season_stat=latest_season_stat,
            as_of=as_of,
            player_window=player_window,
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
            demand_signal=self._build_demand_signal(player.market_signals, window_start=window_start, as_of=as_of),
            scouting_signal=self._build_scouting_signal(player.market_signals, window_start=window_start, as_of=as_of),
            market_pulse=self._build_market_pulse(player.market_signals, window_start=window_start, as_of=as_of),
        )

    def save_snapshot(self, snapshot: ValueSnapshot) -> None:
        statement = select(PlayerValueSnapshotRecord).where(
            PlayerValueSnapshotRecord.player_id == snapshot.player_id,
            PlayerValueSnapshotRecord.as_of == snapshot.as_of,
        )
        snapshot_record = self.session.scalar(statement)
        if snapshot_record is None:
            breakdown_payload = asdict(snapshot.breakdown)
            breakdown_payload["global_scouting_index"] = snapshot.global_scouting_index
            breakdown_payload["previous_global_scouting_index"] = snapshot.previous_global_scouting_index
            breakdown_payload["global_scouting_index_movement_pct"] = snapshot.global_scouting_index_movement_pct
            breakdown_payload["global_scouting_index_breakdown"] = asdict(snapshot.global_scouting_index_breakdown)
            snapshot_record = PlayerValueSnapshotRecord(
                player_id=snapshot.player_id,
                player_name=snapshot.player_name,
                as_of=snapshot.as_of,
                previous_credits=snapshot.previous_credits,
                target_credits=snapshot.target_credits,
                movement_pct=snapshot.movement_pct,
                football_truth_value_credits=snapshot.football_truth_value_credits,
                market_signal_value_credits=snapshot.market_signal_value_credits,
                breakdown_json=breakdown_payload,
                drivers_json=list(snapshot.drivers),
            )
            self.session.add(snapshot_record)
        else:
            breakdown_payload = asdict(snapshot.breakdown)
            breakdown_payload["global_scouting_index"] = snapshot.global_scouting_index
            breakdown_payload["previous_global_scouting_index"] = snapshot.previous_global_scouting_index
            breakdown_payload["global_scouting_index_movement_pct"] = snapshot.global_scouting_index_movement_pct
            breakdown_payload["global_scouting_index_breakdown"] = asdict(snapshot.global_scouting_index_breakdown)
            snapshot_record.player_name = snapshot.player_name
            snapshot_record.previous_credits = snapshot.previous_credits
            snapshot_record.target_credits = snapshot.target_credits
            snapshot_record.movement_pct = snapshot.movement_pct
            snapshot_record.football_truth_value_credits = snapshot.football_truth_value_credits
            snapshot_record.market_signal_value_credits = snapshot.market_signal_value_credits
            snapshot_record.breakdown_json = breakdown_payload
            snapshot_record.drivers_json = list(snapshot.drivers)

        self.session.flush()
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

    def _latest_signal_score(
        self,
        market_signals: Sequence[MarketSignal],
        signal_types: set[str],
        *,
        as_of: datetime | None = None,
    ) -> float | None:
        matching_signals = [
            signal
            for signal in market_signals
            if _normalize_signal_type(signal.signal_type) in signal_types
            and (as_of is None or _coerce_utc(signal.as_of) <= as_of)
        ]
        if not matching_signals:
            return None
        latest_signal = max(
            matching_signals,
            key=lambda item: (_coerce_utc(item.as_of), _coerce_utc(item.created_at), item.id),
        )
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

    def run(
        self,
        *,
        as_of: datetime | None = None,
        lookback_days: int | None = None,
        player_ids: Sequence[str] | None = None,
    ) -> list[ValueSnapshot]:
        snapshot_time = _coerce_utc(as_of or utcnow())
        resolved_settings = self.settings or get_settings()
        with self.session_factory() as session:
            repository = IngestionValueSnapshotRepository(
                session=session,
                pipeline=self.pipeline,
                player_ids=frozenset(player_ids) if player_ids is not None else None,
                event_publisher=self.event_publisher,
                summary_projector=self.summary_projector,
                settings=resolved_settings,
            )
            snapshots = ValueSnapshotJob(
                engine=ValueEngine(config=resolved_settings.value_engine_weighting),
                lookback_days=lookback_days or self.default_lookback_days,
            ).run(
                repository,
                snapshot_time,
            )
            session.commit()
        self.last_run_snapshots = snapshots
        return snapshots


@dataclass(slots=True)
class ValueSnapshotQueryService:
    session: Session

    def get_latest(self, player_id: str) -> PlayerValueSnapshotRecord | None:
        statement = (
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id == player_id)
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_latest(self, limit: int = 50) -> list[PlayerValueSnapshotRecord]:
        statement = (
            select(PlayerValueSnapshotRecord)
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
