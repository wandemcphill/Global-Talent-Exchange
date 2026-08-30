from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import time
from threading import RLock
from typing import Protocol
from weakref import WeakKeyDictionary

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Club, Competition, Player
from app.market.models import (
    Listing,
    ListingStatus,
    ListingType,
    Offer,
    OfferStatus,
    TradeIntent,
    TradeIntentDirection,
    TradeIntentStatus,
)
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.read_models import PlayerValueSnapshotRecord

import logging

logger = logging.getLogger(__name__)

# Process-level TTL cache for the full tradable-player record set.
#
# list_player_records() is the FULL-fidelity load (every relationship,
# including image_metadata/supply_tier/liquidity_band) used by callers that
# need it: get_market_movers, list_leagues, list_league_clubs,
# list_club_players, list_nationalities, list_nationality_players, and
# offline batch/audit scripts.
#
# list_player_candidates() is a lighter load used by the two highest-traffic
# public endpoints (/market/players and /market/browse/catalog): it carries
# every relationship the filter/sort/search predicates in MarketService read
# (country, club, competition, internal_league) but omits image_metadata,
# supply_tier, and liquidity_band, which those two callers never touch -- the
# list endpoint hydrates only the ~20-50 players on the actual result page
# via get_player_records_by_ids() afterwards. Filtering, sorting and
# pagination all happen in Python on the returned records (the predicates
# depend on multi-source fallbacks -- manual price overrides, summary
# read-models, snapshot JSON -- that cannot be expressed in SQL), so both
# loads still scan *all* ~30k+ tradable players; candidates just does it with
# a smaller object graph per row.
#
# Caching the loaded records turns each into one load per TTL while
# preserving the exact in-Python semantics. Safe to reuse across sessions
# because the session factory sets expire_on_commit=False and every
# relationship the downstream code touches is eager-loaded, so detached
# records stay readable.
#
# Keyed by the bound Engine via a WeakKeyDictionary: distinct test engines get
# distinct entries (no cross-test pollution) and entries evict with the engine.
# Disabled by default (ttl 0); production opts in via
# GTE_MARKET_RECORDS_CACHE_TTL_SECONDS so the test suite keeps fresh-read
# semantics unless a test explicitly enables it.
_RECORDS_CACHE: "WeakKeyDictionary[Engine, tuple[float, list[MarketPlayerRecord]]]" = WeakKeyDictionary()
_RECORDS_CACHE_LOCK = RLock()
_CANDIDATES_CACHE: "WeakKeyDictionary[Engine, tuple[float, list[MarketPlayerRecord]]]" = WeakKeyDictionary()
_CANDIDATES_CACHE_LOCK = RLock()


def _records_cache_ttl_seconds() -> float:
    raw = os.environ.get("GTE_MARKET_RECORDS_CACHE_TTL_SECONDS", "0")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def clear_market_records_cache() -> None:
    """Drop all cached player-record sets (used by tests and on demand)."""
    with _RECORDS_CACHE_LOCK:
        _RECORDS_CACHE.clear()
    with _CANDIDATES_CACHE_LOCK:
        _CANDIDATES_CACHE.clear()


class MarketRepository(Protocol):
    def save_listing(self, listing: Listing) -> Listing: ...

    def save_offer(self, offer: Offer) -> Offer: ...

    def save_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent: ...

    def get_listing(self, listing_id: str) -> Listing | None: ...

    def get_offer(self, offer_id: str) -> Offer | None: ...

    def get_trade_intent(self, intent_id: str) -> TradeIntent | None: ...

    def list_offers_for_listing(self, listing_id: str) -> tuple[Offer, ...]: ...

    def list_offers_for_asset(self, asset_id: str, seller_user_id: str | None = None) -> tuple[Offer, ...]: ...

    def list_trade_intents_for_asset(self, asset_id: str) -> tuple[TradeIntent, ...]: ...

    def list_listings_for_asset(self, asset_id: str) -> tuple[Listing, ...]: ...

    def iter_trade_intents(self) -> tuple[TradeIntent, ...]: ...

    def iter_offers(self) -> tuple[Offer, ...]: ...

    def iter_listings(self) -> tuple[Listing, ...]: ...


@dataclass(slots=True)
class InMemoryMarketRepository:
    _listings: dict[str, Listing] = field(default_factory=dict)
    _offers: dict[str, Offer] = field(default_factory=dict)
    _trade_intents: dict[str, TradeIntent] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def save_listing(self, listing: Listing) -> Listing:
        with self._lock:
            self._listings[listing.listing_id] = listing
        return listing

    def save_offer(self, offer: Offer) -> Offer:
        with self._lock:
            self._offers[offer.offer_id] = offer
        return offer

    def save_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent:
        with self._lock:
            self._trade_intents[trade_intent.intent_id] = trade_intent
        return trade_intent

    def get_listing(self, listing_id: str) -> Listing | None:
        with self._lock:
            return self._listings.get(listing_id)

    def get_offer(self, offer_id: str) -> Offer | None:
        with self._lock:
            return self._offers.get(offer_id)

    def get_trade_intent(self, intent_id: str) -> TradeIntent | None:
        with self._lock:
            return self._trade_intents.get(intent_id)

    def list_offers_for_listing(self, listing_id: str) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(offer for offer in self._offers.values() if offer.listing_id == listing_id)

    def list_offers_for_asset(self, asset_id: str, seller_user_id: str | None = None) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(
                offer
                for offer in self._offers.values()
                if offer.asset_id == asset_id and (seller_user_id is None or offer.seller_user_id == seller_user_id)
            )

    def list_trade_intents_for_asset(self, asset_id: str) -> tuple[TradeIntent, ...]:
        with self._lock:
            return tuple(intent for intent in self._trade_intents.values() if intent.asset_id == asset_id)

    def list_listings_for_asset(self, asset_id: str) -> tuple[Listing, ...]:
        with self._lock:
            return tuple(listing for listing in self._listings.values() if listing.asset_id == asset_id)

    def iter_trade_intents(self) -> tuple[TradeIntent, ...]:
        with self._lock:
            return tuple(self._trade_intents.values())

    def iter_offers(self) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(self._offers.values())

    def iter_listings(self) -> tuple[Listing, ...]:
        with self._lock:
            return tuple(self._listings.values())


@dataclass(slots=True)
class RedisMarketRepository:
    redis_url: str
    key_prefix: str = "gte:market_repository"
    client: Redis = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.client = Redis.from_url(self.redis_url, decode_responses=True)

    def save_listing(self, listing: Listing) -> Listing:
        self._write_json(self._key("listing", listing.listing_id), self._listing_payload(listing))
        self._sadd(self._key("listings"), listing.listing_id)
        self._sadd(self._key("asset", listing.asset_id, "listings"), listing.listing_id)
        return listing

    def save_offer(self, offer: Offer) -> Offer:
        self._write_json(self._key("offer", offer.offer_id), self._offer_payload(offer))
        self._sadd(self._key("offers"), offer.offer_id)
        self._sadd(self._key("asset", offer.asset_id, "offers"), offer.offer_id)
        if offer.listing_id:
            self._sadd(self._key("listing", offer.listing_id, "offers"), offer.offer_id)
        return offer

    def save_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent:
        self._write_json(self._key("intent", trade_intent.intent_id), self._trade_intent_payload(trade_intent))
        self._sadd(self._key("intents"), trade_intent.intent_id)
        self._sadd(self._key("asset", trade_intent.asset_id, "intents"), trade_intent.intent_id)
        return trade_intent

    def get_listing(self, listing_id: str) -> Listing | None:
        payload = self._read_json(self._key("listing", listing_id))
        return None if payload is None else self._to_listing(payload)

    def get_offer(self, offer_id: str) -> Offer | None:
        payload = self._read_json(self._key("offer", offer_id))
        return None if payload is None else self._to_offer(payload)

    def get_trade_intent(self, intent_id: str) -> TradeIntent | None:
        payload = self._read_json(self._key("intent", intent_id))
        return None if payload is None else self._to_trade_intent(payload)

    def list_offers_for_listing(self, listing_id: str) -> tuple[Offer, ...]:
        return tuple(
            offer
            for offer in self._load_objects(self._key("listing", listing_id, "offers"), self.get_offer)
            if offer is not None
        )

    def list_offers_for_asset(self, asset_id: str, seller_user_id: str | None = None) -> tuple[Offer, ...]:
        offers = tuple(
            offer
            for offer in self._load_objects(self._key("asset", asset_id, "offers"), self.get_offer)
            if offer is not None
        )
        if seller_user_id is None:
            return offers
        return tuple(offer for offer in offers if offer.seller_user_id == seller_user_id)

    def list_trade_intents_for_asset(self, asset_id: str) -> tuple[TradeIntent, ...]:
        return tuple(
            intent
            for intent in self._load_objects(self._key("asset", asset_id, "intents"), self.get_trade_intent)
            if intent is not None
        )

    def list_listings_for_asset(self, asset_id: str) -> tuple[Listing, ...]:
        return tuple(
            listing
            for listing in self._load_objects(self._key("asset", asset_id, "listings"), self.get_listing)
            if listing is not None
        )

    def iter_trade_intents(self) -> tuple[TradeIntent, ...]:
        return tuple(
            intent for intent in self._load_objects(self._key("intents"), self.get_trade_intent) if intent is not None
        )

    def iter_offers(self) -> tuple[Offer, ...]:
        return tuple(offer for offer in self._load_objects(self._key("offers"), self.get_offer) if offer is not None)

    def iter_listings(self) -> tuple[Listing, ...]:
        return tuple(
            listing for listing in self._load_objects(self._key("listings"), self.get_listing) if listing is not None
        )

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError:
            logger.exception("market_repository.redis_ping_failed")
            return False

    def _load_objects(self, set_key: str, loader) -> tuple[Listing | Offer | TradeIntent | None, ...]:
        try:
            identifiers = sorted(self.client.smembers(set_key))
        except RedisError:
            logger.exception("market_repository.redis_smembers_failed key=%s", set_key)
            raise RuntimeError("Market repository is unavailable.")
        return tuple(loader(identifier) for identifier in identifiers)

    def _write_json(self, key: str, payload: dict[str, object]) -> None:
        try:
            self.client.set(key, json.dumps(payload))
        except RedisError:
            logger.exception("market_repository.redis_set_failed key=%s", key)
            raise RuntimeError("Market repository is unavailable.")

    def _read_json(self, key: str) -> dict[str, object] | None:
        try:
            raw = self.client.get(key)
        except RedisError:
            logger.exception("market_repository.redis_get_failed key=%s", key)
            raise RuntimeError("Market repository is unavailable.")
        if raw is None:
            return None
        return json.loads(raw)

    def _sadd(self, key: str, value: str) -> None:
        try:
            self.client.sadd(key, value)
        except RedisError:
            logger.exception("market_repository.redis_sadd_failed key=%s", key)
            raise RuntimeError("Market repository is unavailable.")

    def _key(self, *parts: str) -> str:
        return ":".join((self.key_prefix, *parts))

    @staticmethod
    def _listing_payload(listing: Listing) -> dict[str, object]:
        return {
            "listing_id": listing.listing_id,
            "asset_id": listing.asset_id,
            "seller_user_id": listing.seller_user_id,
            "listing_type": listing.listing_type.value,
            "ask_price": listing.ask_price,
            "desired_asset_ids": list(listing.desired_asset_ids),
            "note": listing.note,
            "status": listing.status.value,
            "created_at": listing.created_at.isoformat(),
            "updated_at": listing.updated_at.isoformat(),
        }

    @staticmethod
    def _offer_payload(offer: Offer) -> dict[str, object]:
        return {
            "offer_id": offer.offer_id,
            "asset_id": offer.asset_id,
            "listing_id": offer.listing_id,
            "seller_user_id": offer.seller_user_id,
            "buyer_user_id": offer.buyer_user_id,
            "proposer_user_id": offer.proposer_user_id,
            "recipient_user_id": offer.recipient_user_id,
            "cash_amount": offer.cash_amount,
            "offered_asset_ids": list(offer.offered_asset_ids),
            "note": offer.note,
            "status": offer.status.value,
            "parent_offer_id": offer.parent_offer_id,
            "created_at": offer.created_at.isoformat(),
            "updated_at": offer.updated_at.isoformat(),
        }

    @staticmethod
    def _trade_intent_payload(intent: TradeIntent) -> dict[str, object]:
        return {
            "intent_id": intent.intent_id,
            "user_id": intent.user_id,
            "asset_id": intent.asset_id,
            "direction": intent.direction.value,
            "price_floor": intent.price_floor,
            "price_ceiling": intent.price_ceiling,
            "offered_asset_ids": list(intent.offered_asset_ids),
            "note": intent.note,
            "status": intent.status.value,
            "created_at": intent.created_at.isoformat(),
            "updated_at": intent.updated_at.isoformat(),
        }

    @staticmethod
    def _to_listing(payload: dict[str, object]) -> Listing:
        return Listing(
            listing_id=str(payload["listing_id"]),
            asset_id=str(payload["asset_id"]),
            seller_user_id=str(payload["seller_user_id"]),
            listing_type=ListingType(str(payload["listing_type"])),
            ask_price=int(payload["ask_price"]) if payload.get("ask_price") is not None else None,
            desired_asset_ids=tuple(str(item) for item in list(payload.get("desired_asset_ids") or [])),
            note=str(payload["note"]) if payload.get("note") is not None else None,
            status=ListingStatus(str(payload["status"])),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        )

    @staticmethod
    def _to_offer(payload: dict[str, object]) -> Offer:
        return Offer(
            offer_id=str(payload["offer_id"]),
            asset_id=str(payload["asset_id"]),
            listing_id=str(payload["listing_id"]) if payload.get("listing_id") is not None else None,
            seller_user_id=str(payload["seller_user_id"]),
            buyer_user_id=str(payload["buyer_user_id"]),
            proposer_user_id=str(payload["proposer_user_id"]),
            recipient_user_id=str(payload["recipient_user_id"]),
            cash_amount=int(payload["cash_amount"]),
            offered_asset_ids=tuple(str(item) for item in list(payload.get("offered_asset_ids") or [])),
            note=str(payload["note"]) if payload.get("note") is not None else None,
            status=OfferStatus(str(payload["status"])),
            parent_offer_id=str(payload["parent_offer_id"]) if payload.get("parent_offer_id") is not None else None,
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        )

    @staticmethod
    def _to_trade_intent(payload: dict[str, object]) -> TradeIntent:
        return TradeIntent(
            intent_id=str(payload["intent_id"]),
            user_id=str(payload["user_id"]),
            asset_id=str(payload["asset_id"]),
            direction=TradeIntentDirection(str(payload["direction"])),
            price_floor=int(payload["price_floor"]) if payload.get("price_floor") is not None else None,
            price_ceiling=int(payload["price_ceiling"]) if payload.get("price_ceiling") is not None else None,
            offered_asset_ids=tuple(str(item) for item in list(payload.get("offered_asset_ids") or [])),
            note=str(payload["note"]) if payload.get("note") is not None else None,
            status=TradeIntentStatus(str(payload["status"])),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        )


@dataclass(frozen=True, slots=True)
class MarketPlayerRecord:
    player: Player
    summary: PlayerSummaryReadModel | None
    latest_snapshot: PlayerValueSnapshotRecord | None


@dataclass(slots=True)
class SqlAlchemyMarketPlayerRepository:
    session: Session

    def list_player_records(self) -> list[MarketPlayerRecord]:
        ttl = _records_cache_ttl_seconds()
        if ttl <= 0:
            return self._load_player_records()

        bind = self.session.get_bind()
        if not isinstance(bind, Engine):
            # Connection-bound sessions (e.g. nested transactions) skip the
            # process cache; correctness over the marginal speedup.
            return self._load_player_records()

        now = time.monotonic()
        with _RECORDS_CACHE_LOCK:
            cached = _RECORDS_CACHE.get(bind)
            if cached is not None and (now - cached[0]) < ttl:
                return cached[1]

        records = self._load_player_records()
        with _RECORDS_CACHE_LOCK:
            _RECORDS_CACHE[bind] = (time.monotonic(), records)
        return records

    def _load_player_records(self) -> list[MarketPlayerRecord]:
        players = list(
            self.session.scalars(
                select(Player)
                .options(
                    selectinload(Player.country),
                    selectinload(Player.current_club).selectinload(Club.country),
                    selectinload(Player.current_competition).selectinload(Competition.country),
                    selectinload(Player.current_competition).selectinload(Competition.internal_league),
                    selectinload(Player.internal_league),
                    selectinload(Player.supply_tier),
                    selectinload(Player.liquidity_band),
                    selectinload(Player.image_metadata),
                )
                .where(Player.is_tradable.is_(True))
                .order_by(Player.full_name.asc(), Player.id.asc())
            )
        )
        return self._build_records(players)

    def list_player_candidates(self) -> list[MarketPlayerRecord]:
        """Lighter-weight variant of list_player_records() for the two
        highest-traffic public callers (MarketService.list_players and
        browse_catalog). Carries every relationship their filter/sort/search
        predicates read, but omits image_metadata/supply_tier/liquidity_band,
        which neither caller touches. See the module-level comment above
        _RECORDS_CACHE for the full rationale."""
        ttl = _records_cache_ttl_seconds()
        if ttl <= 0:
            return self._load_player_candidates()

        bind = self.session.get_bind()
        if not isinstance(bind, Engine):
            return self._load_player_candidates()

        now = time.monotonic()
        with _CANDIDATES_CACHE_LOCK:
            cached = _CANDIDATES_CACHE.get(bind)
            if cached is not None and (now - cached[0]) < ttl:
                return cached[1]

        records = self._load_player_candidates()
        with _CANDIDATES_CACHE_LOCK:
            _CANDIDATES_CACHE[bind] = (time.monotonic(), records)
        return records

    def _load_player_candidates(self) -> list[MarketPlayerRecord]:
        players = list(
            self.session.scalars(
                select(Player)
                .options(
                    selectinload(Player.country),
                    selectinload(Player.current_club).selectinload(Club.country),
                    selectinload(Player.current_competition).selectinload(Competition.country),
                    selectinload(Player.current_competition).selectinload(Competition.internal_league),
                    selectinload(Player.internal_league),
                )
                .where(Player.is_tradable.is_(True))
                .order_by(Player.full_name.asc(), Player.id.asc())
            )
        )
        return self._build_records(players)

    def get_player_records_by_ids(self, player_ids: list[str]) -> list[MarketPlayerRecord]:
        """Full-fidelity hydration for a known, small set of player ids --
        used to materialize just the page of results list_players() actually
        returns, after list_player_candidates() has determined which ids
        those are and in what order."""
        if not player_ids:
            return []
        players = list(
            self.session.scalars(
                select(Player)
                .options(
                    selectinload(Player.country),
                    selectinload(Player.current_club).selectinload(Club.country),
                    selectinload(Player.current_competition).selectinload(Competition.country),
                    selectinload(Player.current_competition).selectinload(Competition.internal_league),
                    selectinload(Player.internal_league),
                    selectinload(Player.supply_tier),
                    selectinload(Player.liquidity_band),
                    selectinload(Player.image_metadata),
                )
                .where(Player.id.in_(player_ids), Player.is_tradable.is_(True))
            )
        )
        return self._build_records(players)

    def get_player_record(self, player_id: str) -> MarketPlayerRecord | None:
        player = self.session.scalar(
            select(Player)
            .options(
                selectinload(Player.country),
                selectinload(Player.current_club),
                selectinload(Player.current_competition).selectinload(Competition.country),
                selectinload(Player.current_competition).selectinload(Competition.internal_league),
                selectinload(Player.internal_league),
                selectinload(Player.supply_tier),
                selectinload(Player.liquidity_band),
                selectinload(Player.image_metadata),
            )
            .where(
                Player.id == player_id,
                Player.is_tradable.is_(True),
            )
        )
        if player is None:
            return None
        records = self._build_records([player])
        return records[0] if records else None

    def player_exists(self, player_id: str) -> bool:
        statement = select(Player.id).where(
            Player.id == player_id,
            Player.is_tradable.is_(True),
        )
        return self.session.scalar(statement) is not None

    def list_player_history(self, player_id: str) -> tuple[PlayerValueSnapshotRecord, ...]:
        statement = (
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id == player_id)
            .order_by(
                PlayerValueSnapshotRecord.as_of.desc(),
                PlayerValueSnapshotRecord.created_at.desc(),
                PlayerValueSnapshotRecord.id.desc(),
            )
        )
        return tuple(self.session.scalars(statement))

    def _build_records(self, players: list[Player]) -> list[MarketPlayerRecord]:
        if not players:
            return []

        player_ids = [player.id for player in players]
        summary_statement = select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(player_ids))
        summaries = {summary.player_id: summary for summary in self.session.scalars(summary_statement)}

        latest_snapshots: dict[str, PlayerValueSnapshotRecord] = {}
        snapshot_statement = (
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id.in_(player_ids))
            .order_by(
                PlayerValueSnapshotRecord.player_id.asc(),
                PlayerValueSnapshotRecord.as_of.desc(),
                PlayerValueSnapshotRecord.created_at.desc(),
                PlayerValueSnapshotRecord.id.desc(),
            )
        )
        for snapshot in self.session.scalars(snapshot_statement):
            latest_snapshots.setdefault(snapshot.player_id, snapshot)

        return [
            MarketPlayerRecord(
                player=player,
                summary=summaries.get(player.id),
                latest_snapshot=latest_snapshots.get(player.id),
            )
            for player in players
        ]


def build_market_repository(redis_url: str | None) -> MarketRepository:
    if not redis_url:
        return InMemoryMarketRepository()
    repository = RedisMarketRepository(redis_url)
    if repository.ping():
        return repository
    logger.warning("market_repository.redis_unavailable_falling_back_to_memory")
    return InMemoryMarketRepository()
