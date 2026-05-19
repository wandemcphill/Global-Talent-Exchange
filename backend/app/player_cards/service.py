from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.economy.economy_service import EconomyService
from app.football_events_engine.service import RealWorldFootballEventService
from app.ingestion.models import Country, MarketSignal, Player
from app.integrity_engine.service import IntegrityEngineService
from app.market.player_eligibility_policy import is_card_mint_eligible, is_preseeded_national_regen
from app.models.base import generate_uuid
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.player_cards import (
    PlayerAlias,
    PlayerCard,
    PlayerCardEffect,
    PlayerCardFormBuff,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardListing,
    PlayerCardMomentum,
    PlayerCardOwnerHistory,
    PlayerCardSale,
    PlayerCardSupplyBatch,
    PlayerCardTier,
    PlayerCardWatchlist,
    PlayerMarketValueSnapshot,
    PlayerMoniker,
    PlayerStatsSnapshot,
)
from app.models.risk_ops import SystemEventSeverity
from app.models.user import User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.players.read_models import PlayerSummaryReadModel
from app.players.football_integrity import calculate_gsi, gsi_band, normalize_position
from app.risk_ops_engine.service import RiskOpsService
from app.services.avatar_service import AvatarService
from app.services.regen_portrait_service import RegenPortraitError, RegenPortraitService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_TRADE_FEE_BPS = 2000


class PlayerCardMarketError(ValueError):
    pass


class PlayerCardNotFoundError(PlayerCardMarketError):
    pass


class PlayerCardValidationError(PlayerCardMarketError):
    pass


class PlayerCardPermissionError(PlayerCardMarketError):
    pass


@dataclass(slots=True)
class PlayerCardMarketService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    avatar_service: AvatarService = field(default_factory=AvatarService)

    def list_players(self, *, search: str | None = None, limit: int = 20, offset: int = 0) -> list[dict[str, object]]:
        supply_subq = (
            select(PlayerCard.player_id, func.coalesce(func.sum(PlayerCard.supply_total), 0).label("supply_total"))
            .group_by(PlayerCard.player_id)
            .subquery()
        )
        stmt = (
            select(
                Player,
                supply_subq.c.supply_total,
                PlayerSummaryReadModel.current_value_credits,
                PlayerSummaryReadModel.current_club_name,
                PlayerSummaryReadModel.summary_json,
            )
            .outerjoin(supply_subq, supply_subq.c.player_id == Player.id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        )

        if search:
            term = f"%{search.strip()}%"
            stmt = (
                stmt.outerjoin(PlayerAlias, PlayerAlias.player_id == Player.id)
                .outerjoin(PlayerMoniker, PlayerMoniker.player_id == Player.id)
                .where(
                    or_(
                        Player.full_name.ilike(term),
                        Player.short_name.ilike(term),
                        PlayerAlias.alias.ilike(term),
                        PlayerMoniker.moniker.ilike(term),
                    )
                )
                .distinct()
            )

        stmt = stmt.order_by(Player.full_name.asc()).offset(offset).limit(limit)
        rows = self.session.execute(stmt).all()
        results: list[dict[str, object]] = []
        for player, supply_total, current_value_credits, current_club_name, summary_json in rows:
            global_scouting_index = self._global_scouting_index(player, summary_payload=summary_json)
            results.append(
                {
                    "player_id": player.id,
                    "player_name": player.full_name,
                    "position": self._position_code(player),
                    "global_scouting_index": global_scouting_index,
                    "gsi_band": gsi_band(global_scouting_index),
                    "nationality_code": player.country.alpha2_code if player.country is not None else None,
                    "current_club_name": current_club_name
                    or (player.current_club.name if player.current_club is not None else None),
                    "card_supply_total": int(supply_total or 0),
                    "latest_value_credits": float(current_value_credits) if current_value_credits is not None else None,
                    "avatar": self._avatar_payload(player),
                    "image_url": self._image_url(player),
                }
            )
        return results

    def _active_trading_fee_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        return int(rule.trading_fee_bps if rule is not None else DEFAULT_TRADE_FEE_BPS)

    def get_player_detail(self, *, player_id: str) -> dict[str, object]:
        player = self.session.get(Player, player_id)
        if player is None:
            raise PlayerCardNotFoundError("Player was not found.")
        real_world_impact = RealWorldFootballEventService(self.session).get_player_impact(player.id)

        tiers = {tier.id: tier for tier in self.session.scalars(select(PlayerCardTier)).all()}
        cards = list(self.session.scalars(select(PlayerCard).where(PlayerCard.player_id == player.id)).all())
        aliases = [
            row.alias
            for row in self.session.scalars(select(PlayerAlias).where(PlayerAlias.player_id == player.id)).all()
        ]
        monikers = [
            row.moniker
            for row in self.session.scalars(
                select(PlayerMoniker).where(PlayerMoniker.player_id == player.id, PlayerMoniker.is_active.is_(True))
            ).all()
        ]
        effects = list(
            self.session.scalars(
                select(PlayerCardEffect)
                .join(PlayerCard, PlayerCardEffect.player_card_id == PlayerCard.id)
                .where(PlayerCard.player_id == player.id)
            ).all()
        )
        buffs = list(
            self.session.scalars(
                select(PlayerCardFormBuff)
                .join(PlayerCard, PlayerCardFormBuff.player_card_id == PlayerCard.id)
                .where(PlayerCard.player_id == player.id)
            ).all()
        )
        momentum = self.session.scalar(select(PlayerCardMomentum).where(PlayerCardMomentum.player_id == player.id))
        latest_stats = self.session.scalar(
            select(PlayerStatsSnapshot)
            .where(PlayerStatsSnapshot.player_id == player.id)
            .order_by(PlayerStatsSnapshot.as_of.desc())
        )
        latest_market_snapshot = self.session.scalar(
            select(PlayerMarketValueSnapshot)
            .where(PlayerMarketValueSnapshot.player_id == player.id)
            .order_by(PlayerMarketValueSnapshot.as_of.desc())
        )

        card_views: list[dict[str, object]] = []
        for card in cards:
            tier = tiers.get(card.tier_id)
            card_views.append(
                {
                    "card_id": card.id,
                    "player_id": card.player_id,
                    "tier": self._tier_payload(tier) if tier else None,
                    "edition_code": card.edition_code,
                    "display_name": card.display_name,
                    "season_label": card.season_label,
                    "card_variant": card.card_variant,
                    "supply_total": card.supply_total,
                    "supply_available": card.supply_available,
                    "is_active": card.is_active,
                }
            )

        global_scouting_index = self._global_scouting_index(player)
        return {
            "player_id": player.id,
            "player_name": player.full_name,
            "position": self._position_code(player),
            "global_scouting_index": global_scouting_index,
            "gsi_band": gsi_band(global_scouting_index),
            "nationality_code": player.country.alpha2_code if player.country is not None else None,
            "current_club_name": player.current_club.name if player.current_club is not None else None,
            "avatar": self._avatar_payload(player),
            "image_url": self._image_url(player),
            "aliases": aliases,
            "monikers": monikers,
            "cards": card_views,
            "effects": [self._effect_payload(effect) for effect in effects],
            "form_buffs": [self._buff_payload(buff) for buff in buffs],
            "momentum": self._momentum_payload(momentum) if momentum else None,
            "latest_stats_snapshot": self._stats_payload(latest_stats) if latest_stats else None,
            "latest_market_snapshot": (
                self._market_snapshot_payload(latest_market_snapshot) if latest_market_snapshot else None
            ),
            "real_world_flags": [self._trending_flag_payload(flag) for flag in real_world_impact.active_flags],
            "real_world_form_modifiers": [
                self._player_form_modifier_payload(item) for item in real_world_impact.active_form_modifiers
            ],
            "demand_signals": [self._demand_signal_payload(item) for item in real_world_impact.active_demand_signals],
            "recommendation_priority_delta": real_world_impact.recommendation_priority_delta,
            "market_buzz_score": real_world_impact.market_buzz_score,
        }

    def list_inventory(self, *, actor: User) -> list[dict[str, object]]:
        stmt = (
            select(PlayerCardHolding, PlayerCard, PlayerCardTier, Player)
            .join(PlayerCard, PlayerCardHolding.player_card_id == PlayerCard.id)
            .join(PlayerCardTier, PlayerCard.tier_id == PlayerCardTier.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(PlayerCardHolding.owner_user_id == actor.id)
            .order_by(PlayerCardHolding.updated_at.desc())
        )
        rows = self.session.execute(stmt).all()
        inventory: list[dict[str, object]] = []
        for holding, card, tier, player in rows:
            available = holding.quantity_total - holding.quantity_reserved
            if holding.quantity_total <= 0:
                continue
            summary = self._player_summary(player.id)
            global_scouting_index = self._global_scouting_index(player, summary=summary)
            inventory.append(
                {
                    "holding_id": holding.id,
                    "player_card_id": card.id,
                    "player_id": player.id,
                    "player_name": player.full_name,
                    "global_scouting_index": global_scouting_index,
                    "gsi_band": gsi_band(global_scouting_index),
                    "avatar": self._avatar_payload(player, summary=summary),
                    "image_url": self._image_url(player, summary=summary),
                    "latest_value_credits": self._latest_value_credits(
                        player.id,
                        summary=summary,
                    ),
                    "tier_code": tier.code,
                    "tier_name": tier.name,
                    "edition_code": card.edition_code,
                    "quantity_total": holding.quantity_total,
                    "quantity_reserved": holding.quantity_reserved,
                    "quantity_available": max(available, 0),
                    "last_acquired_at": holding.last_acquired_at,
                }
            )
        return inventory

    def list_listings(
        self,
        *,
        status: str = "open",
        player_id: str | None = None,
        tier_id: str | None = None,
        seller_user_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        stmt = (
            select(PlayerCardListing, PlayerCard, PlayerCardTier, Player)
            .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
            .join(PlayerCardTier, PlayerCard.tier_id == PlayerCardTier.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(PlayerCardListing.status == status)
        )
        if player_id:
            stmt = stmt.where(Player.id == player_id)
        if tier_id:
            stmt = stmt.where(PlayerCardTier.id == tier_id)
        if seller_user_id:
            stmt = stmt.where(PlayerCardListing.seller_user_id == seller_user_id)
        stmt = stmt.order_by(PlayerCardListing.created_at.desc()).limit(limit)
        rows = self.session.execute(stmt).all()
        listings: list[dict[str, object]] = []
        for listing, card, tier, player in rows:
            listings.append(self._listing_payload(listing, card, tier, player))
        return listings

    def create_listing(
        self, *, actor: User, player_card_id: str, quantity: int, price_per_card_credits: Decimal
    ) -> dict[str, object]:
        if quantity <= 0:
            raise PlayerCardValidationError("Listing quantity must be positive.")
        if price_per_card_credits <= Decimal("0"):
            raise PlayerCardValidationError("Listing price must be positive.")

        card = self._get_card(player_card_id)
        if not card.is_active:
            raise PlayerCardValidationError("This player card is not active.")
        holding = self._get_holding(actor.id, player_card_id)
        available = holding.quantity_total - holding.quantity_reserved
        if available < quantity:
            raise PlayerCardValidationError("Not enough available card copies to list.")

        holding.quantity_reserved += quantity
        listing = PlayerCardListing(
            listing_id=self._new_id("pcl"),
            player_card_id=card.id,
            seller_user_id=actor.id,
            quantity=quantity,
            price_per_card_credits=self._normalize_amount(price_per_card_credits),
            status="open",
            metadata_json={},
        )
        self.session.add(listing)
        self._append_card_history(
            card.id, "listing.created", actor.id, delta_available=-quantity, metadata={"listing_id": listing.listing_id}
        )
        self._append_owner_history(
            card.id,
            from_user_id=actor.id,
            to_user_id=None,
            quantity=quantity,
            event_type="listed",
            reference_id=listing.listing_id,
        )
        self.session.flush()
        self._publish_event(
            "player_card.listing.created",
            {
                "listing_id": listing.listing_id,
                "player_card_id": card.id,
                "player_id": card.player_id,
                "seller_user_id": actor.id,
                "quantity": quantity,
                "price_per_card_credits": str(price_per_card_credits),
            },
        )
        self._publish_event(
            "market.listing.created",
            {"asset_id": card.player_id, "listing_id": listing.listing_id, "price": float(price_per_card_credits)},
        )
        return self._listing_payload(listing, card, self._get_tier(card.tier_id), self._get_player(card.player_id))

    def cancel_listing(self, *, actor: User, listing_id: str) -> dict[str, object]:
        listing = self._get_listing(listing_id)
        if listing.status != "open":
            raise PlayerCardValidationError("Listing is not open.")
        if listing.seller_user_id != actor.id:
            raise PlayerCardPermissionError("Only the listing owner can cancel this listing.")
        card = self._get_card(listing.player_card_id)
        holding = self._get_holding(actor.id, listing.player_card_id)
        holding.quantity_reserved = max(holding.quantity_reserved - listing.quantity, 0)
        listing.status = "cancelled"
        self._append_card_history(
            card.id,
            "listing.cancelled",
            actor.id,
            delta_available=listing.quantity,
            metadata={"listing_id": listing.listing_id},
        )
        self._append_owner_history(
            card.id,
            from_user_id=actor.id,
            to_user_id=None,
            quantity=listing.quantity,
            event_type="listing_cancelled",
            reference_id=listing.listing_id,
        )
        self.session.flush()
        self._publish_event(
            "player_card.listing.cancelled",
            {
                "listing_id": listing.listing_id,
                "player_card_id": card.id,
                "player_id": card.player_id,
                "seller_user_id": actor.id,
            },
        )
        return self._listing_payload(listing, card, self._get_tier(card.tier_id), self._get_player(card.player_id))

    def buy_listing(self, *, actor: User, listing_id: str, quantity: int | None = None) -> dict[str, object]:
        listing = self._get_listing(listing_id)
        if listing.status != "open":
            raise PlayerCardValidationError("Listing is not open.")
        if listing.seller_user_id == actor.id:
            raise PlayerCardValidationError("You cannot buy your own listing.")
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Admin accounts cannot buy player cards outside approved liquidity flows.")
        if quantity is None:
            quantity = listing.quantity
        if quantity <= 0 or quantity > listing.quantity:
            raise PlayerCardValidationError("Purchase quantity is invalid.")

        card = self._get_card(listing.player_card_id)
        seller = self.session.get(User, listing.seller_user_id)
        if seller is None:
            raise PlayerCardValidationError("Seller account was not found.")

        gross = self._normalize_amount(Decimal(listing.price_per_card_credits) * Decimal(quantity))
        settlement_reference = f"player-card-sale:{listing.listing_id}:{self._new_id('settle')}"
        if self._settlement_exists(settlement_reference):
            raise PlayerCardMarketError("This sale has already been settled.")
        settlement = EconomyService(self.session, wallet_service=self.wallet_service).settle_marketplace_transaction(
            buyer=actor,
            seller=seller,
            gross_amount=gross,
            unit=LedgerUnit.COIN,
            reference=settlement_reference,
            external_reference=settlement_reference,
            description="Player card marketplace trade",
            buyer_source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
            seller_source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
            fee_source_tag=LedgerSourceTag.TRADING_FEE_BURN,
            fee_bps=self._active_trading_fee_bps(),
            burn_fee=True,
            actor=actor,
            metadata={
                "player_card_sale": {
                    "listing_id": listing.listing_id,
                    "player_card_id": card.id,
                    "quantity": quantity,
                }
            },
        )
        fee = settlement.fee_amount
        seller_net = settlement.seller_net_amount

        seller_holding = self._get_holding(seller.id, card.id)
        seller_holding.quantity_reserved = max(seller_holding.quantity_reserved - quantity, 0)
        seller_holding.quantity_total = max(seller_holding.quantity_total - quantity, 0)
        if seller_holding.quantity_total == 0:
            self.session.delete(seller_holding)

        buyer_holding = self._get_or_create_holding(actor.id, card.id)
        buyer_holding.quantity_total += quantity
        buyer_holding.last_acquired_at = datetime.now(UTC)

        if quantity == listing.quantity:
            listing.status = "sold"
        else:
            listing.quantity -= quantity

        sale = PlayerCardSale(
            sale_id=self._new_id("pcs"),
            listing_id=listing.listing_id,
            player_card_id=card.id,
            seller_user_id=seller.id,
            buyer_user_id=actor.id,
            quantity=quantity,
            price_per_card_credits=self._normalize_amount(listing.price_per_card_credits),
            gross_credits=gross,
            fee_credits=fee,
            seller_net_credits=seller_net,
            status="settled",
            settlement_reference=settlement_reference,
            metadata_json={},
        )
        self.session.add(sale)

        self._append_owner_history(
            card.id,
            from_user_id=seller.id,
            to_user_id=actor.id,
            quantity=quantity,
            event_type="sold",
            reference_id=sale.sale_id,
        )
        self._append_card_history(
            card.id, "sale.completed", actor.id, metadata={"sale_id": sale.sale_id, "listing_id": listing.listing_id}
        )
        self._record_market_signal(card.player_id, sale, actor, seller)
        self._record_market_snapshot(card.player_id)
        self._update_momentum(card.player_id)
        self.session.flush()
        self._run_integrity_checks(card, sale)

        self._publish_event(
            "player_card.sale.completed",
            {
                "sale_id": sale.sale_id,
                "listing_id": listing.listing_id,
                "player_card_id": card.id,
                "player_id": card.player_id,
                "seller_user_id": seller.id,
                "buyer_user_id": actor.id,
                "quantity": quantity,
                "price_per_card_credits": str(listing.price_per_card_credits),
                "gross_credits": str(gross),
                "fee_credits": str(fee),
            },
        )
        self._publish_event(
            "market.execution.recorded",
            {
                "execution_id": sale.sale_id,
                "asset_id": card.player_id,
                "price": float(listing.price_per_card_credits),
                "quantity": quantity,
                "seller_user_id": seller.id,
                "buyer_user_id": actor.id,
            },
        )

        return {
            "sale_id": sale.sale_id,
            "listing_id": sale.listing_id,
            "player_card_id": sale.player_card_id,
            "seller_user_id": sale.seller_user_id,
            "buyer_user_id": sale.buyer_user_id,
            "quantity": sale.quantity,
            "price_per_card_credits": sale.price_per_card_credits,
            "gross_credits": sale.gross_credits,
            "fee_credits": sale.fee_credits,
            "seller_net_credits": sale.seller_net_credits,
            "status": sale.status,
            "settlement_reference": sale.settlement_reference,
            "created_at": sale.created_at,
        }

    def add_watchlist(
        self, *, actor: User, player_id: str, player_card_id: str | None, notes: str | None
    ) -> PlayerCardWatchlist:
        watch = self.session.scalar(
            select(PlayerCardWatchlist).where(
                PlayerCardWatchlist.user_id == actor.id,
                PlayerCardWatchlist.player_id == player_id,
                PlayerCardWatchlist.player_card_id == player_card_id,
            )
        )
        if watch is not None:
            watch.notes = notes
            self.session.flush()
            return watch
        watch = PlayerCardWatchlist(
            user_id=actor.id, player_id=player_id, player_card_id=player_card_id, notes=notes, metadata_json={}
        )
        self.session.add(watch)
        self.session.flush()
        return watch

    def list_watchlist(self, *, actor: User) -> list[PlayerCardWatchlist]:
        stmt = (
            select(PlayerCardWatchlist)
            .where(PlayerCardWatchlist.user_id == actor.id)
            .order_by(PlayerCardWatchlist.updated_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def remove_watchlist(self, *, actor: User, watchlist_id: str) -> None:
        watch = self.session.get(PlayerCardWatchlist, watchlist_id)
        if watch is None or watch.user_id != actor.id:
            raise PlayerCardNotFoundError("Watchlist entry was not found.")
        self.session.delete(watch)
        self.session.flush()

    def apply_supply_batch(
        self,
        *,
        actor: User,
        player_id: str,
        tier_code: str,
        quantity: int,
        edition_code: str,
        season_label: str | None,
        batch_key: str,
        owner_user_id: str | None,
        source_type: str,
        source_reference: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> PlayerCardSupplyBatch:
        if quantity <= 0:
            raise PlayerCardValidationError("Supply quantity must be positive.")
        player = self._get_player(player_id, actor=actor)
        tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == tier_code))
        if tier is None:
            raise PlayerCardValidationError("Card tier was not found.")

        existing_batch = self.session.scalar(
            select(PlayerCardSupplyBatch).where(PlayerCardSupplyBatch.batch_key == batch_key)
        )
        if existing_batch is not None:
            return existing_batch

        card = self.session.scalar(
            select(PlayerCard).where(
                PlayerCard.player_id == player.id,
                PlayerCard.tier_id == tier.id,
                PlayerCard.edition_code == edition_code,
            )
        )
        if card is None:
            card = PlayerCard(
                player_id=player.id,
                tier_id=tier.id,
                edition_code=edition_code,
                display_name=f"{player.full_name} {tier.name}",
                season_label=season_label,
                card_variant="base",
                supply_total=0,
                supply_available=0,
                metadata_json={},
            )
            self.session.add(card)
            self.session.flush()

        batch = PlayerCardSupplyBatch(
            batch_key=batch_key,
            player_card_id=card.id,
            player_id=player.id,
            tier_id=tier.id,
            quantity=quantity,
            status="applied",
            source_type=source_type,
            source_reference=source_reference,
            minted_by_user_id=actor.id,
            assigned_user_id=owner_user_id,
            metadata_json=metadata or {},
        )
        self.session.add(batch)
        card.supply_total += quantity
        card.supply_available += quantity
        self._append_card_history(
            card.id,
            "supply.batch",
            actor.id,
            delta_supply=quantity,
            delta_available=quantity,
            metadata={"batch_key": batch_key},
        )

        if owner_user_id:
            holding = self._get_or_create_holding(owner_user_id, card.id)
            holding.quantity_total += quantity
            holding.last_acquired_at = datetime.now(UTC)
            self._append_owner_history(
                card.id,
                from_user_id=None,
                to_user_id=owner_user_id,
                quantity=quantity,
                event_type="minted",
                reference_id=batch_key,
            )
        self.session.flush()
        return batch

    def apply_preseeded_national_regen_supply_batch(
        self,
        *,
        actor: User,
        seed_id: str,
        tier_code: str,
        quantity: int,
        edition_code: str,
        season_label: str | None,
        batch_key: str | None,
        owner_user_id: str | None,
        source_reference: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> PlayerCardSupplyBatch:
        seed = self.session.get(NationalRegenSeed, seed_id)
        if seed is None:
            raise PlayerCardNotFoundError("Preseeded regen seed was not found.")
        if not is_preseeded_national_regen(seed):
            raise PlayerCardValidationError("Only preseeded national regen seeds can use this mint path.")

        player = self._ensure_player_from_national_seed(seed, actor=actor)
        resolved_batch_key = (batch_key or "").strip()
        if not resolved_batch_key:
            fingerprint = f"{seed.id}:{tier_code}:{edition_code}:{owner_user_id or 'unassigned'}:{quantity}"
            resolved_batch_key = f"national-seed:{fingerprint}".lower()

        metadata_payload = dict(metadata or {})
        metadata_payload.update(
            {
                "national_seed_id": seed.id,
                "national_seed_key": seed.seed_key,
                "source_type": "national_seed",
                "source_bucket": "preseeded",
                "is_preseeded_national_regen": True,
                "admin_trade_enabled": True,
                "admin_mint_enabled": True,
            }
        )
        batch = self.apply_supply_batch(
            actor=actor,
            player_id=player.id,
            tier_code=tier_code,
            quantity=quantity,
            edition_code=edition_code,
            season_label=season_label,
            batch_key=resolved_batch_key,
            owner_user_id=owner_user_id,
            source_type="admin_preseeded_regen_mint",
            source_reference=source_reference or seed.seed_key,
            metadata=metadata_payload,
        )

        card = self.session.get(PlayerCard, batch.player_card_id)
        if card is not None:
            card.card_variant = "preseeded_regen"
            card.metadata_json = {
                **dict(card.metadata_json or {}),
                "national_seed_id": seed.id,
                "national_seed_key": seed.seed_key,
                "source_type": "national_seed",
                "source_bucket": "preseeded",
                "is_preseeded_national_regen": True,
                "admin_trade_enabled": True,
            }
        self.session.flush()
        return batch

    def _record_market_signal(self, player_id: str, sale: PlayerCardSale, buyer: User, seller: User) -> None:
        signal = MarketSignal(
            source_provider="player_card_market",
            provider_external_id=sale.sale_id,
            player_id=player_id,
            signal_type="trade_print_price_credits",
            score=float(sale.price_per_card_credits),
            as_of=datetime.now(UTC),
            notes=json.dumps(
                {
                    "sale_id": sale.sale_id,
                    "listing_id": sale.listing_id,
                    "seller_user_id": seller.id,
                    "buyer_user_id": buyer.id,
                    "quantity": sale.quantity,
                }
            ),
        )
        self.session.merge(signal)

    def _record_market_snapshot(self, player_id: str) -> None:
        now = datetime.now(UTC)
        window_start = now - timedelta(hours=24)
        sales_rows = self.session.execute(
            select(PlayerCardSale.price_per_card_credits, PlayerCardSale.quantity)
            .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
            .where(PlayerCard.player_id == player_id, PlayerCardSale.created_at >= window_start)
            .order_by(PlayerCardSale.created_at.desc())
        ).all()
        total_qty = sum(int(row.quantity) for row in sales_rows)
        weighted_total = sum(
            self._normalize_amount(row.price_per_card_credits) * int(row.quantity) for row in sales_rows
        )
        avg_price = None
        high_price = None
        low_price = None
        if sales_rows:
            prices = [self._normalize_amount(row.price_per_card_credits) for row in sales_rows]
            high_price = max(prices)
            low_price = min(prices)
            if total_qty > 0:
                avg_price = self._normalize_amount(weighted_total / Decimal(total_qty))

        floor_price = self.session.scalar(
            select(func.min(PlayerCardListing.price_per_card_credits))
            .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
            .where(PlayerCard.player_id == player_id, PlayerCardListing.status == "open")
        )
        listing_count = (
            self.session.scalar(
                select(func.count(PlayerCardListing.id))
                .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
                .where(PlayerCard.player_id == player_id, PlayerCardListing.status == "open")
            )
            or 0
        )

        snapshot = PlayerMarketValueSnapshot(
            player_id=player_id,
            as_of=now,
            last_trade_price_credits=(
                float(self._normalize_amount(sales_rows[0].price_per_card_credits)) if sales_rows else None
            ),
            avg_trade_price_credits=float(avg_price) if avg_price is not None else None,
            volume_24h=int(total_qty),
            listing_floor_price_credits=float(self._normalize_amount(floor_price)) if floor_price is not None else None,
            listing_count=int(listing_count),
            high_24h_price_credits=float(high_price) if high_price is not None else None,
            low_24h_price_credits=float(low_price) if low_price is not None else None,
            metadata_json={},
        )
        self.session.add(snapshot)

    def _update_momentum(self, player_id: str) -> None:
        avg_7d = self._average_trade_price(player_id, days=7)
        avg_30d = self._average_trade_price(player_id, days=30)
        momentum_7d = Decimal("0")
        momentum_30d = Decimal("0")
        if avg_30d and avg_30d > Decimal("0"):
            momentum_7d = ((avg_7d or avg_30d) - avg_30d) / avg_30d * Decimal("100")
            momentum_30d = ((avg_7d or avg_30d) - avg_30d) / avg_30d * Decimal("100")
        trend = "flat"
        if momentum_7d > Decimal("2"):
            trend = "up"
        elif momentum_7d < Decimal("-2"):
            trend = "down"
        momentum = self.session.scalar(select(PlayerCardMomentum).where(PlayerCardMomentum.player_id == player_id))
        if momentum is None:
            momentum = PlayerCardMomentum(player_id=player_id, metadata_json={})
            self.session.add(momentum)
        momentum.last_trade_price_credits = float(avg_7d) if avg_7d is not None else momentum.last_trade_price_credits
        momentum.momentum_7d_pct = float(momentum_7d)
        momentum.momentum_30d_pct = float(momentum_30d)
        momentum.trend_direction = trend

    def _average_trade_price(self, player_id: str, *, days: int) -> Decimal | None:
        window_start = datetime.now(UTC) - timedelta(days=days)
        sales_rows = self.session.execute(
            select(PlayerCardSale.price_per_card_credits, PlayerCardSale.quantity)
            .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
            .where(PlayerCard.player_id == player_id, PlayerCardSale.created_at >= window_start)
        ).all()
        if not sales_rows:
            return None
        total_qty = sum(int(row.quantity) for row in sales_rows)
        if total_qty == 0:
            return None
        weighted_total = sum(
            self._normalize_amount(row.price_per_card_credits) * int(row.quantity) for row in sales_rows
        )
        return self._normalize_amount(weighted_total / Decimal(total_qty))

    def _run_integrity_checks(self, card: PlayerCard, sale: PlayerCardSale) -> None:
        now = datetime.now(UTC)
        integrity_service = IntegrityEngineService(self.session)
        risk_service = RiskOpsService(self.session)

        lookback_7d = now - timedelta(days=7)
        pair_count = (
            self.session.scalar(
                select(func.count(PlayerCardSale.id)).where(
                    PlayerCardSale.created_at >= lookback_7d,
                    or_(
                        and_(
                            PlayerCardSale.seller_user_id == sale.seller_user_id,
                            PlayerCardSale.buyer_user_id == sale.buyer_user_id,
                        ),
                        and_(
                            PlayerCardSale.seller_user_id == sale.buyer_user_id,
                            PlayerCardSale.buyer_user_id == sale.seller_user_id,
                        ),
                    ),
                )
            )
            or 0
        )
        if pair_count >= 3:
            subject = f"pair:{sale.seller_user_id}:{sale.buyer_user_id}"
            integrity_service.register_incident_once(
                user_id=sale.seller_user_id,
                incident_type="repeated_card_trade_pair",
                subject=subject,
                severity="high" if pair_count >= 5 else "medium",
                title="Repeated card trading pair detected",
                description=f"{pair_count} trades between the same pair in the last 7 days.",
                score_delta=Decimal("-12.50"),
                metadata_json={"pair": [sale.seller_user_id, sale.buyer_user_id], "count": int(pair_count)},
            )
            integrity_service.register_incident_once(
                user_id=sale.buyer_user_id,
                incident_type="repeated_card_trade_pair",
                subject=subject,
                severity="high" if pair_count >= 5 else "medium",
                title="Repeated card trading pair detected",
                description=f"{pair_count} trades between the same pair in the last 7 days.",
                score_delta=Decimal("-12.50"),
                metadata_json={"pair": [sale.seller_user_id, sale.buyer_user_id], "count": int(pair_count)},
            )

        lookback_24h = now - timedelta(hours=24)
        churn_count = (
            self.session.scalar(
                select(func.count(PlayerCardSale.id)).where(
                    PlayerCardSale.player_card_id == sale.player_card_id,
                    PlayerCardSale.created_at >= lookback_24h,
                )
            )
            or 0
        )
        if churn_count >= 6:
            subject = f"asset:{sale.player_card_id}:{now:%Y%m%d}"
            integrity_service.register_incident_once(
                user_id=sale.seller_user_id,
                incident_type="card_asset_churn",
                subject=subject,
                severity="medium",
                title="Card asset churn detected",
                description="Repeated trades of the same card asset were detected in a short window.",
                score_delta=Decimal("-7.50"),
                metadata_json={"player_card_id": sale.player_card_id, "count": int(churn_count)},
            )

        recent_sales = list(
            self.session.scalars(
                select(PlayerCardSale)
                .where(PlayerCardSale.player_card_id == sale.player_card_id)
                .order_by(PlayerCardSale.created_at.desc())
                .limit(3)
            ).all()
        )
        if len(recent_sales) == 3:
            unique_users = {row.seller_user_id for row in recent_sales} | {row.buyer_user_id for row in recent_sales}
            if len(unique_users) == 2:
                directions = [(row.seller_user_id, row.buyer_user_id) for row in recent_sales]
                if directions[0] == directions[2] and directions[0] != directions[1]:
                    subject = f"loop:{sale.player_card_id}:{now:%Y%m%d%H}"
                    integrity_service.register_incident_once(
                        user_id=sale.seller_user_id,
                        incident_type="circular_card_trading",
                        subject=subject,
                        severity="high",
                        title="Circular trading detected",
                        description="Card trades are cycling between the same two accounts.",
                        score_delta=Decimal("-15.00"),
                        metadata_json={"player_card_id": sale.player_card_id, "sequence": directions},
                    )

        recent_prices = list(
            self.session.scalars(
                select(PlayerCardSale.price_per_card_credits)
                .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
                .where(PlayerCard.player_id == card.player_id)
                .order_by(PlayerCardSale.created_at.desc())
                .limit(10)
            ).all()
        )
        if len(recent_prices) >= 3:
            average_price = sum(self._normalize_amount(price) for price in recent_prices) / Decimal(len(recent_prices))
            if average_price > Decimal("0"):
                current_price = self._normalize_amount(sale.price_per_card_credits)
                if current_price > average_price * Decimal("2.5"):
                    risk_service.create_system_event(
                        actor_user_id=None,
                        event_key=f"player-card-price-spike:{card.player_id}:{now:%Y%m%d%H}",
                        event_type="player_card_price_spike",
                        severity=SystemEventSeverity.WARNING,
                        title="Player card price spike",
                        body="Player card trade price exceeded 2.5x recent average.",
                        subject_type="player",
                        subject_id=card.player_id,
                        metadata_json={"price": float(current_price), "average": float(average_price)},
                    )

        volume_1h = (
            self.session.scalar(
                select(func.count(PlayerCardSale.id))
                .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
                .where(PlayerCard.player_id == card.player_id, PlayerCardSale.created_at >= now - timedelta(hours=1))
            )
            or 0
        )
        if volume_1h >= 12:
            risk_service.create_system_event(
                actor_user_id=None,
                event_key=f"player-card-volume-cluster:{card.player_id}:{now:%Y%m%d%H}",
                event_type="player_card_volume_cluster",
                severity=SystemEventSeverity.WARNING,
                title="Suspicious player card volume cluster",
                body="High-volume card trading cluster detected in the last hour.",
                subject_type="player",
                subject_id=card.player_id,
                metadata_json={"volume_1h": int(volume_1h)},
            )

    def _append_card_history(
        self,
        player_card_id: str,
        event_type: str,
        actor_user_id: str | None,
        *,
        delta_supply: int = 0,
        delta_available: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            PlayerCardHistory(
                player_card_id=player_card_id,
                event_type=event_type,
                description=None,
                delta_supply=delta_supply,
                delta_available=delta_available,
                actor_user_id=actor_user_id,
                metadata_json=metadata or {},
            )
        )

    def _append_owner_history(
        self,
        player_card_id: str,
        *,
        from_user_id: str | None,
        to_user_id: str | None,
        quantity: int,
        event_type: str,
        reference_id: str | None,
    ) -> None:
        self.session.add(
            PlayerCardOwnerHistory(
                player_card_id=player_card_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                quantity=quantity,
                event_type=event_type,
                reference_id=reference_id,
                metadata_json={},
            )
        )

    def _get_card(self, player_card_id: str) -> PlayerCard:
        card = self.session.get(PlayerCard, player_card_id)
        if card is None:
            raise PlayerCardNotFoundError("Player card was not found.")
        return card

    def _get_listing(self, listing_id: str) -> PlayerCardListing:
        listing = self.session.scalar(select(PlayerCardListing).where(PlayerCardListing.listing_id == listing_id))
        if listing is None:
            raise PlayerCardNotFoundError("Listing was not found.")
        return listing

    def _get_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id, PlayerCardHolding.player_card_id == player_card_id
            )
        )
        if holding is None:
            raise PlayerCardValidationError("Player card holding was not found for this user.")
        return holding

    def _get_or_create_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id, PlayerCardHolding.player_card_id == player_card_id
            )
        )
        if holding is None:
            holding = PlayerCardHolding(
                owner_user_id=user_id,
                player_card_id=player_card_id,
                quantity_total=0,
                quantity_reserved=0,
                metadata_json={},
            )
            self.session.add(holding)
            self.session.flush()
        return holding

    def _get_tier(self, tier_id: str) -> PlayerCardTier:
        tier = self.session.get(PlayerCardTier, tier_id)
        if tier is None:
            raise PlayerCardNotFoundError("Player card tier was not found.")
        return tier

    def _ensure_player_from_national_seed(self, seed: NationalRegenSeed, *, actor: User | None = None) -> Player:
        provider = "gtex_national_seed"
        player = self.session.scalar(
            select(Player).where(Player.source_provider == provider, Player.provider_external_id == seed.id)
        )
        if player is None:
            player = Player(
                source_provider=provider,
                provider_external_id=seed.id,
                full_name=seed.display_name,
                is_tradable=True,
                is_real_player=False,
            )
            self.session.add(player)

        first_name, last_name = self._split_display_name(seed.display_name)
        country = self._country_for_national_seed(seed)
        now = datetime.now(UTC)
        player.full_name = seed.display_name
        player.first_name = first_name
        player.last_name = last_name
        player.short_name = seed.display_name
        resolved_position = normalize_position(seed.primary_position)
        player.position = resolved_position.value if resolved_position is not None else seed.primary_position
        player.normalized_position = resolved_position.name if resolved_position is not None else None
        player.date_of_birth = self._birth_date_from_age(seed.age)
        player.country_id = country.id if country is not None else player.country_id
        player.market_value_eur = self._market_value_from_seed(seed)
        player.current_market_reference_value = player.market_value_eur
        player.market_reference_currency = "EUR"
        player.profile_completeness_score = max(float(player.profile_completeness_score or 0), 0.95)
        player.is_tradable = True
        player.is_real_player = False
        player.canonical_display_name = seed.display_name
        player.identity_confidence_score = 0.98
        player.source_last_refreshed_at = now
        self.session.flush()

        try:
            portrait_metadata = RegenPortraitService(self.session).ensure_national_seed_portrait(seed)
        except RegenPortraitError:
            portrait_metadata = dict(seed.metadata_json or {})

        enabled_at = now.isoformat()
        seed_metadata = dict(seed.metadata_json or {})
        seed_metadata.update(
            {
                "national_pool_only": False,
                "admin_trade_enabled": True,
                "admin_mint_enabled": True,
                "trade_enabled_by_admin": True,
                "card_mint_eligible": True,
                "transfer_market_eligible": True,
                "share_market_eligible": True,
                "market_eligible": True,
                "buy_cta_allowed": True,
                "buyable": True,
                "tradable": True,
                "minted_player_id": player.id,
                "enabled_for_trade_by_user_id": actor.id if actor is not None else None,
                "enabled_for_trade_at": enabled_at,
            }
        )
        seed.metadata_json = seed_metadata

        player.dna_profile = {
            **dict(player.dna_profile or {}),
            "source_type": "national_seed",
            "source_bucket": "preseeded",
            "is_regen": True,
            "is_preseeded_national_regen": True,
            "national_pool_only": False,
            "admin_trade_enabled": True,
            "admin_mint_enabled": True,
            "trade_enabled_by_admin": True,
            "card_mint_eligible": True,
            "transfer_market_eligible": True,
            "share_market_eligible": True,
            "market_eligible": True,
            "buy_cta_allowed": True,
            "buyable": True,
            "tradable": True,
            "national_seed_id": seed.id,
            "national_seed_key": seed.seed_key,
            "country_code": seed.country_code,
            "country_name": seed.country_name,
            "current_rating": int(seed.current_rating),
            "potential_rating": int(seed.potential_rating),
            "growth_curve": float(seed.growth_curve),
            "rarity_tier": seed.rarity_tier,
            "portraitUrl": portrait_metadata.get("portraitUrl"),
            "image_url": portrait_metadata.get("portraitUrl"),
            "faceSeed": portrait_metadata.get("faceSeed"),
            "enabled_for_trade_at": enabled_at,
        }
        self.session.flush()
        try:
            RegenPortraitService(self.session).ensure_player_portrait(player)
        except RegenPortraitError:
            pass
        return player

    def _country_for_national_seed(self, seed: NationalRegenSeed) -> Country | None:
        code = (seed.country_code or "").strip().upper()
        country_name = (seed.country_name or "").strip()
        if not code and not country_name:
            return None
        filters = []
        if code:
            filters.extend(
                [
                    Country.alpha2_code == code,
                    Country.alpha3_code == code,
                    Country.fifa_code == code,
                    Country.provider_external_id == code,
                ]
            )
        if country_name:
            filters.append(Country.name == country_name)
        return self.session.scalar(select(Country).where(or_(*filters)).limit(1)) if filters else None

    @staticmethod
    def _split_display_name(display_name: str) -> tuple[str, str | None]:
        parts = display_name.strip().split(" ", 1)
        return parts[0], parts[1] if len(parts) > 1 else None

    @staticmethod
    def _birth_date_from_age(age: int | None) -> date | None:
        if age is None or age <= 0:
            return None
        today = date.today()
        return date(max(today.year - int(age), 1900), 1, 1)

    @staticmethod
    def _normalize_position(position: str | None) -> str | None:
        resolved = normalize_position(position)
        if resolved is not None:
            return resolved.name
        value = (position or "").strip()
        return value or None

    def _position_code(self, player: Player) -> str | None:
        return self._normalize_position(player.normalized_position or player.position)

    @staticmethod
    def _market_value_from_seed(seed: NationalRegenSeed) -> float:
        rarity_multiplier = {
            "common": 1.0,
            "rare": 1.35,
            "elite": 2.1,
            "legendary": 3.25,
        }.get(str(seed.rarity_tier or "common").lower(), 1.0)
        rating_value = (int(seed.current_rating) * 1_800) + (int(seed.potential_rating) * 2_400)
        growth_multiplier = 1.0 + (max(0.0, min(float(seed.growth_curve or 0.0), 1.0)) * 0.25)
        return float(max(75_000, round(rating_value * rarity_multiplier * growth_multiplier, 2)))

    def _get_player(self, player_id: str, *, actor: User | None = None) -> Player:
        player = self.session.get(Player, player_id)
        if player is not None:
            if not is_card_mint_eligible(player):
                raise PlayerCardValidationError("Player is not eligible for card minting.")
            return player
        seed = self.session.get(NationalRegenSeed, player_id)
        if seed is not None and is_preseeded_national_regen(seed):
            if is_card_mint_eligible(seed):
                return self._ensure_player_from_national_seed(seed, actor=actor)
            raise PlayerCardValidationError(
                "Preseeded national regens are national-pool-only and cannot be card minted."
            )
        raise PlayerCardNotFoundError("Player was not found.")

    def _settlement_exists(self, reference: str) -> bool:
        existing = self.session.scalar(select(PlayerCardSale).where(PlayerCardSale.settlement_reference == reference))
        return existing is not None

    def _publish_event(self, name: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is None:
            return
        self.event_publisher.publish(DomainEvent(name=name, payload=payload))

    def _tier_payload(self, tier: PlayerCardTier) -> dict[str, object]:
        return {
            "tier_id": tier.id,
            "code": tier.code,
            "name": tier.name,
            "rarity_rank": tier.rarity_rank,
            "max_supply": tier.max_supply,
            "supply_multiplier": float(tier.supply_multiplier),
            "base_mint_price_credits": float(tier.base_mint_price_credits),
            "color_hex": tier.color_hex,
            "is_active": tier.is_active,
        }

    def _effect_payload(self, effect: PlayerCardEffect) -> dict[str, object]:
        return {
            "effect_id": effect.id,
            "player_card_id": effect.player_card_id,
            "effect_type": effect.effect_type,
            "effect_value": float(effect.effect_value),
            "applied_at": effect.applied_at,
            "expires_at": effect.expires_at,
            "source": effect.source,
            "metadata_json": effect.metadata_json,
        }

    def _buff_payload(self, buff: PlayerCardFormBuff) -> dict[str, object]:
        return {
            "buff_id": buff.id,
            "player_card_id": buff.player_card_id,
            "buff_type": buff.buff_type,
            "buff_value": float(buff.buff_value),
            "started_at": buff.started_at,
            "expires_at": buff.expires_at,
            "source": buff.source,
            "metadata_json": buff.metadata_json,
        }

    def _trending_flag_payload(self, flag) -> dict[str, object]:
        return {
            "id": flag.id,
            "player_id": flag.player_id,
            "event_id": flag.event_id,
            "flag_type": flag.flag_type,
            "flag_label": flag.flag_label,
            "trend_score": float(flag.trend_score),
            "priority": flag.priority,
            "status": flag.status,
            "started_at": flag.started_at,
            "expires_at": flag.expires_at,
            "source": flag.source,
            "metadata_json": flag.metadata_json,
        }

    def _player_form_modifier_payload(self, modifier) -> dict[str, object]:
        return {
            "id": modifier.id,
            "player_id": modifier.player_id,
            "event_id": modifier.event_id,
            "modifier_type": modifier.modifier_type,
            "modifier_label": modifier.modifier_label,
            "modifier_score": float(modifier.modifier_score),
            "gameplay_effect_value": float(modifier.gameplay_effect_value),
            "market_effect_value": float(modifier.market_effect_value),
            "recommendation_effect_value": float(modifier.recommendation_effect_value),
            "visible_to_users": modifier.visible_to_users,
            "status": modifier.status,
            "started_at": modifier.started_at,
            "expires_at": modifier.expires_at,
            "source": modifier.source,
            "metadata_json": modifier.metadata_json,
        }

    def _demand_signal_payload(self, signal) -> dict[str, object]:
        return {
            "id": signal.id,
            "player_id": signal.player_id,
            "event_id": signal.event_id,
            "signal_type": signal.signal_type,
            "signal_label": signal.signal_label,
            "demand_score": float(signal.demand_score),
            "scouting_interest_delta": float(signal.scouting_interest_delta),
            "recommendation_priority_delta": float(signal.recommendation_priority_delta),
            "market_buzz_score": float(signal.market_buzz_score),
            "status": signal.status,
            "started_at": signal.started_at,
            "expires_at": signal.expires_at,
            "source": signal.source,
            "metadata_json": signal.metadata_json,
        }

    def _momentum_payload(self, momentum: PlayerCardMomentum) -> dict[str, object]:
        return {
            "momentum_id": momentum.id,
            "player_id": momentum.player_id,
            "last_trade_price_credits": (
                float(momentum.last_trade_price_credits) if momentum.last_trade_price_credits is not None else None
            ),
            "momentum_7d_pct": float(momentum.momentum_7d_pct),
            "momentum_30d_pct": float(momentum.momentum_30d_pct),
            "trend_direction": momentum.trend_direction,
            "metadata_json": momentum.metadata_json,
        }

    def _stats_payload(self, snapshot: PlayerStatsSnapshot) -> dict[str, object]:
        return {
            "snapshot_id": snapshot.id,
            "player_id": snapshot.player_id,
            "as_of": snapshot.as_of,
            "competition_id": snapshot.competition_id,
            "season_id": snapshot.season_id,
            "source_type": snapshot.source_type,
            "stats_json": snapshot.stats_json,
        }

    def _market_snapshot_payload(self, snapshot: PlayerMarketValueSnapshot) -> dict[str, object]:
        return {
            "snapshot_id": snapshot.id,
            "player_id": snapshot.player_id,
            "as_of": snapshot.as_of,
            "last_trade_price_credits": (
                float(snapshot.last_trade_price_credits) if snapshot.last_trade_price_credits is not None else None
            ),
            "avg_trade_price_credits": (
                float(snapshot.avg_trade_price_credits) if snapshot.avg_trade_price_credits is not None else None
            ),
            "volume_24h": snapshot.volume_24h,
            "listing_floor_price_credits": (
                float(snapshot.listing_floor_price_credits)
                if snapshot.listing_floor_price_credits is not None
                else None
            ),
            "listing_count": snapshot.listing_count,
            "high_24h_price_credits": (
                float(snapshot.high_24h_price_credits) if snapshot.high_24h_price_credits is not None else None
            ),
            "low_24h_price_credits": (
                float(snapshot.low_24h_price_credits) if snapshot.low_24h_price_credits is not None else None
            ),
            "metadata_json": snapshot.metadata_json,
        }

    def _listing_payload(
        self, listing: PlayerCardListing, card: PlayerCard, tier: PlayerCardTier, player: Player
    ) -> dict[str, object]:
        summary = self._player_summary(player.id)
        global_scouting_index = self._global_scouting_index(player, summary=summary)
        return {
            "listing_id": listing.listing_id,
            "player_card_id": listing.player_card_id,
            "player_id": player.id,
            "player_name": player.full_name,
            "global_scouting_index": global_scouting_index,
            "gsi_band": gsi_band(global_scouting_index),
            "avatar": self._avatar_payload(player, summary=summary),
            "image_url": self._image_url(player, summary=summary),
            "latest_value_credits": self._latest_value_credits(
                player.id,
                summary=summary,
            ),
            "tier_code": tier.code,
            "tier_name": tier.name,
            "edition_code": card.edition_code,
            "seller_user_id": listing.seller_user_id,
            "quantity": listing.quantity,
            "price_per_card_credits": float(listing.price_per_card_credits),
            "status": listing.status,
            "created_at": listing.created_at,
        }

    def _global_scouting_index(
        self,
        player: Player,
        *,
        summary: PlayerSummaryReadModel | None = None,
        summary_payload: Any | None = None,
    ) -> int:
        payload: dict[str, Any] = {}
        if isinstance(summary_payload, dict):
            payload.update(summary_payload)
        elif isinstance(summary, PlayerSummaryReadModel) and isinstance(summary.summary_json, dict):
            payload.update(summary.summary_json)
        if isinstance(player.dna_profile, dict):
            payload.update(player.dna_profile)
        payload.setdefault("id", player.id)
        payload.setdefault("player_id", player.id)
        payload.setdefault("name", player.full_name)
        payload.setdefault("position", player.position)
        payload.setdefault("normalized_position", player.normalized_position)
        payload.setdefault("market_value_eur", player.market_value_eur)
        return calculate_gsi(payload, position=self._position_code(player))

    def _player_summary(self, player_id: str) -> PlayerSummaryReadModel | None:
        return self.session.get(PlayerSummaryReadModel, player_id)

    def _latest_value_credits(
        self,
        player_id: str,
        *,
        summary: PlayerSummaryReadModel | None = None,
    ) -> float | None:
        resolved_summary = summary if summary is not None else self._player_summary(player_id)
        if resolved_summary is None:
            return None
        return float(resolved_summary.current_value_credits)

    def _avatar_payload(
        self,
        player: Player,
        *,
        summary: PlayerSummaryReadModel | None = None,
    ) -> dict[str, object]:
        resolved_summary = summary if summary is not None else self._player_summary(player.id)
        summary_payload = (
            resolved_summary.summary_json
            if resolved_summary is not None and isinstance(resolved_summary.summary_json, dict)
            else None
        )
        return self.avatar_service.build_from_player(
            player,
            summary_payload=summary_payload,
        ).model_dump()

    @staticmethod
    def _image_url_from_payload(payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None
        for key in ("image_url", "portrait_url", "photo_url"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        image_payload = payload.get("image")
        if isinstance(image_payload, dict):
            for key in ("source_url", "url", "storage_key"):
                value = image_payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _image_url(
        self,
        player: Player,
        *,
        summary: PlayerSummaryReadModel | None = None,
    ) -> str | None:
        resolved_summary = summary if summary is not None else self._player_summary(player.id)
        summary_payload = (
            resolved_summary.summary_json
            if resolved_summary is not None and isinstance(resolved_summary.summary_json, dict)
            else None
        )
        direct = self._image_url_from_payload(summary_payload)
        if direct:
            return direct
        candidates = sorted(
            player.image_metadata,
            key=lambda image: (
                not image.is_primary,
                image.moderation_status != "approved",
                image.created_at,
                image.id,
            ),
        )
        for image in candidates:
            if image.moderation_status == "rejected":
                continue
            if image.source_url:
                return image.source_url
            if image.storage_key:
                return image.storage_key
        if not bool(player.is_real_player):
            try:
                return RegenPortraitService(self.session).ensure_player_portrait(player).portrait_url
            except RegenPortraitError:
                return None
        return None

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{generate_uuid().split('-')[0]}"

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
