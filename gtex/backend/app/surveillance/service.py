from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import PriceBandLimit, Settings
from app.ingestion.models import Player
from app.market.models import ListingStatus, OfferStatus
from app.market.read_models import MarketSummaryReadModel
from app.market.service import MarketEngine
from app.value_engine.read_models import PlayerValueSnapshotRecord

SUSPICIOUS_SIGNAL_TYPES = frozenset(
    {
        "suspicious_purchases",
        "suspicious_sales",
        "suspicious_shortlist_adds",
        "suspicious_watchlist_adds",
        "suspicious_follows",
        "suspicious_transfer_room_adds",
        "suspicious_scouting_activity",
    }
)
OBSERVED_SIGNAL_TYPES = frozenset(
    {
        "purchases",
        "sales",
        "shortlist_adds",
        "watchlist_adds",
        "follows",
        "transfer_room_adds",
        "scouting_activity",
    }
) | SUSPICIOUS_SIGNAL_TYPES
ACTIVE_OFFER_STATUSES = {OfferStatus.PENDING, OfferStatus.COUNTERED, OfferStatus.ACCEPTED}


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_signal_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True, slots=True)
class SuspiciousPlayerAlert:
    player_id: str
    player_name: str
    as_of: datetime
    supply_tier: str | None
    liquidity_band: str | None
    suspicious_events: int
    total_events: int
    suspicious_share: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    target_credits: float
    market_signal_ratio: float
    price_band_code: str
    price_band_min_ratio: float
    price_band_max_ratio: float
    price_band_breach_ratio: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SuspiciousClusterAlert:
    cluster_id: str
    member_user_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    interaction_count: int
    repeated_pair_count: int
    has_cycle: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThinMarketAlert:
    asset_id: str
    ask_price: int | None
    best_offer_price: int | None
    pending_offer_count: int
    active_trade_intent_count: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HolderConcentrationAlert:
    holder_user_id: str
    observed_asset_count: int
    observed_holder_share: float
    asset_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CircularTradeAlert:
    asset_id: str
    cycle_user_ids: tuple[str, ...]
    cycle_length: int
    repetition_count: int
    trade_count: int
    accepted_offer_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(slots=True)
class SurveillanceService:
    settings: Settings

    def list_suspicious_players(
        self,
        session: Session,
        *,
        lookback_days: int = 7,
        limit: int = 50,
    ) -> list[SuspiciousPlayerAlert]:
        threshold = self.settings.suspicion_thresholds
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        latest_snapshots = self._latest_snapshots(session)
        if not latest_snapshots:
            return []

        players = session.scalars(
            select(Player)
            .options(
                selectinload(Player.market_signals),
                selectinload(Player.supply_tier),
                selectinload(Player.liquidity_band),
            )
            .where(Player.id.in_(tuple(latest_snapshots.keys())))
        ).all()

        alerts: list[SuspiciousPlayerAlert] = []
        for player in players:
            snapshot = latest_snapshots.get(player.id)
            if snapshot is None:
                continue
            suspicious_events = 0
            total_events = 0
            for signal in player.market_signals:
                signal_as_of = _coerce_utc(signal.as_of)
                if signal_as_of < cutoff:
                    continue
                signal_type = _normalize_signal_type(signal.signal_type)
                if signal_type not in OBSERVED_SIGNAL_TYPES:
                    continue
                score = max(int(round(signal.score)), 0)
                total_events += score
                if signal_type in SUSPICIOUS_SIGNAL_TYPES:
                    suspicious_events += score
            suspicious_share = round(
                (suspicious_events / total_events) if total_events > 0 else 0.0,
                4,
            )
            market_signal_ratio = round(
                (snapshot.market_signal_value_credits / snapshot.football_truth_value_credits)
                if snapshot.football_truth_value_credits > 0
                else 1.0,
                4,
            )
            price_band = self._resolve_price_band_limit(
                player.liquidity_band.code if player.liquidity_band is not None else None
            )
            price_band_breach_ratio = 0.0
            if market_signal_ratio < price_band.min_ratio:
                price_band_breach_ratio = round(price_band.min_ratio - market_signal_ratio, 4)
            elif market_signal_ratio > price_band.max_ratio:
                price_band_breach_ratio = round(market_signal_ratio - price_band.max_ratio, 4)

            reasons: list[str] = []
            if suspicious_events >= threshold.player_min_suspicious_events:
                reasons.append("suspicious-volume")
            if suspicious_share >= threshold.player_min_suspicious_share:
                reasons.append("suspicious-share")
            if price_band_breach_ratio >= threshold.player_price_band_breach_ratio:
                reasons.append("price-band-breach")
            if not reasons:
                continue
            alerts.append(
                SuspiciousPlayerAlert(
                    player_id=player.id,
                    player_name=player.full_name,
                    as_of=snapshot.as_of,
                    supply_tier=player.supply_tier.code if player.supply_tier is not None else None,
                    liquidity_band=player.liquidity_band.code if player.liquidity_band is not None else None,
                    suspicious_events=suspicious_events,
                    total_events=total_events,
                    suspicious_share=suspicious_share,
                    football_truth_value_credits=round(snapshot.football_truth_value_credits, 2),
                    market_signal_value_credits=round(snapshot.market_signal_value_credits, 2),
                    target_credits=round(snapshot.target_credits, 2),
                    market_signal_ratio=market_signal_ratio,
                    price_band_code=price_band.code,
                    price_band_min_ratio=price_band.min_ratio,
                    price_band_max_ratio=price_band.max_ratio,
                    price_band_breach_ratio=price_band_breach_ratio,
                    reasons=tuple(reasons),
                )
            )
        alerts.sort(
            key=lambda item: (
                item.price_band_breach_ratio,
                item.suspicious_share,
                item.suspicious_events,
                item.target_credits,
            ),
            reverse=True,
        )
        return alerts[:limit]

    def list_suspicious_clusters(
        self,
        market_engine: MarketEngine,
        *,
        limit: int = 50,
    ) -> list[SuspiciousClusterAlert]:
        threshold = self.settings.suspicion_thresholds
        offers = [
            offer
            for offer in market_engine.repository.iter_offers()
            if offer.status in ACTIVE_OFFER_STATUSES
        ]
        adjacency: dict[str, set[str]] = defaultdict(set)
        for offer in offers:
            adjacency[offer.seller_user_id].add(offer.buyer_user_id)
            adjacency[offer.buyer_user_id].add(offer.seller_user_id)

        visited: set[str] = set()
        alerts: list[SuspiciousClusterAlert] = []
        for user_id in sorted(adjacency):
            if user_id in visited:
                continue
            stack = [user_id]
            component: set[str] = set()
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                stack.extend(adjacency[current] - visited)

            if len(component) < threshold.cluster_min_member_count:
                continue

            component_offers = [
                offer
                for offer in offers
                if offer.seller_user_id in component and offer.buyer_user_id in component
            ]
            if len(component_offers) < threshold.cluster_min_interaction_count:
                continue

            asset_ids = tuple(sorted({offer.asset_id for offer in component_offers}))
            pair_counts: dict[tuple[str, str], int] = defaultdict(int)
            directed_edges: set[tuple[str, str]] = set()
            for offer in component_offers:
                pair_counts[tuple(sorted((offer.seller_user_id, offer.buyer_user_id)))] += 1
                directed_edges.add((offer.seller_user_id, offer.buyer_user_id))

            repeated_pair_count = sum(1 for count in pair_counts.values() if count > 1)
            has_cycle = any((right, left) in directed_edges for left, right in directed_edges)
            if not has_cycle and len(component) >= 3 and len(component_offers) >= len(component):
                has_cycle = True

            reasons: list[str] = []
            if len(asset_ids) <= threshold.cluster_max_asset_count:
                reasons.append("activity-concentrated")
            if repeated_pair_count > 0:
                reasons.append("repeated-counterparties")
            if has_cycle:
                reasons.append("cyclical-flow")
            if not reasons:
                continue

            member_ids = tuple(sorted(component))
            alerts.append(
                SuspiciousClusterAlert(
                    cluster_id=f"cluster:{'|'.join(member_ids)}",
                    member_user_ids=member_ids,
                    asset_ids=asset_ids,
                    interaction_count=len(component_offers),
                    repeated_pair_count=repeated_pair_count,
                    has_cycle=has_cycle,
                    reasons=tuple(reasons),
                )
            )
        alerts.sort(
            key=lambda item: (
                item.has_cycle,
                item.repeated_pair_count,
                item.interaction_count,
                -len(item.asset_ids),
            ),
            reverse=True,
        )
        return alerts[:limit]

    def list_thin_market_alerts(
        self,
        session: Session,
        *,
        limit: int = 50,
    ) -> list[ThinMarketAlert]:
        threshold = self.settings.suspicion_thresholds
        summaries = session.scalars(select(MarketSummaryReadModel)).all()
        alerts: list[ThinMarketAlert] = []
        for summary in summaries:
            reference_price = summary.ask_price or summary.best_offer_price or 0
            if reference_price < threshold.thin_market_min_price_credits:
                continue
            if summary.pending_offer_count > threshold.thin_market_max_pending_offers:
                continue
            if summary.active_trade_intent_count > threshold.thin_market_max_active_trade_intents:
                continue
            reasons: list[str] = []
            if summary.pending_offer_count == 0:
                reasons.append("no-pending-offers")
            if summary.active_trade_intent_count == 0:
                reasons.append("no-active-intents")
            if summary.best_offer_price is None:
                reasons.append("no-best-offer")
            alerts.append(
                ThinMarketAlert(
                    asset_id=summary.asset_id,
                    ask_price=summary.ask_price,
                    best_offer_price=summary.best_offer_price,
                    pending_offer_count=summary.pending_offer_count,
                    active_trade_intent_count=summary.active_trade_intent_count,
                    reasons=tuple(reasons),
                )
            )
        alerts.sort(
            key=lambda item: (
                item.ask_price or item.best_offer_price or 0,
                -item.pending_offer_count,
                -item.active_trade_intent_count,
            ),
            reverse=True,
        )
        return alerts[:limit]

    def list_holder_concentration_alerts(
        self,
        market_engine: MarketEngine,
        *,
        limit: int = 50,
    ) -> list[HolderConcentrationAlert]:
        threshold = self.settings.suspicion_thresholds
        asset_events: list[tuple[str, datetime, str]] = []
        for listing in market_engine.repository.iter_listings():
            if listing.status not in {ListingStatus.OPEN, ListingStatus.COMPLETED, ListingStatus.CANCELLED}:
                continue
            asset_events.append((listing.asset_id, listing.updated_at, listing.seller_user_id))
        for offer in market_engine.repository.iter_offers():
            if offer.status is not OfferStatus.ACCEPTED:
                continue
            asset_events.append((offer.asset_id, offer.updated_at, offer.buyer_user_id))
        asset_events.sort(key=lambda item: (item[0], item[1], item[2]))

        holder_by_asset: dict[str, str] = {}
        for asset_id, _event_time, user_id in asset_events:
            holder_by_asset[asset_id] = user_id
        if not holder_by_asset:
            return []

        assets_by_holder: dict[str, list[str]] = defaultdict(list)
        for asset_id, holder_user_id in holder_by_asset.items():
            assets_by_holder[holder_user_id].append(asset_id)

        total_assets = len(holder_by_asset)
        alerts: list[HolderConcentrationAlert] = []
        for holder_user_id, asset_ids in assets_by_holder.items():
            share = round(len(asset_ids) / total_assets, 4)
            if len(asset_ids) < threshold.holder_concentration_min_assets:
                continue
            if share < threshold.holder_concentration_share:
                continue
            alerts.append(
                HolderConcentrationAlert(
                    holder_user_id=holder_user_id,
                    observed_asset_count=len(asset_ids),
                    observed_holder_share=share,
                    asset_ids=tuple(sorted(asset_ids)),
                    reasons=("holder-concentration",),
                )
            )
        alerts.sort(
            key=lambda item: (item.observed_holder_share, item.observed_asset_count),
            reverse=True,
        )
        return alerts[:limit]

    def list_circular_trade_alerts(
        self,
        market_engine: MarketEngine,
        *,
        limit: int = 50,
    ) -> list[CircularTradeAlert]:
        threshold = self.settings.suspicion_thresholds
        accepted_offers_by_asset: dict[str, list] = defaultdict(list)
        for offer in market_engine.repository.iter_offers():
            if offer.status is OfferStatus.ACCEPTED:
                accepted_offers_by_asset[offer.asset_id].append(offer)

        alerts: list[CircularTradeAlert] = []
        for asset_id, offers in accepted_offers_by_asset.items():
            ordered_offers = sorted(offers, key=lambda offer: (offer.updated_at, offer.created_at, offer.offer_id))
            if len(ordered_offers) < threshold.circular_trade_min_cycle_length:
                continue

            owners = [ordered_offers[0].seller_user_id]
            offer_ids: list[str] = []
            cycles: list[tuple[str, ...]] = []
            for offer in ordered_offers:
                offer_ids.append(offer.offer_id)
                owners.append(offer.buyer_user_id)
                current_index = len(owners) - 1
                current_owner = owners[current_index]
                for previous_index in range(current_index - threshold.circular_trade_min_cycle_length + 1):
                    if owners[previous_index] != current_owner:
                        continue
                    cycle_users = owners[previous_index:current_index]
                    unique_users = tuple(dict.fromkeys(cycle_users))
                    if len(unique_users) < threshold.circular_trade_min_cycle_length:
                        continue
                    cycles.append(unique_users)
                    break

            if len(cycles) < threshold.circular_trade_min_repetitions:
                continue

            cycle_user_ids = cycles[-1]
            alerts.append(
                CircularTradeAlert(
                    asset_id=asset_id,
                    cycle_user_ids=cycle_user_ids,
                    cycle_length=len(cycle_user_ids),
                    repetition_count=len(cycles),
                    trade_count=len(ordered_offers),
                    accepted_offer_ids=tuple(offer_ids),
                    reasons=("circular-trade",),
                )
            )
        alerts.sort(
            key=lambda item: (item.repetition_count, item.trade_count, item.cycle_length),
            reverse=True,
        )
        return alerts[:limit]

    def _latest_snapshots(self, session: Session) -> dict[str, PlayerValueSnapshotRecord]:
        snapshots = session.scalars(
            select(PlayerValueSnapshotRecord)
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
        ).all()
        latest_by_player: dict[str, PlayerValueSnapshotRecord] = {}
        for snapshot in snapshots:
            latest_by_player.setdefault(snapshot.player_id, snapshot)
        return latest_by_player

    def _resolve_price_band_limit(self, liquidity_band_code: str | None) -> PriceBandLimit:
        lookup = {limit.code: limit for limit in self.settings.value_engine_weighting.price_band_limits}
        if liquidity_band_code is not None:
            normalized = liquidity_band_code.strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in lookup:
                return lookup[normalized]
        return lookup.get("default") or self.settings.value_engine_weighting.price_band_limits[0]
