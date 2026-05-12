from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.models.player_cards import (
    PlayerCard,
    PlayerCardBurnEvent,
    PlayerCardHistory,
    PlayerCardHolding,
    PlayerCardOwnerHistory,
    PlayerCardPack,
    PlayerCardPackOpening,
    PlayerCardTier,
    PlayerCardUpgradeEvent,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.player_cards.service import PlayerCardNotFoundError, PlayerCardValidationError
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


@dataclass(slots=True)
class PlayerCardCollectiblesService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def list_packs(self) -> list[dict[str, Any]]:
        self.ensure_default_packs()
        packs = list(
            self.session.scalars(
                select(PlayerCardPack)
                .where(PlayerCardPack.is_active.is_(True))
                .order_by(PlayerCardPack.price_credits.asc(), PlayerCardPack.title.asc())
            ).all()
        )
        return [self._pack_payload(pack) for pack in packs]

    def open_pack(self, *, actor: User, pack_key: str, metadata_json: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_default_packs()
        pack = self.session.scalar(select(PlayerCardPack).where(PlayerCardPack.pack_key == pack_key))
        if pack is None or not pack.is_active:
            raise PlayerCardNotFoundError("Player card pack was not found.")

        price = self._normalize_amount(pack.price_credits)
        if price > Decimal("0.0000"):
            self._charge_pack_price(actor=actor, amount=price, pack_key=pack.pack_key)

        cards = self._select_cards_for_pack(pack)
        if len(cards) < pack.cards_per_pack:
            raise PlayerCardValidationError("Not enough active card supply is available for this pack.")

        opened_cards: list[dict[str, Any]] = []
        for card, tier in cards[: pack.cards_per_pack]:
            card.supply_available = max(card.supply_available - 1, 0)
            holding = self._get_or_create_holding(actor.id, card.id)
            holding.quantity_total += 1
            holding.last_acquired_at = datetime.now(UTC)
            opened_cards.append(self._opened_card_payload(card, tier))
            self._append_card_history(
                card.id,
                "pack.opened",
                actor.id,
                delta_available=-1,
                metadata={"pack_key": pack.pack_key},
            )
            self._append_owner_history(
                card.id,
                from_user_id=None,
                to_user_id=actor.id,
                quantity=1,
                event_type="pack_opened",
                reference_id=None,
            )

        opening = PlayerCardPackOpening(
            pack_id=pack.id,
            user_id=actor.id,
            status="opened",
            price_credits=price,
            opened_cards_json=opened_cards,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(opening)
        self.session.flush()
        self._publish(
            "player_card.pack.opened", {"opening_id": opening.id, "pack_key": pack.pack_key, "user_id": actor.id}
        )
        return self._opening_payload(opening, pack)

    def burn_card(
        self,
        *,
        actor: User,
        player_card_id: str,
        quantity: int,
        reason: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if quantity <= 0:
            raise PlayerCardValidationError("Burn quantity must be positive.")
        card = self._get_card(player_card_id)
        holding = self._get_holding(actor.id, card.id)
        available = holding.quantity_total - holding.quantity_reserved
        if available < quantity:
            raise PlayerCardValidationError("Not enough available card copies to burn.")

        holding.quantity_total -= quantity
        remaining_quantity = max(holding.quantity_total, 0)
        if holding.quantity_total <= 0:
            self.session.delete(holding)
        burn = PlayerCardBurnEvent(
            user_id=actor.id,
            player_card_id=card.id,
            quantity=quantity,
            reason=reason,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(burn)
        self._append_card_history(
            card.id,
            "card.burned",
            actor.id,
            delta_supply=-quantity,
            metadata={"reason": reason},
        )
        self._append_owner_history(
            card.id,
            from_user_id=actor.id,
            to_user_id=None,
            quantity=quantity,
            event_type="burned",
            reference_id=None,
        )
        self.session.flush()
        return {
            "burn_event_id": burn.id,
            "player_card_id": card.id,
            "user_id": actor.id,
            "quantity": quantity,
            "reason": reason,
            "remaining_quantity": remaining_quantity,
            "created_at": burn.created_at,
        }

    def upgrade_cards(
        self,
        *,
        actor: User,
        source_player_card_ids: list[str],
        target_tier_code: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        unique_source_ids = list(dict.fromkeys(item.strip() for item in source_player_card_ids if item.strip()))
        if len(unique_source_ids) < 2:
            raise PlayerCardValidationError("At least two source cards are required for an upgrade.")

        sources = [self._get_card(card_id) for card_id in unique_source_ids]
        player_ids = {card.player_id for card in sources}
        if len(player_ids) != 1:
            raise PlayerCardValidationError("Only cards for the same player can be fused.")

        for card in sources:
            holding = self._get_holding(actor.id, card.id)
            if holding.quantity_total - holding.quantity_reserved < 1:
                raise PlayerCardValidationError("One or more source cards is not available for upgrade.")

        target_tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == target_tier_code))
        if target_tier is None or not target_tier.is_active:
            raise PlayerCardValidationError("Target card tier was not found.")

        target_card = self._get_or_create_target_card(
            source_card=sources[0],
            target_tier=target_tier,
            metadata_json=metadata_json or {},
        )
        for card in sources:
            holding = self._get_holding(actor.id, card.id)
            holding.quantity_total -= 1
            if holding.quantity_total <= 0:
                self.session.delete(holding)
            self._append_card_history(
                card.id,
                "card.upgrade.source_burned",
                actor.id,
                delta_supply=-1,
                metadata={"target_player_card_id": target_card.id},
            )
            self._append_owner_history(
                card.id,
                from_user_id=actor.id,
                to_user_id=None,
                quantity=1,
                event_type="upgrade_burned",
                reference_id=None,
            )

        target_card.supply_total += 1
        target_holding = self._get_or_create_holding(actor.id, target_card.id)
        target_holding.quantity_total += 1
        target_holding.last_acquired_at = datetime.now(UTC)
        event = PlayerCardUpgradeEvent(
            user_id=actor.id,
            source_player_card_ids_json=unique_source_ids,
            target_player_card_id=target_card.id,
            status="completed",
            burn_quantity=len(unique_source_ids),
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(event)
        self._append_card_history(
            target_card.id,
            "card.upgrade.created",
            actor.id,
            delta_supply=1,
            metadata={"source_player_card_ids": unique_source_ids},
        )
        self._append_owner_history(
            target_card.id,
            from_user_id=None,
            to_user_id=actor.id,
            quantity=1,
            event_type="upgrade_created",
            reference_id=None,
        )
        self.session.flush()
        return {
            "upgrade_event_id": event.id,
            "source_player_card_ids": unique_source_ids,
            "target_player_card_id": target_card.id,
            "user_id": actor.id,
            "burn_quantity": len(unique_source_ids),
            "status": event.status,
            "created_at": event.created_at,
        }

    def ensure_default_packs(self) -> None:
        existing = self.session.scalar(select(PlayerCardPack).where(PlayerCardPack.pack_key == "starter-draft"))
        if existing is not None:
            return
        odds = {
            str(tier.code): max(1, 100 - (int(tier.rarity_rank or 1) * 10))
            for tier in self.session.scalars(select(PlayerCardTier).where(PlayerCardTier.is_active.is_(True))).all()
        }
        if not odds:
            odds = {"bronze": 70, "silver": 20, "gold": 8, "elite": 2}
        self.session.add(
            PlayerCardPack(
                pack_key="starter-draft",
                title="Starter Draft Pack",
                description="A live-supply collectible card pack backed by existing GTEX card inventory.",
                price_credits=Decimal("0.0000"),
                cards_per_pack=3,
                drop_odds_json=odds,
                is_active=True,
                metadata_json={"source": "batch_32_default"},
            )
        )
        self.session.flush()

    def _select_cards_for_pack(self, pack: PlayerCardPack) -> list[tuple[PlayerCard, PlayerCardTier]]:
        stmt = (
            select(PlayerCard, PlayerCardTier)
            .join(PlayerCardTier, PlayerCard.tier_id == PlayerCardTier.id)
            .where(
                PlayerCard.is_active.is_(True),
                PlayerCard.supply_available > 0,
                PlayerCardTier.is_active.is_(True),
            )
            .order_by(PlayerCardTier.rarity_rank.asc(), PlayerCard.updated_at.desc(), PlayerCard.display_name.asc())
        )
        return list(self.session.execute(stmt).all())

    def _get_or_create_target_card(
        self,
        *,
        source_card: PlayerCard,
        target_tier: PlayerCardTier,
        metadata_json: dict[str, Any],
    ) -> PlayerCard:
        existing = self.session.scalar(
            select(PlayerCard).where(
                PlayerCard.player_id == source_card.player_id,
                PlayerCard.tier_id == target_tier.id,
                PlayerCard.edition_code == "fused",
            )
        )
        if existing is not None:
            return existing
        target = PlayerCard(
            player_id=source_card.player_id,
            tier_id=target_tier.id,
            edition_code="fused",
            display_name=f"{source_card.display_name} {target_tier.name} Fusion",
            season_label=source_card.season_label,
            card_variant="fused",
            supply_total=0,
            supply_available=0,
            is_active=True,
            metadata_json={"source": "card_upgrade", **metadata_json},
        )
        self.session.add(target)
        self.session.flush()
        return target

    def _charge_pack_price(self, *, actor: User, amount: Decimal, pack_key: str) -> None:
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=-amount,
                        source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
                        transaction_type=LedgerTransactionType.TRADE_BUY,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=amount,
                        source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
                        transaction_type=LedgerTransactionType.TRADE_SELL,
                    ),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
                transaction_type=LedgerTransactionType.TRADE_BUY,
                reference=f"player-card-pack:{pack_key}:{actor.id}:{datetime.now(UTC).timestamp()}",
                description="Player card pack purchase",
                actor=actor,
                metadata={"pack_key": pack_key},
            )
        except InsufficientBalanceError as exc:
            raise PlayerCardValidationError("Insufficient balance to open this card pack.") from exc

    def _get_card(self, player_card_id: str) -> PlayerCard:
        card = self.session.get(PlayerCard, player_card_id)
        if card is None:
            raise PlayerCardNotFoundError("Player card was not found.")
        return card

    def _get_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.player_card_id == player_card_id,
            )
        )
        if holding is None:
            raise PlayerCardValidationError("Player card holding was not found for this user.")
        return holding

    def _get_or_create_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.player_card_id == player_card_id,
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

    def _pack_payload(self, pack: PlayerCardPack) -> dict[str, Any]:
        return {
            "pack_key": pack.pack_key,
            "title": pack.title,
            "description": pack.description,
            "price_credits": self._normalize_amount(pack.price_credits),
            "cards_per_pack": pack.cards_per_pack,
            "drop_odds_json": dict(pack.drop_odds_json or {}),
            "is_active": pack.is_active,
            "metadata_json": dict(pack.metadata_json or {}),
        }

    def _opening_payload(self, opening: PlayerCardPackOpening, pack: PlayerCardPack) -> dict[str, Any]:
        return {
            "opening_id": opening.id,
            "pack_key": pack.pack_key,
            "user_id": opening.user_id,
            "status": opening.status,
            "price_credits": self._normalize_amount(opening.price_credits),
            "opened_cards": list(opening.opened_cards_json or []),
            "created_at": opening.created_at,
        }

    def _opened_card_payload(self, card: PlayerCard, tier: PlayerCardTier) -> dict[str, Any]:
        return {
            "player_card_id": card.id,
            "player_id": card.player_id,
            "display_name": card.display_name,
            "tier_code": tier.code,
            "tier_name": tier.name,
            "rarity_rank": tier.rarity_rank,
            "edition_code": card.edition_code,
            "card_variant": card.card_variant,
        }

    def _publish(self, name: str, payload: dict[str, Any]) -> None:
        self.event_publisher.publish(DomainEvent(name=name, payload=payload))

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
