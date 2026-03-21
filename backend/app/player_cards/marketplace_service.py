from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import Boolean, Integer, Numeric, String, and_, case, cast, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.core.config import PlayerCardMarketIntegrityConfig, Settings, get_settings
from app.core.events import EventPublisher, InMemoryEventPublisher
from app.ingestion.models import Player
from app.integrity_engine.service import IntegrityEngineService
from app.models.base import generate_uuid
from app.models.card_access import (
    CardLoanContract,
    CardLoanListing,
    CardLoanNegotiation,
    CardMarketplaceAuditEvent,
    CardSwapExecution,
    CardSwapListing,
)
from app.models.creator_card import CreatorCard
from app.models.player_cards import (
    PlayerAlias,
    PlayerCard,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardListing,
    PlayerMarketValueSnapshot,
    PlayerCardOwnerHistory,
    PlayerCardSale,
    PlayerCardTier,
    PlayerMoniker,
)
from app.models.regen import RegenProfile
from app.models.risk_ops import SystemEventSeverity
from app.models.user import User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.player_cards.service import PlayerCardNotFoundError, PlayerCardPermissionError, PlayerCardValidationError
from app.players.read_models import PlayerSummaryReadModel
from app.risk_ops_engine.service import RiskOpsService
from app.services.avatar_service import AvatarIdentityInput, AvatarService
from app.value_engine.scoring import credits_from_real_world_value
from app.wallets.service import LedgerPosting, WalletService


AMOUNT_QUANTUM = Decimal("0.0001")
FREE_LOAN_FLOOR_RATIO = Decimal("0.05")
NORMAL_LOAN_PLATFORM_FEE_BPS = 2_000
REGEN_LOAN_PLATFORM_FEE_BPS = 4_000
MAX_LOAN_DURATION_DAYS = 30
DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 100


@dataclass(slots=True)
class PlayerCardMarketplaceService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    settings: Settings = field(default_factory=get_settings)
    avatar_service: AvatarService = field(default_factory=AvatarService)

    @staticmethod
    def _normalize_amount(value: Decimal | float | int | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _new_public_id(prefix: str) -> str:
        return f"{prefix}_{generate_uuid().replace('-', '')[:24]}"

    @staticmethod
    def _is_expired(value: datetime | None) -> bool:
        if value is None:
            return False
        return PlayerCardMarketplaceService._coerce_utc(value) <= datetime.now(UTC)

    @staticmethod
    def _coerce_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _available_holding_quantity(holding: PlayerCardHolding) -> int:
        return max(holding.quantity_total - holding.quantity_reserved, 0)

    def _ensure_market_actor(self, actor: User) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Admin accounts cannot use the player card marketplace.")

    def _get_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise PlayerCardValidationError("User was not found.")
        return user

    def _get_card(self, player_card_id: str) -> PlayerCard:
        card = self.session.get(PlayerCard, player_card_id)
        if card is None:
            raise PlayerCardNotFoundError("Player card was not found.")
        if not card.is_active:
            raise PlayerCardValidationError("Player card is not active.")
        return card

    def _get_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.player_card_id == player_card_id,
            )
        )
        if holding is None or holding.quantity_total <= 0:
            raise PlayerCardValidationError("The requested player card is not held by this user.")
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
                player_card_id=player_card_id,
                owner_user_id=user_id,
                quantity_total=0,
                quantity_reserved=0,
                metadata_json={},
            )
            self.session.add(holding)
            self.session.flush()
        return holding

    def _get_sale_listing(self, listing_id: str) -> PlayerCardListing:
        listing = self.session.scalar(select(PlayerCardListing).where(PlayerCardListing.listing_id == listing_id))
        if listing is None:
            raise PlayerCardNotFoundError("Sale listing was not found.")
        return listing

    def _get_loan_listing(self, listing_id: str) -> CardLoanListing:
        listing = self.session.get(CardLoanListing, listing_id)
        if listing is None:
            raise PlayerCardNotFoundError("Loan listing was not found.")
        return listing

    def _get_loan_negotiation(self, negotiation_id: str) -> CardLoanNegotiation:
        negotiation = self.session.get(CardLoanNegotiation, negotiation_id)
        if negotiation is None:
            raise PlayerCardNotFoundError("Loan negotiation was not found.")
        return negotiation

    def _get_loan_contract(self, contract_id: str) -> CardLoanContract:
        contract = self.session.get(CardLoanContract, contract_id)
        if contract is None:
            raise PlayerCardNotFoundError("Loan contract was not found.")
        return contract

    def _get_swap_listing(self, listing_id: str) -> CardSwapListing:
        listing = self.session.get(CardSwapListing, listing_id)
        if listing is None:
            raise PlayerCardNotFoundError("Swap listing was not found.")
        return listing

    def _append_card_history(
        self,
        player_card_id: str,
        event_type: str,
        actor_user_id: str | None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            PlayerCardHistory(
                player_card_id=player_card_id,
                event_type=event_type,
                description=None,
                delta_supply=0,
                delta_available=0,
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

    def _audit(
        self,
        *,
        listing_type: str,
        action: str,
        actor_user_id: str | None,
        player_card_id: str | None,
        listing_id: str | None = None,
        loan_contract_id: str | None = None,
        negotiation_id: str | None = None,
        swap_execution_id: str | None = None,
        status_from: str | None = None,
        status_to: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            CardMarketplaceAuditEvent(
                listing_type=listing_type,
                action=action,
                actor_user_id=actor_user_id,
                player_card_id=player_card_id,
                listing_id=listing_id,
                loan_contract_id=loan_contract_id,
                negotiation_id=negotiation_id,
                swap_execution_id=swap_execution_id,
                status_from=status_from,
                status_to=status_to,
                payload_json=payload or {},
            )
        )

    def _get_card_context(self, player_card_id: str) -> dict[str, Any]:
        row = self.session.execute(
            select(
                PlayerCard,
                PlayerCardTier,
                Player,
                PlayerSummaryReadModel.current_club_name,
                PlayerSummaryReadModel.average_rating,
                PlayerSummaryReadModel.summary_json,
            )
            .join(PlayerCardTier, PlayerCardTier.id == PlayerCard.tier_id)
            .join(Player, Player.id == PlayerCard.player_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(PlayerCard.id == player_card_id)
        ).one_or_none()
        if row is None:
            raise PlayerCardNotFoundError("Player card was not found.")
        card, tier, player, current_club_name, average_rating, summary_payload = row
        is_regen = card.card_variant.lower().startswith("regen") or self.session.scalar(
            select(RegenProfile.id).where(RegenProfile.linked_unique_card_id == card.id).limit(1)
        ) is not None
        is_creator_linked = self.session.scalar(
            select(CreatorCard.id).where(CreatorCard.player_id == player.id, CreatorCard.status == "active").limit(1)
        ) is not None
        asset_origin = "regen_newgen" if is_regen else "creator_linked" if is_creator_linked else "standard"
        return {
            "card": card,
            "tier": tier,
            "player": player,
            "club_name": current_club_name,
            "average_rating": average_rating,
            "is_regen_newgen": is_regen,
            "is_creator_linked": is_creator_linked,
            "asset_origin": asset_origin,
            "avatar": self.avatar_service.build_from_player(
                player,
                summary_payload=summary_payload if isinstance(summary_payload, dict) else None,
            ).model_dump(),
        }

    def _base_value_credits(self, context: dict[str, Any]) -> Decimal:
        summary = self.session.get(PlayerSummaryReadModel, context["player"].id)
        if summary is not None and summary.current_value_credits > 0:
            return self._normalize_amount(summary.current_value_credits)
        if context["player"].market_value_eur and context["player"].market_value_eur > 0:
            return self._normalize_amount(credits_from_real_world_value(context["player"].market_value_eur))
        if context["tier"].base_mint_price_credits and Decimal(str(context["tier"].base_mint_price_credits)) > Decimal("0"):
            return self._normalize_amount(context["tier"].base_mint_price_credits)
        return Decimal("1.0000")

    @staticmethod
    def _stringify_amount(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.quantize(AMOUNT_QUANTUM), "f")

    def _market_integrity_config(self) -> PlayerCardMarketIntegrityConfig:
        return self.settings.player_card_market_integrity

    def _recent_player_trade_average(
        self,
        player_id: str,
        *,
        days: int,
        exclude_sale_id: str | None = None,
    ) -> tuple[Decimal | None, int]:
        stmt = (
            select(PlayerCardSale.price_per_card_credits, PlayerCardSale.quantity)
            .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
            .where(
                PlayerCard.player_id == player_id,
                PlayerCardSale.created_at >= datetime.now(UTC) - timedelta(days=days),
            )
            .order_by(PlayerCardSale.created_at.desc())
        )
        if exclude_sale_id:
            stmt = stmt.where(PlayerCardSale.sale_id != exclude_sale_id)
        rows = self.session.execute(stmt).all()
        if not rows:
            return None, 0
        total_quantity = sum(int(row.quantity) for row in rows)
        if total_quantity <= 0:
            return None, len(rows)
        weighted_total = sum(self._normalize_amount(row.price_per_card_credits) * int(row.quantity) for row in rows)
        return self._normalize_amount(weighted_total / Decimal(total_quantity)), len(rows)

    def _reference_price_credits(
        self,
        context: dict[str, Any],
        *,
        exclude_sale_id: str | None = None,
    ) -> tuple[Decimal, str, int]:
        config = self._market_integrity_config()
        average_trade_price, sale_count = self._recent_player_trade_average(
            context["player"].id,
            days=config.sale_reference_lookback_days,
            exclude_sale_id=exclude_sale_id,
        )
        if average_trade_price is not None and sale_count >= config.minimum_reference_sales:
            return average_trade_price, "recent_player_trades", sale_count

        snapshot = self.session.scalar(
            select(PlayerMarketValueSnapshot)
            .where(PlayerMarketValueSnapshot.player_id == context["player"].id)
            .order_by(PlayerMarketValueSnapshot.as_of.desc())
            .limit(1)
        )
        if snapshot is not None:
            for field_name in (
                "avg_trade_price_credits",
                "last_trade_price_credits",
                "listing_floor_price_credits",
            ):
                value = getattr(snapshot, field_name)
                if value is not None and Decimal(str(value)) > Decimal("0"):
                    return self._normalize_amount(value), f"market_snapshot.{field_name}", sale_count

        summary = self.session.get(PlayerSummaryReadModel, context["player"].id)
        if summary is not None and summary.current_value_credits and Decimal(str(summary.current_value_credits)) > Decimal("0"):
            return self._normalize_amount(summary.current_value_credits), "player_summary.current_value", sale_count

        return self._base_value_credits(context), "tier_or_value_fallback", sale_count

    def _latest_recent_cancelled_sale_listing(
        self,
        seller_user_id: str,
        player_card_id: str,
    ) -> datetime | None:
        cooldown_minutes = self._market_integrity_config().relist_cooldown_minutes
        if cooldown_minutes <= 0:
            return None
        window_start = datetime.now(UTC) - timedelta(minutes=cooldown_minutes)
        cancelled_at = self.session.scalar(
            select(func.max(PlayerCardListing.updated_at)).where(
                PlayerCardListing.seller_user_id == seller_user_id,
                PlayerCardListing.player_card_id == player_card_id,
                PlayerCardListing.status == "cancelled",
                PlayerCardListing.updated_at >= window_start,
            )
        )
        return None if cancelled_at is None else self._coerce_utc(cancelled_at)

    def _sale_listing_guardrail_snapshot(
        self,
        *,
        actor: User,
        context: dict[str, Any],
        proposed_price_credits: Decimal,
    ) -> dict[str, Any]:
        config = self._market_integrity_config()
        normalized_price = self._normalize_amount(proposed_price_credits)
        reference_price, reference_source, reference_sale_count = self._reference_price_credits(context)
        floor_price = self._normalize_amount(reference_price * Decimal(str(config.listing_price_floor_ratio)))
        ceiling_price = self._normalize_amount(reference_price * Decimal(str(config.listing_price_ceiling_ratio)))
        price_ratio = Decimal("1.0000")
        if reference_price > Decimal("0"):
            price_ratio = self._normalize_amount(normalized_price / reference_price)
        recent_cancelled_at = self._latest_recent_cancelled_sale_listing(actor.id, context["card"].id)
        cooldown_active = recent_cancelled_at is not None
        cooldown_ends_at = (
            recent_cancelled_at + timedelta(minutes=config.relist_cooldown_minutes)
            if recent_cancelled_at is not None
            else None
        )
        return {
            "reference_source": reference_source,
            "reference_sale_count": reference_sale_count,
            "reference_price_credits": self._stringify_amount(reference_price),
            "listing_price_credits": self._stringify_amount(normalized_price),
            "listing_price_floor_credits": self._stringify_amount(floor_price),
            "listing_price_ceiling_credits": self._stringify_amount(ceiling_price),
            "price_ratio_to_reference": self._stringify_amount(price_ratio),
            "relist_cooldown_minutes": config.relist_cooldown_minutes,
            "relist_cooldown_active": cooldown_active,
            "last_cancelled_at": recent_cancelled_at.isoformat() if recent_cancelled_at is not None else None,
            "cooldown_ends_at": cooldown_ends_at.isoformat() if cooldown_ends_at is not None else None,
        }

    def _enforce_sale_listing_guardrails(
        self,
        *,
        actor: User,
        context: dict[str, Any],
        proposed_price_credits: Decimal,
    ) -> dict[str, Any]:
        snapshot = self._sale_listing_guardrail_snapshot(
            actor=actor,
            context=context,
            proposed_price_credits=proposed_price_credits,
        )
        if snapshot["relist_cooldown_active"]:
            self._audit(
                listing_type="sale",
                action="listing_blocked_cooldown",
                actor_user_id=actor.id,
                player_card_id=context["card"].id,
                payload=snapshot,
            )
            raise PlayerCardValidationError(
                "Sale listing is in relist cooldown after a recent cancellation for this card."
            )

        normalized_price = self._normalize_amount(proposed_price_credits)
        floor_price = Decimal(str(snapshot["listing_price_floor_credits"]))
        ceiling_price = Decimal(str(snapshot["listing_price_ceiling_credits"]))
        if normalized_price < floor_price or normalized_price > ceiling_price:
            self._audit(
                listing_type="sale",
                action="listing_blocked_price_guardrail",
                actor_user_id=actor.id,
                player_card_id=context["card"].id,
                payload=snapshot,
            )
            raise PlayerCardValidationError(
                f"Listing price must stay between {self._stringify_amount(floor_price)} and "
                f"{self._stringify_amount(ceiling_price)} credits for current market integrity controls."
            )
        return snapshot

    def _run_sale_integrity_checks(self, context: dict[str, Any], sale: PlayerCardSale) -> dict[str, Any]:
        config = self._market_integrity_config()
        integrity_service = IntegrityEngineService(self.session)
        risk_service = RiskOpsService(self.session)
        now = datetime.now(UTC)
        signals: list[str] = []

        reference_price, reference_source, reference_sale_count = self._reference_price_credits(
            context,
            exclude_sale_id=sale.sale_id,
        )
        sale_price = self._normalize_amount(sale.price_per_card_credits)
        price_ratio = Decimal("1.0000")
        if reference_price > Decimal("0"):
            price_ratio = self._normalize_amount(sale_price / reference_price)
        anomaly_ratio = Decimal(str(config.price_spike_alert_ratio))
        if reference_price > Decimal("0") and (
            sale_price > reference_price * anomaly_ratio
            or sale_price < reference_price / anomaly_ratio
        ):
            direction = "spike" if sale_price > reference_price else "dump"
            risk_service.create_system_event(
                actor_user_id=None,
                event_key=f"player-card-price-anomaly:{context['player'].id}:{now:%Y%m%d%H}",
                event_type="player_card_price_anomaly",
                severity=SystemEventSeverity.WARNING,
                title="Player card price anomaly",
                body="A player-card settlement cleared far outside the current market reference.",
                subject_type="player",
                subject_id=context["player"].id,
                metadata_json={
                    "sale_id": sale.sale_id,
                    "player_card_id": sale.player_card_id,
                    "direction": direction,
                    "sale_price_credits": self._stringify_amount(sale_price),
                    "reference_price_credits": self._stringify_amount(reference_price),
                    "reference_source": reference_source,
                },
            )
            signals.append("price_anomaly")

        pair_count = self.session.scalar(
            select(func.count(PlayerCardSale.id)).where(
                PlayerCardSale.created_at >= now - timedelta(hours=config.pair_trade_lookback_hours),
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
        ) or 0
        if pair_count >= config.pair_trade_alert_threshold:
            pair_subject = ":".join(sorted((sale.seller_user_id, sale.buyer_user_id)))
            for user_id in (sale.seller_user_id, sale.buyer_user_id):
                integrity_service.register_incident_once(
                    user_id=user_id,
                    incident_type="repeated_card_trade_pair",
                    subject=f"pair:{pair_subject}",
                    severity="high" if pair_count >= config.pair_trade_alert_threshold + 2 else "medium",
                    title="Repeated card trading pair detected",
                    description=(
                        f"{pair_count} player-card trades occurred between the same pair inside the current review window."
                    ),
                    score_delta=Decimal("-12.50"),
                    metadata_json={
                        "pair": [sale.seller_user_id, sale.buyer_user_id],
                        "count": int(pair_count),
                        "window_hours": config.pair_trade_lookback_hours,
                    },
                )
            signals.append("repeated_pair_trade")

        asset_churn_count = self.session.scalar(
            select(func.count(PlayerCardSale.id)).where(
                PlayerCardSale.player_card_id == sale.player_card_id,
                PlayerCardSale.created_at >= now - timedelta(hours=config.asset_churn_window_hours),
            )
        ) or 0
        if asset_churn_count >= config.asset_churn_alert_threshold:
            risk_service.create_system_event(
                actor_user_id=None,
                event_key=f"player-card-asset-churn:{sale.player_card_id}:{now:%Y%m%d%H}",
                event_type="player_card_asset_churn",
                severity=SystemEventSeverity.WARNING,
                title="Player card asset churn detected",
                body="The same player card has been traded repeatedly in a short review window.",
                subject_type="player_card",
                subject_id=sale.player_card_id,
                metadata_json={
                    "player_card_id": sale.player_card_id,
                    "count": int(asset_churn_count),
                    "window_hours": config.asset_churn_window_hours,
                },
            )
            signals.append("asset_churn")

        recent_sales = list(
            self.session.scalars(
                select(PlayerCardSale)
                .where(
                    PlayerCardSale.player_card_id == sale.player_card_id,
                    PlayerCardSale.created_at >= now - timedelta(hours=config.circular_trade_window_hours),
                )
                .order_by(PlayerCardSale.created_at.desc())
                .limit(3)
            ).all()
        )
        circular_trade_detected = False
        if len(recent_sales) == 3:
            unique_users = {row.seller_user_id for row in recent_sales} | {row.buyer_user_id for row in recent_sales}
            directions = [(row.seller_user_id, row.buyer_user_id) for row in recent_sales]
            circular_trade_detected = len(unique_users) == 2 and directions[0] == directions[2] and directions[0] != directions[1]
            if circular_trade_detected:
                loop_subject = f"loop:{sale.player_card_id}:{now:%Y%m%d%H}"
                for user_id in (sale.seller_user_id, sale.buyer_user_id):
                    integrity_service.register_incident_once(
                        user_id=user_id,
                        incident_type="circular_card_trading",
                        subject=loop_subject,
                        severity="high",
                        title="Circular player-card trading detected",
                        description="Recent settlements show the same card moving back and forth between the same accounts.",
                        score_delta=Decimal("-15.00"),
                        metadata_json={
                            "player_card_id": sale.player_card_id,
                            "sequence": directions,
                            "window_hours": config.circular_trade_window_hours,
                        },
                    )
                signals.append("circular_trade")

        volume_cluster_count = self.session.scalar(
            select(func.count(PlayerCardSale.id))
            .join(PlayerCard, PlayerCardSale.player_card_id == PlayerCard.id)
            .where(
                PlayerCard.player_id == context["player"].id,
                PlayerCardSale.created_at >= now - timedelta(minutes=config.volume_cluster_window_minutes),
            )
        ) or 0
        if volume_cluster_count >= config.volume_cluster_trade_threshold:
            risk_service.create_system_event(
                actor_user_id=None,
                event_key=f"player-card-volume-cluster:{context['player'].id}:{now:%Y%m%d%H}",
                event_type="player_card_volume_cluster",
                severity=SystemEventSeverity.WARNING,
                title="Player card volume cluster detected",
                body="Player-card trading volume surged above the configured review threshold.",
                subject_type="player",
                subject_id=context["player"].id,
                metadata_json={
                    "player_id": context["player"].id,
                    "count": int(volume_cluster_count),
                    "window_minutes": config.volume_cluster_window_minutes,
                },
            )
            signals.append("volume_cluster")

        return {
            "reference_source": reference_source,
            "reference_sale_count": reference_sale_count,
            "reference_price_credits": self._stringify_amount(reference_price),
            "sale_price_credits": self._stringify_amount(sale_price),
            "price_ratio_to_reference": self._stringify_amount(price_ratio),
            "pair_trade_count": int(pair_count),
            "asset_churn_count": int(asset_churn_count),
            "volume_cluster_count": int(volume_cluster_count),
            "circular_trade_detected": circular_trade_detected,
            "signals": signals,
        }

    def _loan_economics(self, context: dict[str, Any], requested_fee_credits: Decimal) -> dict[str, Any]:
        normalized_requested_fee = self._normalize_amount(requested_fee_credits)
        base_value = self._base_value_credits(context)
        effective_fee = normalized_requested_fee
        fee_floor_applied = False
        if normalized_requested_fee == Decimal("0.0000"):
            effective_fee = self._normalize_amount(base_value * FREE_LOAN_FLOOR_RATIO)
            fee_floor_applied = True
        platform_fee_bps = REGEN_LOAN_PLATFORM_FEE_BPS if context["is_regen_newgen"] else NORMAL_LOAN_PLATFORM_FEE_BPS
        platform_fee = self._normalize_amount(effective_fee * Decimal(platform_fee_bps) / Decimal(10_000))
        lender_net = self._normalize_amount(effective_fee - platform_fee)
        return {
            "base_value_credits": base_value,
            "requested_fee_credits": normalized_requested_fee,
            "effective_fee_credits": effective_fee,
            "platform_fee_credits": platform_fee,
            "lender_net_credits": lender_net,
            "platform_fee_bps": platform_fee_bps,
            "fee_floor_applied": fee_floor_applied,
        }

    def _ensure_borrower_has_no_player_version(self, user_id: str, player_id: str) -> None:
        held_version = self.session.scalar(
            select(func.count(PlayerCardHolding.id))
            .join(PlayerCard, PlayerCard.id == PlayerCardHolding.player_card_id)
            .where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.quantity_total > 0,
                PlayerCard.player_id == player_id,
            )
        ) or 0
        if held_version > 0:
            raise PlayerCardValidationError("You already control a version of this player.")
        active_loan = self.session.scalar(
            select(func.count(CardLoanContract.id))
            .join(PlayerCard, PlayerCard.id == CardLoanContract.player_card_id)
            .where(
                CardLoanContract.borrower_user_id == user_id,
                CardLoanContract.status.in_(("accepted_pending_settlement", "active")),
                PlayerCard.player_id == player_id,
            )
        ) or 0
        if active_loan > 0:
            raise PlayerCardValidationError("You already have a loan workflow in progress for this player.")

    def _ensure_usage_allowed(
        self,
        restrictions: dict[str, Any] | None,
        *,
        competition_id: str | None,
        squad_scope: str | None,
    ) -> None:
        payload = restrictions or {}
        allowed_competitions = {str(item) for item in payload.get("allowed_competition_ids", [])}
        blocked_competitions = {str(item) for item in payload.get("blocked_competition_ids", [])}
        allowed_squad_scopes = {str(item) for item in payload.get("allowed_squad_scopes", [])}
        if competition_id and allowed_competitions and competition_id not in allowed_competitions:
            raise PlayerCardValidationError("This loan is not eligible for the requested competition.")
        if competition_id and competition_id in blocked_competitions:
            raise PlayerCardValidationError("This loan is blocked from the requested competition.")
        if squad_scope and allowed_squad_scopes and squad_scope not in allowed_squad_scopes:
            raise PlayerCardValidationError("This loan cannot be used in the requested squad scope.")

    def _asset_origin_expr(self):
        regen_exists = select(RegenProfile.id).where(RegenProfile.linked_unique_card_id == PlayerCard.id).limit(1).exists()
        creator_exists = (
            select(CreatorCard.id)
            .where(CreatorCard.player_id == PlayerCard.player_id, CreatorCard.status == "active")
            .limit(1)
            .exists()
        )
        is_regen_expr = or_(func.lower(func.coalesce(PlayerCard.card_variant, "")).like("regen%"), regen_exists)
        asset_origin_expr = case(
            (is_regen_expr, literal("regen_newgen")),
            (creator_exists, literal("creator_linked")),
            else_=literal("standard"),
        )
        return is_regen_expr, creator_exists, asset_origin_expr

    def _search_relevance(self, search: str | None):
        if not search or not search.strip():
            return literal(100), literal(True)
        normalized = search.strip().lower()
        full_name = func.lower(func.coalesce(Player.full_name, ""))
        short_name = func.lower(func.coalesce(Player.short_name, ""))
        club_name = func.lower(func.coalesce(PlayerSummaryReadModel.current_club_name, ""))
        normalized_position = func.lower(func.coalesce(Player.normalized_position, ""))
        raw_position = func.lower(func.coalesce(Player.position, ""))
        tier_code = func.lower(func.coalesce(PlayerCardTier.code, ""))
        tier_name = func.lower(func.coalesce(PlayerCardTier.name, ""))
        edition_code = func.lower(func.coalesce(PlayerCard.edition_code, ""))
        alias_exact = select(PlayerAlias.id).where(PlayerAlias.player_id == Player.id, func.lower(PlayerAlias.alias) == normalized).limit(1).exists()
        alias_prefix = select(PlayerAlias.id).where(PlayerAlias.player_id == Player.id, func.lower(PlayerAlias.alias).like(f"{normalized}%")).limit(1).exists()
        alias_contains = select(PlayerAlias.id).where(PlayerAlias.player_id == Player.id, func.lower(PlayerAlias.alias).like(f"%{normalized}%")).limit(1).exists()
        moniker_exact = select(PlayerMoniker.id).where(PlayerMoniker.player_id == Player.id, func.lower(PlayerMoniker.moniker) == normalized).limit(1).exists()
        moniker_prefix = select(PlayerMoniker.id).where(PlayerMoniker.player_id == Player.id, func.lower(PlayerMoniker.moniker).like(f"{normalized}%")).limit(1).exists()
        moniker_contains = select(PlayerMoniker.id).where(PlayerMoniker.player_id == Player.id, func.lower(PlayerMoniker.moniker).like(f"%{normalized}%")).limit(1).exists()
        filter_expr = or_(
            full_name.like(f"%{normalized}%"),
            short_name.like(f"%{normalized}%"),
            alias_contains,
            moniker_contains,
            club_name.like(f"%{normalized}%"),
            normalized_position.like(f"%{normalized}%"),
            raw_position.like(f"%{normalized}%"),
            tier_code.like(f"%{normalized}%"),
            tier_name.like(f"%{normalized}%"),
            edition_code.like(f"%{normalized}%"),
        )
        rank_expr = case(
            (full_name == normalized, 0),
            (short_name == normalized, 1),
            (alias_exact, 2),
            (moniker_exact, 3),
            (club_name == normalized, 4),
            (normalized_position == normalized, 5),
            (raw_position == normalized, 6),
            (tier_code == normalized, 7),
            (tier_name == normalized, 8),
            (edition_code == normalized, 9),
            (full_name.like(f"{normalized}%"), 10),
            (short_name.like(f"{normalized}%"), 11),
            (alias_prefix, 12),
            (moniker_prefix, 13),
            (club_name.like(f"{normalized}%"), 14),
            (normalized_position.like(f"{normalized}%"), 15),
            (raw_position.like(f"{normalized}%"), 16),
            (tier_code.like(f"{normalized}%"), 17),
            (tier_name.like(f"{normalized}%"), 18),
            (edition_code.like(f"{normalized}%"), 19),
            (full_name.like(f"%{normalized}%"), 20),
            (short_name.like(f"%{normalized}%"), 21),
            (alias_contains, 22),
            (moniker_contains, 23),
            (club_name.like(f"%{normalized}%"), 24),
            (normalized_position.like(f"%{normalized}%"), 25),
            (raw_position.like(f"%{normalized}%"), 26),
            (tier_code.like(f"%{normalized}%"), 27),
            (tier_name.like(f"%{normalized}%"), 28),
            (edition_code.like(f"%{normalized}%"), 29),
            else_=100,
        )
        return rank_expr, filter_expr

    def _common_market_filters(
        self,
        *,
        search: str | None,
        club: str | None,
        position: str | None,
        rating_min: float | None,
        rating_max: float | None,
        tier_code: str | None,
        rarity_rank_min: int | None,
        rarity_rank_max: int | None,
        asset_origin: str | None,
        availability: str,
        availability_expr,
        negotiable: bool | None,
        is_negotiable_expr,
        asset_origin_expr,
    ) -> tuple[Any, list[Any]]:
        rank_expr, search_filter = self._search_relevance(search)
        filters: list[Any] = []
        if search and search.strip():
            filters.append(search_filter)
        if club:
            filters.append(func.lower(func.coalesce(PlayerSummaryReadModel.current_club_name, "")).like(f"%{club.strip().lower()}%"))
        if position:
            normalized_position = position.strip().lower()
            filters.append(
                or_(
                    func.lower(func.coalesce(Player.normalized_position, "")) == normalized_position,
                    func.lower(func.coalesce(Player.position, "")) == normalized_position,
                )
            )
        if rating_min is not None:
            filters.append(PlayerSummaryReadModel.average_rating >= rating_min)
        if rating_max is not None:
            filters.append(PlayerSummaryReadModel.average_rating <= rating_max)
        if tier_code:
            filters.append(func.lower(PlayerCardTier.code) == tier_code.strip().lower())
        if rarity_rank_min is not None:
            filters.append(PlayerCardTier.rarity_rank >= rarity_rank_min)
        if rarity_rank_max is not None:
            filters.append(PlayerCardTier.rarity_rank <= rarity_rank_max)
        if asset_origin:
            filters.append(asset_origin_expr == asset_origin.strip().lower())
        if availability == "available":
            filters.append(availability_expr == "available")
        elif availability == "unavailable":
            filters.append(availability_expr == "unavailable")
        if negotiable is not None:
            filters.append(is_negotiable_expr.is_(negotiable))
        return rank_expr, filters

    def _build_sale_search_query(
        self,
        *,
        search: str | None,
        club: str | None,
        position: str | None,
        rating_min: float | None,
        rating_max: float | None,
        tier_code: str | None,
        rarity_rank_min: int | None,
        rarity_rank_max: int | None,
        asset_origin: str | None,
        sale_price_min: Decimal | None,
        sale_price_max: Decimal | None,
        availability: str,
        negotiable: bool | None,
    ):
        availability_expr = case(
            (
                and_(
                    PlayerCardListing.status == "open",
                    PlayerCardListing.quantity > 0,
                    or_(PlayerCardListing.expires_at.is_(None), PlayerCardListing.expires_at > datetime.now(UTC)),
                ),
                literal("available"),
            ),
            else_=literal("unavailable"),
        )
        is_regen_expr, is_creator_expr, asset_origin_expr = self._asset_origin_expr()
        rank_expr, filters = self._common_market_filters(
            search=search,
            club=club,
            position=position,
            rating_min=rating_min,
            rating_max=rating_max,
            tier_code=tier_code,
            rarity_rank_min=rarity_rank_min,
            rarity_rank_max=rarity_rank_max,
            asset_origin=asset_origin,
            availability=availability,
            availability_expr=availability_expr,
            negotiable=negotiable,
            is_negotiable_expr=PlayerCardListing.is_negotiable,
            asset_origin_expr=asset_origin_expr,
        )
        if sale_price_min is not None:
            filters.append(PlayerCardListing.price_per_card_credits >= self._normalize_amount(sale_price_min))
        if sale_price_max is not None:
            filters.append(PlayerCardListing.price_per_card_credits <= self._normalize_amount(sale_price_max))
        return (
            select(
                literal("sale").label("listing_type"),
                PlayerCardListing.listing_id.label("listing_id"),
                PlayerCard.id.label("player_card_id"),
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                PlayerSummaryReadModel.current_club_name.label("club_name"),
                func.coalesce(Player.normalized_position, Player.position).label("position"),
                PlayerSummaryReadModel.average_rating.label("average_rating"),
                PlayerCardTier.code.label("tier_code"),
                PlayerCardTier.name.label("tier_name"),
                PlayerCardTier.rarity_rank.label("rarity_rank"),
                PlayerCard.edition_code.label("edition_code"),
                PlayerCardListing.seller_user_id.label("listing_owner_user_id"),
                PlayerCardListing.status.label("status"),
                availability_expr.label("availability"),
                PlayerCardListing.is_negotiable.label("is_negotiable"),
                asset_origin_expr.label("asset_origin"),
                is_regen_expr.label("is_regen_newgen"),
                is_creator_expr.label("is_creator_linked"),
                PlayerCardListing.quantity.label("quantity"),
                PlayerCardListing.quantity.label("available_quantity"),
                PlayerCardListing.price_per_card_credits.label("sale_price_credits"),
                cast(literal(None), Numeric(18, 4)).label("loan_fee_credits"),
                cast(literal(None), Integer).label("loan_duration_days"),
                cast(literal(None), String(36)).label("requested_player_card_id"),
                cast(literal(None), String(36)).label("requested_player_id"),
                literal("{}").label("requested_filters_json"),
                PlayerCardListing.created_at.label("created_at"),
                PlayerCardListing.expires_at.label("expires_at"),
                PlayerCardListing.price_per_card_credits.label("search_price"),
                rank_expr.label("search_rank"),
            )
            .join(PlayerCard, PlayerCard.id == PlayerCardListing.player_card_id)
            .join(PlayerCardTier, PlayerCardTier.id == PlayerCard.tier_id)
            .join(Player, Player.id == PlayerCard.player_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(*filters)
        )

    def _build_loan_search_query(
        self,
        *,
        search: str | None,
        club: str | None,
        position: str | None,
        rating_min: float | None,
        rating_max: float | None,
        tier_code: str | None,
        rarity_rank_min: int | None,
        rarity_rank_max: int | None,
        asset_origin: str | None,
        loan_fee_min: Decimal | None,
        loan_fee_max: Decimal | None,
        loan_duration_min: int | None,
        loan_duration_max: int | None,
        availability: str,
        negotiable: bool | None,
    ):
        availability_expr = case(
            (
                and_(
                    CardLoanListing.status == "open",
                    CardLoanListing.available_slots > 0,
                    or_(CardLoanListing.expires_at.is_(None), CardLoanListing.expires_at > datetime.now(UTC)),
                ),
                literal("available"),
            ),
            else_=literal("unavailable"),
        )
        is_regen_expr, is_creator_expr, asset_origin_expr = self._asset_origin_expr()
        rank_expr, filters = self._common_market_filters(
            search=search,
            club=club,
            position=position,
            rating_min=rating_min,
            rating_max=rating_max,
            tier_code=tier_code,
            rarity_rank_min=rarity_rank_min,
            rarity_rank_max=rarity_rank_max,
            asset_origin=asset_origin,
            availability=availability,
            availability_expr=availability_expr,
            negotiable=negotiable,
            is_negotiable_expr=CardLoanListing.is_negotiable,
            asset_origin_expr=asset_origin_expr,
        )
        if loan_fee_min is not None:
            filters.append(CardLoanListing.loan_fee_credits >= self._normalize_amount(loan_fee_min))
        if loan_fee_max is not None:
            filters.append(CardLoanListing.loan_fee_credits <= self._normalize_amount(loan_fee_max))
        if loan_duration_min is not None:
            filters.append(CardLoanListing.duration_days >= loan_duration_min)
        if loan_duration_max is not None:
            filters.append(CardLoanListing.duration_days <= loan_duration_max)
        return (
            select(
                literal("loan").label("listing_type"),
                CardLoanListing.id.label("listing_id"),
                PlayerCard.id.label("player_card_id"),
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                PlayerSummaryReadModel.current_club_name.label("club_name"),
                func.coalesce(Player.normalized_position, Player.position).label("position"),
                PlayerSummaryReadModel.average_rating.label("average_rating"),
                PlayerCardTier.code.label("tier_code"),
                PlayerCardTier.name.label("tier_name"),
                PlayerCardTier.rarity_rank.label("rarity_rank"),
                PlayerCard.edition_code.label("edition_code"),
                CardLoanListing.owner_user_id.label("listing_owner_user_id"),
                CardLoanListing.status.label("status"),
                availability_expr.label("availability"),
                CardLoanListing.is_negotiable.label("is_negotiable"),
                asset_origin_expr.label("asset_origin"),
                is_regen_expr.label("is_regen_newgen"),
                is_creator_expr.label("is_creator_linked"),
                CardLoanListing.total_slots.label("quantity"),
                CardLoanListing.available_slots.label("available_quantity"),
                cast(literal(None), Numeric(18, 4)).label("sale_price_credits"),
                CardLoanListing.loan_fee_credits.label("loan_fee_credits"),
                CardLoanListing.duration_days.label("loan_duration_days"),
                cast(literal(None), String(36)).label("requested_player_card_id"),
                cast(literal(None), String(36)).label("requested_player_id"),
                literal("{}").label("requested_filters_json"),
                CardLoanListing.created_at.label("created_at"),
                CardLoanListing.expires_at.label("expires_at"),
                CardLoanListing.loan_fee_credits.label("search_price"),
                rank_expr.label("search_rank"),
            )
            .join(PlayerCard, PlayerCard.id == CardLoanListing.player_card_id)
            .join(PlayerCardTier, PlayerCardTier.id == PlayerCard.tier_id)
            .join(Player, Player.id == PlayerCard.player_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(*filters)
        )

    def _build_swap_search_query(
        self,
        *,
        search: str | None,
        club: str | None,
        position: str | None,
        rating_min: float | None,
        rating_max: float | None,
        tier_code: str | None,
        rarity_rank_min: int | None,
        rarity_rank_max: int | None,
        asset_origin: str | None,
        availability: str,
        negotiable: bool | None,
    ):
        availability_expr = case(
            (
                and_(
                    CardSwapListing.status == "open",
                    or_(CardSwapListing.expires_at.is_(None), CardSwapListing.expires_at > datetime.now(UTC)),
                ),
                literal("available"),
            ),
            else_=literal("unavailable"),
        )
        is_regen_expr, is_creator_expr, asset_origin_expr = self._asset_origin_expr()
        rank_expr, filters = self._common_market_filters(
            search=search,
            club=club,
            position=position,
            rating_min=rating_min,
            rating_max=rating_max,
            tier_code=tier_code,
            rarity_rank_min=rarity_rank_min,
            rarity_rank_max=rarity_rank_max,
            asset_origin=asset_origin,
            availability=availability,
            availability_expr=availability_expr,
            negotiable=negotiable,
            is_negotiable_expr=CardSwapListing.is_negotiable,
            asset_origin_expr=asset_origin_expr,
        )
        return (
            select(
                literal("swap").label("listing_type"),
                CardSwapListing.id.label("listing_id"),
                PlayerCard.id.label("player_card_id"),
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                PlayerSummaryReadModel.current_club_name.label("club_name"),
                func.coalesce(Player.normalized_position, Player.position).label("position"),
                PlayerSummaryReadModel.average_rating.label("average_rating"),
                PlayerCardTier.code.label("tier_code"),
                PlayerCardTier.name.label("tier_name"),
                PlayerCardTier.rarity_rank.label("rarity_rank"),
                PlayerCard.edition_code.label("edition_code"),
                CardSwapListing.owner_user_id.label("listing_owner_user_id"),
                CardSwapListing.status.label("status"),
                availability_expr.label("availability"),
                CardSwapListing.is_negotiable.label("is_negotiable"),
                asset_origin_expr.label("asset_origin"),
                is_regen_expr.label("is_regen_newgen"),
                is_creator_expr.label("is_creator_linked"),
                cast(literal(1), Integer).label("quantity"),
                cast(literal(1), Integer).label("available_quantity"),
                cast(literal(None), Numeric(18, 4)).label("sale_price_credits"),
                cast(literal(None), Numeric(18, 4)).label("loan_fee_credits"),
                cast(literal(None), Integer).label("loan_duration_days"),
                CardSwapListing.requested_player_card_id.label("requested_player_card_id"),
                CardSwapListing.requested_player_id.label("requested_player_id"),
                cast(CardSwapListing.desired_filters_json, String).label("requested_filters_json"),
                CardSwapListing.created_at.label("created_at"),
                CardSwapListing.expires_at.label("expires_at"),
                cast(literal(None), Numeric(18, 4)).label("search_price"),
                rank_expr.label("search_rank"),
            )
            .join(PlayerCard, PlayerCard.id == CardSwapListing.player_card_id)
            .join(PlayerCardTier, PlayerCardTier.id == PlayerCard.tier_id)
            .join(Player, Player.id == PlayerCard.player_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(*filters)
        )

    def _search_listing_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        requested_filters = payload.pop("requested_filters_json", None)
        if requested_filters in {None, "", "null"}:
            payload["requested_filters_json"] = {}
        elif isinstance(requested_filters, str):
            try:
                payload["requested_filters_json"] = json.loads(requested_filters)
            except json.JSONDecodeError:
                payload["requested_filters_json"] = {}
        else:
            payload["requested_filters_json"] = dict(requested_filters or {})
        payload.pop("search_price", None)
        payload.pop("search_rank", None)
        payload["avatar"] = self.avatar_service.build_from_payload(
            AvatarIdentityInput(
                player_id=str(payload.get("player_id") or ""),
                player_name=str(payload.get("player_name") or ""),
                position=payload.get("position"),
                avatar_seed_token=payload.get("avatar_seed_token"),
                avatar_dna_seed=payload.get("avatar_dna_seed"),
            )
        ).model_dump()
        return payload

    def search_marketplace(
        self,
        *,
        listing_type: str | None = None,
        search: str | None = None,
        club: str | None = None,
        position: str | None = None,
        rating_min: float | None = None,
        rating_max: float | None = None,
        tier_code: str | None = None,
        rarity_rank_min: int | None = None,
        rarity_rank_max: int | None = None,
        asset_origin: str | None = None,
        sale_price_min: Decimal | None = None,
        sale_price_max: Decimal | None = None,
        loan_fee_min: Decimal | None = None,
        loan_fee_max: Decimal | None = None,
        loan_duration_min: int | None = None,
        loan_duration_max: int | None = None,
        availability: str = "available",
        negotiable: bool | None = None,
        sort: str = "relevance",
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        normalized_listing_type = None if listing_type is None else listing_type.strip().lower()
        if normalized_listing_type not in {None, "sale", "loan", "swap"}:
            raise PlayerCardValidationError("Listing type must be one of sale, loan, or swap.")
        normalized_availability = availability.strip().lower()
        if normalized_availability not in {"available", "unavailable", "all"}:
            raise PlayerCardValidationError("Availability must be one of available, unavailable, or all.")
        normalized_sort = sort.strip().lower()
        if normalized_sort not in {"relevance", "newest", "cheapest", "highest_rated"}:
            raise PlayerCardValidationError("Sort must be one of relevance, newest, cheapest, or highest_rated.")

        queries: list[Any] = []
        if normalized_listing_type in {None, "sale"}:
            queries.append(
                self._build_sale_search_query(
                    search=search,
                    club=club,
                    position=position,
                    rating_min=rating_min,
                    rating_max=rating_max,
                    tier_code=tier_code,
                    rarity_rank_min=rarity_rank_min,
                    rarity_rank_max=rarity_rank_max,
                    asset_origin=asset_origin,
                    sale_price_min=sale_price_min,
                    sale_price_max=sale_price_max,
                    availability=normalized_availability,
                    negotiable=negotiable,
                )
            )
        if normalized_listing_type in {None, "loan"}:
            queries.append(
                self._build_loan_search_query(
                    search=search,
                    club=club,
                    position=position,
                    rating_min=rating_min,
                    rating_max=rating_max,
                    tier_code=tier_code,
                    rarity_rank_min=rarity_rank_min,
                    rarity_rank_max=rarity_rank_max,
                    asset_origin=asset_origin,
                    loan_fee_min=loan_fee_min,
                    loan_fee_max=loan_fee_max,
                    loan_duration_min=loan_duration_min,
                    loan_duration_max=loan_duration_max,
                    availability=normalized_availability,
                    negotiable=negotiable,
                )
            )
        if normalized_listing_type in {None, "swap"} and all(
            value is None for value in (sale_price_min, sale_price_max, loan_fee_min, loan_fee_max, loan_duration_min, loan_duration_max)
        ):
            queries.append(
                self._build_swap_search_query(
                    search=search,
                    club=club,
                    position=position,
                    rating_min=rating_min,
                    rating_max=rating_max,
                    tier_code=tier_code,
                    rarity_rank_min=rarity_rank_min,
                    rarity_rank_max=rarity_rank_max,
                    asset_origin=asset_origin,
                    availability=normalized_availability,
                    negotiable=negotiable,
                )
            )
        if not queries:
            return {"total": 0, "limit": limit, "offset": offset, "items": []}

        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        offset = max(0, offset)
        listings_subquery = union_all(*queries).subquery()
        total = int(self.session.scalar(select(func.count()).select_from(listings_subquery)) or 0)
        statement = select(listings_subquery)

        null_rating = case((listings_subquery.c.average_rating.is_(None), 1), else_=0)
        null_price = case((listings_subquery.c.search_price.is_(None), 1), else_=0)
        if normalized_sort == "relevance" and search:
            statement = statement.order_by(listings_subquery.c.search_rank.asc(), null_rating.asc(), listings_subquery.c.average_rating.desc(), listings_subquery.c.created_at.desc())
        elif normalized_sort == "newest" or (normalized_sort == "relevance" and not search):
            statement = statement.order_by(listings_subquery.c.created_at.desc())
        elif normalized_sort == "cheapest":
            statement = statement.order_by(null_price.asc(), listings_subquery.c.search_price.asc(), listings_subquery.c.created_at.desc())
        else:
            statement = statement.order_by(null_rating.asc(), listings_subquery.c.average_rating.desc(), listings_subquery.c.created_at.desc())

        rows = self.session.execute(statement.offset(offset).limit(limit)).mappings().all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [self._search_listing_payload(dict(row)) for row in rows],
        }

    def _sale_listing_payload(self, listing: PlayerCardListing, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "listing_id": listing.listing_id,
            "listing_type": "sale",
            "player_card_id": context["card"].id,
            "player_id": context["player"].id,
            "player_name": context["player"].full_name,
            "club_name": context["club_name"],
            "position": context["player"].normalized_position or context["player"].position,
            "average_rating": float(context["average_rating"]) if context["average_rating"] is not None else None,
            "avatar": context["avatar"],
            "tier_code": context["tier"].code,
            "tier_name": context["tier"].name,
            "rarity_rank": context["tier"].rarity_rank,
            "edition_code": context["card"].edition_code,
            "listing_owner_user_id": listing.seller_user_id,
            "status": listing.status,
            "availability": "available" if listing.status == "open" and not self._is_expired(listing.expires_at) else "unavailable",
            "is_negotiable": listing.is_negotiable,
            "asset_origin": context["asset_origin"],
            "is_regen_newgen": context["is_regen_newgen"],
            "is_creator_linked": context["is_creator_linked"],
            "quantity": listing.quantity,
            "available_quantity": listing.quantity if listing.status == "open" else 0,
            "sale_price_credits": self._normalize_amount(listing.price_per_card_credits),
            "created_at": listing.created_at,
            "expires_at": listing.expires_at,
            "requested_filters_json": {},
        }

    def _sale_execution_payload(self, sale: PlayerCardSale) -> dict[str, Any]:
        return {
            "sale_id": sale.sale_id,
            "listing_id": sale.listing_id,
            "player_card_id": sale.player_card_id,
            "seller_user_id": sale.seller_user_id,
            "buyer_user_id": sale.buyer_user_id,
            "quantity": sale.quantity,
            "price_per_card_credits": self._normalize_amount(sale.price_per_card_credits),
            "gross_credits": self._normalize_amount(sale.gross_credits),
            "fee_credits": self._normalize_amount(sale.fee_credits),
            "seller_net_credits": self._normalize_amount(sale.seller_net_credits),
            "status": sale.status,
            "settlement_reference": sale.settlement_reference,
            "created_at": sale.created_at,
        }

    def create_sale_listing(
        self,
        *,
        actor: User,
        player_card_id: str,
        quantity: int,
        price_per_card_credits: Decimal,
        is_negotiable: bool = False,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        if quantity <= 0:
            raise PlayerCardValidationError("Listing quantity must be positive.")
        if price_per_card_credits <= Decimal("0"):
            raise PlayerCardValidationError("Listing price must be positive.")

        context = self._get_card_context(player_card_id)
        holding = self._get_holding(actor.id, player_card_id)
        if self._available_holding_quantity(holding) < quantity:
            raise PlayerCardValidationError("Not enough unreserved card quantity is available to list for sale.")
        integrity_snapshot = self._enforce_sale_listing_guardrails(
            actor=actor,
            context=context,
            proposed_price_credits=price_per_card_credits,
        )

        holding.quantity_reserved += quantity
        listing = PlayerCardListing(
            listing_id=self._new_public_id("sale"),
            player_card_id=player_card_id,
            seller_user_id=actor.id,
            quantity=quantity,
            price_per_card_credits=self._normalize_amount(price_per_card_credits),
            status="open",
            is_negotiable=is_negotiable,
            expires_at=expires_at,
            integrity_context_json=integrity_snapshot,
            metadata_json={"source": "marketplace_v2"},
        )
        self.session.add(listing)
        self._append_card_history(player_card_id, "marketplace.sale.listed", actor.id, metadata={"listing_id": listing.listing_id})
        self._append_owner_history(
            player_card_id,
            from_user_id=actor.id,
            to_user_id=None,
            quantity=quantity,
            event_type="marketplace_sale_listed",
            reference_id=listing.listing_id,
        )
        self._audit(
            listing_type="sale",
            action="listing_created",
            actor_user_id=actor.id,
            player_card_id=player_card_id,
            listing_id=listing.listing_id,
            status_to="open",
            payload={
                "quantity": quantity,
                "price_per_card_credits": str(listing.price_per_card_credits),
                "is_negotiable": is_negotiable,
                "integrity": integrity_snapshot,
            },
        )
        self.session.flush()
        return self._sale_listing_payload(listing, context)

    def cancel_sale_listing(self, *, actor: User, listing_id: str) -> dict[str, Any]:
        listing = self._get_sale_listing(listing_id)
        if listing.seller_user_id != actor.id:
            raise PlayerCardPermissionError("Only the listing owner can cancel this sale listing.")
        if listing.status != "open":
            raise PlayerCardValidationError("Only open sale listings can be cancelled.")
        holding = self._get_holding(actor.id, listing.player_card_id)
        holding.quantity_reserved = max(holding.quantity_reserved - listing.quantity, 0)
        previous_status = listing.status
        listing.status = "cancelled"
        self._audit(
            listing_type="sale",
            action="listing_cancelled",
            actor_user_id=actor.id,
            player_card_id=listing.player_card_id,
            listing_id=listing.listing_id,
            status_from=previous_status,
            status_to=listing.status,
        )
        self.session.flush()
        return self._sale_listing_payload(listing, self._get_card_context(listing.player_card_id))

    def buy_sale_listing(self, *, actor: User, listing_id: str, quantity: int | None = None) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        listing = self._get_sale_listing(listing_id)
        if listing.status != "open" or self._is_expired(listing.expires_at):
            raise PlayerCardValidationError("Sale listing is not available.")
        if listing.seller_user_id == actor.id:
            raise PlayerCardValidationError("You cannot buy your own listing.")
        if quantity is None:
            quantity = listing.quantity
        if quantity <= 0 or quantity > listing.quantity:
            raise PlayerCardValidationError("Purchase quantity is invalid.")

        seller = self._get_user(listing.seller_user_id)
        gross = self._normalize_amount(Decimal(listing.price_per_card_credits) * Decimal(quantity))
        fee = self._normalize_amount(gross * Decimal(NORMAL_LOAN_PLATFORM_FEE_BPS) / Decimal(10_000))
        seller_net = self._normalize_amount(gross - fee)
        settlement_reference = f"player-card-marketplace-sale:{listing.listing_id}:{generate_uuid()}"

        buyer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.CREDIT)
        seller_account = self.wallet_service.get_user_account(self.session, seller, LedgerUnit.CREDIT)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=buyer_account, amount=-gross, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                LedgerPosting(account=seller_account, amount=seller_net, source_tag=LedgerSourceTag.PLAYER_CARD_SALE),
                LedgerPosting(account=platform_account, amount=fee, source_tag=LedgerSourceTag.TRADING_FEE_BURN),
            ],
            reason=self.wallet_service.trade_settlement_reason,
            reference=settlement_reference,
            description="Player card marketplace sale settlement",
            external_reference=settlement_reference,
            actor=actor,
        )

        seller_holding = self._get_holding(seller.id, listing.player_card_id)
        seller_holding.quantity_reserved = max(seller_holding.quantity_reserved - quantity, 0)
        seller_holding.quantity_total = max(seller_holding.quantity_total - quantity, 0)
        if seller_holding.quantity_total == 0:
            self.session.delete(seller_holding)

        buyer_holding = self._get_or_create_holding(actor.id, listing.player_card_id)
        buyer_holding.quantity_total += quantity
        buyer_holding.last_acquired_at = datetime.now(UTC)

        previous_status = listing.status
        if quantity == listing.quantity:
            listing.status = "sold"
        else:
            listing.quantity -= quantity

        sale = PlayerCardSale(
            sale_id=self._new_public_id("sale_exec"),
            listing_id=listing.listing_id,
            player_card_id=listing.player_card_id,
            seller_user_id=seller.id,
            buyer_user_id=actor.id,
            quantity=quantity,
            price_per_card_credits=self._normalize_amount(listing.price_per_card_credits),
            gross_credits=gross,
            fee_credits=fee,
            seller_net_credits=seller_net,
            status="settled",
            settlement_reference=settlement_reference,
            integrity_flags_json={},
            metadata_json={"source": "marketplace_v2"},
        )
        self.session.add(sale)
        self._append_owner_history(
            listing.player_card_id,
            from_user_id=seller.id,
            to_user_id=actor.id,
            quantity=quantity,
            event_type="marketplace_sale_settled",
            reference_id=sale.sale_id,
        )
        self._append_card_history(listing.player_card_id, "marketplace.sale.settled", actor.id, metadata={"sale_id": sale.sale_id})
        self._audit(
            listing_type="sale",
            action="sale_settled",
            actor_user_id=actor.id,
            player_card_id=listing.player_card_id,
            listing_id=listing.listing_id,
            status_from=previous_status,
            status_to=listing.status,
            payload={"sale_id": sale.sale_id, "gross_credits": str(gross), "fee_credits": str(fee), "seller_net_credits": str(seller_net)},
        )
        self.session.flush()
        sale.integrity_flags_json = self._run_sale_integrity_checks(self._get_card_context(listing.player_card_id), sale)
        self.session.flush()
        return self._sale_execution_payload(sale)

    def _loan_listing_payload(self, listing: CardLoanListing, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "listing_id": listing.id,
            "player_card_id": context["card"].id,
            "player_id": context["player"].id,
            "player_name": context["player"].full_name,
            "club_name": context["club_name"],
            "position": context["player"].normalized_position or context["player"].position,
            "average_rating": float(context["average_rating"]) if context["average_rating"] is not None else None,
            "avatar": context["avatar"],
            "tier_code": context["tier"].code,
            "tier_name": context["tier"].name,
            "rarity_rank": context["tier"].rarity_rank,
            "edition_code": context["card"].edition_code,
            "owner_user_id": listing.owner_user_id,
            "total_slots": listing.total_slots,
            "available_slots": listing.available_slots,
            "duration_days": listing.duration_days,
            "loan_fee_credits": self._normalize_amount(listing.loan_fee_credits),
            "currency": listing.currency,
            "status": listing.status,
            "is_negotiable": listing.is_negotiable,
            "asset_origin": context["asset_origin"],
            "is_regen_newgen": context["is_regen_newgen"],
            "is_creator_linked": context["is_creator_linked"],
            "usage_restrictions_json": dict(listing.usage_restrictions_json or {}),
            "borrower_rights_json": dict(listing.borrower_rights_json or {}),
            "lender_restrictions_json": dict(listing.lender_restrictions_json or {}),
            "terms_json": dict(listing.terms_json or {}),
            "created_at": listing.created_at,
            "expires_at": listing.expires_at,
        }

    def _loan_negotiation_payload(self, negotiation: CardLoanNegotiation) -> dict[str, Any]:
        return {
            "negotiation_id": negotiation.id,
            "listing_id": negotiation.listing_id,
            "player_card_id": negotiation.player_card_id,
            "owner_user_id": negotiation.owner_user_id,
            "borrower_user_id": negotiation.borrower_user_id,
            "proposer_user_id": negotiation.proposer_user_id,
            "counterparty_user_id": negotiation.counterparty_user_id,
            "proposed_duration_days": negotiation.proposed_duration_days,
            "proposed_loan_fee_credits": self._normalize_amount(negotiation.proposed_loan_fee_credits),
            "status": negotiation.status,
            "note": negotiation.note,
            "requested_terms_json": dict(negotiation.requested_terms_json or {}),
            "created_at": negotiation.created_at,
            "updated_at": negotiation.updated_at,
            "responded_at": negotiation.responded_at,
            "expires_at": negotiation.expires_at,
        }

    def _loan_contract_payload(self, contract: CardLoanContract, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "loan_contract_id": contract.id,
            "listing_id": contract.listing_id,
            "accepted_negotiation_id": contract.accepted_negotiation_id,
            "player_card_id": context["card"].id,
            "player_id": context["player"].id,
            "player_name": context["player"].full_name,
            "club_name": context["club_name"],
            "position": context["player"].normalized_position or context["player"].position,
            "average_rating": float(context["average_rating"]) if context["average_rating"] is not None else None,
            "avatar": context["avatar"],
            "tier_code": context["tier"].code,
            "tier_name": context["tier"].name,
            "rarity_rank": context["tier"].rarity_rank,
            "edition_code": context["card"].edition_code,
            "owner_user_id": contract.owner_user_id,
            "borrower_user_id": contract.borrower_user_id,
            "status": contract.status,
            "asset_origin": context["asset_origin"],
            "is_regen_newgen": context["is_regen_newgen"],
            "is_creator_linked": context["is_creator_linked"],
            "currency": contract.currency,
            "loan_duration_days": contract.loan_duration_days,
            "requested_loan_fee_credits": self._normalize_amount(contract.requested_loan_fee_credits),
            "effective_loan_fee_credits": self._normalize_amount(contract.loan_fee_credits),
            "platform_fee_credits": self._normalize_amount(contract.platform_fee_credits),
            "lender_net_credits": self._normalize_amount(contract.lender_net_credits),
            "platform_fee_bps": contract.platform_fee_bps,
            "fee_floor_applied": contract.fee_floor_applied,
            "accepted_at": contract.accepted_at,
            "settled_at": contract.settled_at,
            "borrowed_at": contract.borrowed_at,
            "due_at": contract.due_at,
            "returned_at": contract.returned_at,
            "settlement_reference": contract.settlement_reference,
            "accepted_terms_json": dict(contract.accepted_terms_json or {}),
            "borrower_rights_json": dict(contract.borrower_rights_json or {}),
            "lender_rights_json": dict(contract.lender_rights_json or {}),
            "lender_restrictions_json": dict(contract.lender_restrictions_json or {}),
            "usage_snapshot_json": dict(contract.usage_snapshot_json or {}),
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
        }

    def _resolved_borrower_rights(self, listing: CardLoanListing, duration_days: int) -> dict[str, Any]:
        rights = {
            "can_use_in_squad": True,
            "can_enter_competitions": True,
            "can_sell": False,
            "can_swap": False,
            "can_sub_loan": False,
            "duration_days": duration_days,
        }
        rights.update(dict(listing.borrower_rights_json or {}))
        return rights

    @staticmethod
    def _default_lender_rights() -> dict[str, Any]:
        return {
            "retains_title": True,
            "earns_settlement_share": True,
            "can_trigger_expiry_return": True,
            "can_revoke_after_expiry": True,
        }

    def _resolved_lender_restrictions(self, listing: CardLoanListing) -> dict[str, Any]:
        restrictions = {
            "sale_blocked_while_active": True,
            "swap_blocked_while_active": True,
            "secondary_loan_blocked_while_active": True,
            "permanent_transfer_blocked_while_active": True,
        }
        restrictions.update(dict(listing.lender_restrictions_json or {}))
        return restrictions

    def _ensure_loan_listing_available(self, listing: CardLoanListing) -> None:
        if listing.status != "open":
            raise PlayerCardValidationError("Loan listing is not open.")
        if listing.available_slots <= 0:
            raise PlayerCardValidationError("Loan listing has no remaining availability.")
        if self._is_expired(listing.expires_at):
            raise PlayerCardValidationError("Loan listing has expired.")

    def create_loan_listing(
        self,
        *,
        actor: User,
        player_card_id: str,
        total_slots: int,
        duration_days: int,
        loan_fee_credits: Decimal,
        is_negotiable: bool = False,
        usage_restrictions_json: dict[str, Any] | None = None,
        borrower_rights_json: dict[str, Any] | None = None,
        lender_restrictions_json: dict[str, Any] | None = None,
        terms_json: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        if total_slots <= 0:
            raise PlayerCardValidationError("Loan slot count must be positive.")
        if duration_days <= 0 or duration_days > MAX_LOAN_DURATION_DAYS:
            raise PlayerCardValidationError(f"Loan duration must be between 1 and {MAX_LOAN_DURATION_DAYS} days.")
        if loan_fee_credits < Decimal("0"):
            raise PlayerCardValidationError("Loan fee cannot be negative.")

        context = self._get_card_context(player_card_id)
        holding = self._get_holding(actor.id, player_card_id)
        if self._available_holding_quantity(holding) < total_slots:
            raise PlayerCardValidationError("Not enough unreserved card quantity is available to list for loan.")

        holding.quantity_reserved += total_slots
        listing = CardLoanListing(
            player_card_id=player_card_id,
            owner_user_id=actor.id,
            total_slots=total_slots,
            available_slots=total_slots,
            duration_days=duration_days,
            loan_fee_credits=self._normalize_amount(loan_fee_credits),
            currency=LedgerUnit.CREDIT.value,
            status="open",
            is_negotiable=is_negotiable,
            expires_at=expires_at,
            usage_restrictions_json=usage_restrictions_json or {},
            borrower_rights_json=borrower_rights_json or {},
            lender_restrictions_json=lender_restrictions_json or {},
            terms_json=terms_json or {},
            metadata_json={"source": "marketplace_v2"},
        )
        self.session.add(listing)
        self._audit(listing_type="loan", action="listing_created", actor_user_id=actor.id, player_card_id=player_card_id, listing_id=listing.id, status_to="open")
        self.session.flush()
        return self._loan_listing_payload(listing, context)

    def cancel_loan_listing(self, *, actor: User, listing_id: str) -> dict[str, Any]:
        listing = self._get_loan_listing(listing_id)
        if listing.owner_user_id != actor.id:
            raise PlayerCardPermissionError("Only the listing owner can cancel this loan listing.")
        if listing.status != "open":
            raise PlayerCardValidationError("Only open loan listings can be cancelled.")
        holding = self._get_holding(actor.id, listing.player_card_id)
        holding.quantity_reserved = max(holding.quantity_reserved - max(listing.available_slots, 0), 0)
        previous_status = listing.status
        listing.available_slots = 0
        listing.status = "cancelled"
        self._audit(listing_type="loan", action="listing_cancelled", actor_user_id=actor.id, player_card_id=listing.player_card_id, listing_id=listing.id, status_from=previous_status, status_to=listing.status)
        self.session.flush()
        return self._loan_listing_payload(listing, self._get_card_context(listing.player_card_id))

    def create_loan_negotiation(
        self,
        *,
        actor: User,
        listing_id: str,
        proposed_duration_days: int,
        proposed_loan_fee_credits: Decimal,
        requested_terms_json: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        listing = self._get_loan_listing(listing_id)
        self._ensure_loan_listing_available(listing)
        if actor.id == listing.owner_user_id:
            raise PlayerCardValidationError("You cannot negotiate against your own loan listing.")
        if proposed_duration_days <= 0 or proposed_duration_days > MAX_LOAN_DURATION_DAYS:
            raise PlayerCardValidationError(f"Loan duration must be between 1 and {MAX_LOAN_DURATION_DAYS} days.")
        if proposed_loan_fee_credits < Decimal("0"):
            raise PlayerCardValidationError("Loan fee cannot be negative.")
        if not listing.is_negotiable and (
            proposed_duration_days != listing.duration_days or self._normalize_amount(proposed_loan_fee_credits) != self._normalize_amount(listing.loan_fee_credits)
        ):
            raise PlayerCardValidationError("This loan listing is not negotiable.")

        self._ensure_borrower_has_no_player_version(actor.id, self._get_card_context(listing.player_card_id)["player"].id)
        negotiation = CardLoanNegotiation(
            listing_id=listing.id,
            player_card_id=listing.player_card_id,
            owner_user_id=listing.owner_user_id,
            borrower_user_id=actor.id,
            proposer_user_id=actor.id,
            counterparty_user_id=listing.owner_user_id,
            proposed_duration_days=proposed_duration_days,
            proposed_loan_fee_credits=self._normalize_amount(proposed_loan_fee_credits),
            status="pending",
            note=note,
            requested_terms_json=requested_terms_json or {},
            metadata_json={},
        )
        self.session.add(negotiation)
        self._audit(listing_type="loan", action="negotiation_created", actor_user_id=actor.id, player_card_id=listing.player_card_id, listing_id=listing.id, negotiation_id=negotiation.id, status_to="pending")
        self.session.flush()
        return self._loan_negotiation_payload(negotiation)

    def counter_loan_negotiation(
        self,
        *,
        actor: User,
        negotiation_id: str,
        proposed_duration_days: int,
        proposed_loan_fee_credits: Decimal,
        requested_terms_json: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        negotiation = self._get_loan_negotiation(negotiation_id)
        if negotiation.status != "pending":
            raise PlayerCardValidationError("Only pending loan negotiations can be countered.")
        if actor.id != negotiation.counterparty_user_id:
            raise PlayerCardPermissionError("Only the current counterparty can counter this negotiation.")
        listing = self._get_loan_listing(negotiation.listing_id)
        self._ensure_loan_listing_available(listing)

        negotiation.status = "countered"
        negotiation.responded_at = datetime.now(UTC)
        counter = CardLoanNegotiation(
            listing_id=negotiation.listing_id,
            player_card_id=negotiation.player_card_id,
            owner_user_id=negotiation.owner_user_id,
            borrower_user_id=negotiation.borrower_user_id,
            proposer_user_id=actor.id,
            counterparty_user_id=negotiation.proposer_user_id,
            proposed_duration_days=proposed_duration_days,
            proposed_loan_fee_credits=self._normalize_amount(proposed_loan_fee_credits),
            status="pending",
            note=note,
            supersedes_negotiation_id=negotiation.id,
            requested_terms_json=requested_terms_json or {},
            metadata_json={},
        )
        self.session.add(counter)
        self._audit(listing_type="loan", action="negotiation_countered", actor_user_id=actor.id, player_card_id=negotiation.player_card_id, listing_id=negotiation.listing_id, negotiation_id=counter.id, status_from="countered", status_to="pending")
        self.session.flush()
        return self._loan_negotiation_payload(counter)

    def accept_loan_negotiation(self, *, actor: User, negotiation_id: str) -> dict[str, Any]:
        negotiation = self._get_loan_negotiation(negotiation_id)
        if negotiation.status != "pending":
            raise PlayerCardValidationError("Only pending loan negotiations can be accepted.")
        if actor.id != negotiation.counterparty_user_id:
            raise PlayerCardPermissionError("Only the current counterparty can accept this loan negotiation.")
        listing = self._get_loan_listing(negotiation.listing_id)
        self._ensure_loan_listing_available(listing)
        context = self._get_card_context(listing.player_card_id)
        economics = self._loan_economics(context, negotiation.proposed_loan_fee_credits)
        accepted_at = datetime.now(UTC)

        negotiation.status = "accepted"
        negotiation.responded_at = accepted_at
        listing.available_slots = max(listing.available_slots - 1, 0)
        contract = CardLoanContract(
            listing_id=listing.id,
            accepted_negotiation_id=negotiation.id,
            player_card_id=listing.player_card_id,
            owner_user_id=listing.owner_user_id,
            borrower_user_id=negotiation.borrower_user_id,
            loan_fee_credits=economics["effective_fee_credits"],
            requested_loan_fee_credits=economics["requested_fee_credits"],
            platform_fee_credits=economics["platform_fee_credits"],
            lender_net_credits=economics["lender_net_credits"],
            platform_fee_bps=economics["platform_fee_bps"],
            fee_floor_applied=economics["fee_floor_applied"],
            loan_duration_days=negotiation.proposed_duration_days,
            currency=LedgerUnit.CREDIT.value,
            status="accepted_pending_settlement",
            accepted_at=accepted_at,
            borrowed_at=accepted_at,
            due_at=accepted_at + timedelta(days=negotiation.proposed_duration_days),
            accepted_terms_json={"requested_terms": dict(negotiation.requested_terms_json or {}), "listing_terms": dict(listing.terms_json or {})},
            borrower_rights_json=self._resolved_borrower_rights(listing, negotiation.proposed_duration_days),
            lender_rights_json=self._default_lender_rights(),
            lender_restrictions_json=self._resolved_lender_restrictions(listing),
            usage_snapshot_json={"usage_restrictions": dict(listing.usage_restrictions_json or {})},
            metadata_json={"asset_origin": context["asset_origin"]},
        )
        self.session.add(contract)
        self._audit(listing_type="loan", action="negotiation_accepted", actor_user_id=actor.id, player_card_id=listing.player_card_id, listing_id=listing.id, negotiation_id=negotiation.id, loan_contract_id=contract.id, status_from="pending", status_to="accepted_pending_settlement")
        self.session.flush()
        return self._loan_contract_payload(contract, context)

    def settle_loan_contract(self, *, actor: User, contract_id: str) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        contract = self._get_loan_contract(contract_id)
        if contract.status != "accepted_pending_settlement":
            raise PlayerCardValidationError("Only accepted loan contracts can be settled.")
        if actor.id != contract.borrower_user_id:
            raise PlayerCardPermissionError("Only the borrower can settle this loan contract.")
        borrower = self._get_user(contract.borrower_user_id)
        lender = self._get_user(contract.owner_user_id)
        settlement_reference = f"player-card-loan:{contract.id}:{generate_uuid()}"
        effective_fee = self._normalize_amount(contract.loan_fee_credits)
        platform_fee = self._normalize_amount(contract.platform_fee_credits)
        lender_net = self._normalize_amount(contract.lender_net_credits)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=self.wallet_service.get_user_account(self.session, borrower, LedgerUnit.CREDIT), amount=-effective_fee, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                LedgerPosting(account=self.wallet_service.get_user_account(self.session, lender, LedgerUnit.CREDIT), amount=lender_net, source_tag=LedgerSourceTag.PLAYER_CARD_SALE),
                LedgerPosting(account=self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT), amount=platform_fee, source_tag=LedgerSourceTag.TRADING_FEE_BURN),
            ],
            reason=self.wallet_service.trade_settlement_reason,
            reference=settlement_reference,
            description="Player card loan settlement",
            external_reference=settlement_reference,
            actor=actor,
        )
        now = datetime.now(UTC)
        contract.status = "active"
        contract.settlement_reference = settlement_reference
        contract.settled_at = now
        contract.borrowed_at = now
        contract.due_at = now + timedelta(days=contract.loan_duration_days)
        self._audit(listing_type="loan", action="contract_settled", actor_user_id=actor.id, player_card_id=contract.player_card_id, listing_id=contract.listing_id, loan_contract_id=contract.id, status_from="accepted_pending_settlement", status_to="active")
        self.session.flush()
        return self._loan_contract_payload(contract, self._get_card_context(contract.player_card_id))

    def return_loan_contract(self, *, actor: User, contract_id: str) -> dict[str, Any]:
        contract = self._get_loan_contract(contract_id)
        if contract.status != "active":
            raise PlayerCardValidationError("Only active loan contracts can be returned.")
        if actor.id not in {contract.owner_user_id, contract.borrower_user_id} and actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Only the lender, borrower, or an admin can return this loan contract.")
        listing = self._get_loan_listing(contract.listing_id)
        holding = self._get_holding(contract.owner_user_id, contract.player_card_id)
        now = datetime.now(UTC)
        previous_status = contract.status
        due_at = self._coerce_utc(contract.due_at) if contract.due_at is not None else None
        contract.status = "expired" if due_at is not None and due_at <= now else "returned"
        contract.returned_at = now
        if listing.status == "open" and not self._is_expired(listing.expires_at):
            listing.available_slots = min(listing.total_slots, listing.available_slots + 1)
        else:
            holding.quantity_reserved = max(holding.quantity_reserved - 1, 0)
        self._audit(listing_type="loan", action="contract_returned", actor_user_id=actor.id, player_card_id=contract.player_card_id, listing_id=contract.listing_id, loan_contract_id=contract.id, status_from=previous_status, status_to=contract.status)
        self.session.flush()
        return self._loan_contract_payload(contract, self._get_card_context(contract.player_card_id))

    def list_loan_contracts(self, *, actor: User, role: str | None = None, status: str | None = None) -> dict[str, Any]:
        stmt = select(CardLoanContract)
        normalized_role = None if role is None else role.strip().lower()
        if normalized_role in {None, "all"}:
            stmt = stmt.where(or_(CardLoanContract.borrower_user_id == actor.id, CardLoanContract.owner_user_id == actor.id))
        elif normalized_role == "borrower":
            stmt = stmt.where(CardLoanContract.borrower_user_id == actor.id)
        elif normalized_role == "lender":
            stmt = stmt.where(CardLoanContract.owner_user_id == actor.id)
        else:
            raise PlayerCardValidationError("Role must be one of borrower, lender, or all.")
        if status:
            stmt = stmt.where(CardLoanContract.status == status)
        contracts = list(self.session.scalars(stmt.order_by(CardLoanContract.created_at.desc())).all())
        return {
            "total": len(contracts),
            "items": [self._loan_contract_payload(contract, self._get_card_context(contract.player_card_id)) for contract in contracts],
        }

    def validate_contract_usage(
        self,
        *,
        borrower_user_id: str,
        player_card_id: str,
        competition_id: str | None = None,
        squad_scope: str | None = None,
    ) -> bool:
        contract = self.session.scalar(
            select(CardLoanContract).where(
                CardLoanContract.borrower_user_id == borrower_user_id,
                CardLoanContract.player_card_id == player_card_id,
                CardLoanContract.status == "active",
            )
        )
        due_at = self._coerce_utc(contract.due_at) if contract is not None and contract.due_at is not None else None
        if contract is None or (due_at is not None and due_at <= datetime.now(UTC)):
            return False
        restrictions = (contract.usage_snapshot_json or {}).get("usage_restrictions") or {}
        self._ensure_usage_allowed(restrictions, competition_id=competition_id, squad_scope=squad_scope)
        return True

    def _swap_listing_payload(self, listing: CardSwapListing, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "listing_id": listing.id,
            "player_card_id": context["card"].id,
            "player_id": context["player"].id,
            "player_name": context["player"].full_name,
            "club_name": context["club_name"],
            "position": context["player"].normalized_position or context["player"].position,
            "average_rating": float(context["average_rating"]) if context["average_rating"] is not None else None,
            "avatar": context["avatar"],
            "tier_code": context["tier"].code,
            "tier_name": context["tier"].name,
            "rarity_rank": context["tier"].rarity_rank,
            "edition_code": context["card"].edition_code,
            "owner_user_id": listing.owner_user_id,
            "status": listing.status,
            "is_negotiable": listing.is_negotiable,
            "asset_origin": context["asset_origin"],
            "is_regen_newgen": context["is_regen_newgen"],
            "is_creator_linked": context["is_creator_linked"],
            "requested_player_card_id": listing.requested_player_card_id,
            "requested_player_id": listing.requested_player_id,
            "desired_filters_json": dict(listing.desired_filters_json or {}),
            "terms_json": dict(listing.terms_json or {}),
            "created_at": listing.created_at,
            "expires_at": listing.expires_at,
        }

    def _swap_execution_payload(self, execution: CardSwapExecution) -> dict[str, Any]:
        return {
            "swap_execution_id": execution.id,
            "listing_id": execution.listing_id,
            "owner_user_id": execution.owner_user_id,
            "counterparty_user_id": execution.counterparty_user_id,
            "owner_player_card_id": execution.owner_player_card_id,
            "counterparty_player_card_id": execution.counterparty_player_card_id,
            "status": execution.status,
            "settled_at": execution.settled_at,
            "snapshot_json": dict(execution.snapshot_json or {}),
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
        }

    def _validate_swap_desired_filters(self, desired_filters: dict[str, Any], context: dict[str, Any]) -> None:
        if not desired_filters:
            return
        desired_player_name = desired_filters.get("player_name")
        if desired_player_name and desired_player_name.strip().lower() not in context["player"].full_name.lower():
            raise PlayerCardValidationError("Counterparty card does not match the requested player name.")
        desired_club = desired_filters.get("club")
        if desired_club and desired_club.strip().lower() not in (context["club_name"] or "").lower():
            raise PlayerCardValidationError("Counterparty card does not match the requested club.")
        desired_position = desired_filters.get("position")
        actual_position = (context["player"].normalized_position or context["player"].position or "").lower()
        if desired_position and desired_position.strip().lower() != actual_position:
            raise PlayerCardValidationError("Counterparty card does not match the requested position.")
        desired_tier = desired_filters.get("tier_code")
        if desired_tier and desired_tier.strip().lower() != context["tier"].code.lower():
            raise PlayerCardValidationError("Counterparty card does not match the requested tier.")

    def create_swap_listing(
        self,
        *,
        actor: User,
        player_card_id: str,
        requested_player_card_id: str | None = None,
        requested_player_id: str | None = None,
        desired_filters_json: dict[str, Any] | None = None,
        terms_json: dict[str, Any] | None = None,
        is_negotiable: bool = False,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        context = self._get_card_context(player_card_id)
        holding = self._get_holding(actor.id, player_card_id)
        if self._available_holding_quantity(holding) < 1:
            raise PlayerCardValidationError("No unreserved card quantity is available to list for swap.")
        if requested_player_card_id and requested_player_id:
            raise PlayerCardValidationError("Provide either a requested player card id or requested player id, not both.")

        holding.quantity_reserved += 1
        listing = CardSwapListing(
            player_card_id=player_card_id,
            owner_user_id=actor.id,
            requested_player_card_id=requested_player_card_id,
            requested_player_id=requested_player_id,
            status="open",
            is_negotiable=is_negotiable,
            expires_at=expires_at,
            desired_filters_json=desired_filters_json or {},
            terms_json=terms_json or {},
            metadata_json={"source": "marketplace_v2"},
        )
        self.session.add(listing)
        self._audit(listing_type="swap", action="listing_created", actor_user_id=actor.id, player_card_id=player_card_id, listing_id=listing.id, status_to="open")
        self.session.flush()
        return self._swap_listing_payload(listing, context)

    def cancel_swap_listing(self, *, actor: User, listing_id: str) -> dict[str, Any]:
        listing = self._get_swap_listing(listing_id)
        if listing.owner_user_id != actor.id:
            raise PlayerCardPermissionError("Only the listing owner can cancel this swap listing.")
        if listing.status != "open":
            raise PlayerCardValidationError("Only open swap listings can be cancelled.")
        holding = self._get_holding(actor.id, listing.player_card_id)
        holding.quantity_reserved = max(holding.quantity_reserved - 1, 0)
        previous_status = listing.status
        listing.status = "cancelled"
        self._audit(listing_type="swap", action="listing_cancelled", actor_user_id=actor.id, player_card_id=listing.player_card_id, listing_id=listing.id, status_from=previous_status, status_to=listing.status)
        self.session.flush()
        return self._swap_listing_payload(listing, self._get_card_context(listing.player_card_id))

    def execute_swap_listing(
        self,
        *,
        actor: User,
        listing_id: str,
        counterparty_player_card_id: str,
    ) -> dict[str, Any]:
        self._ensure_market_actor(actor)
        listing = self._get_swap_listing(listing_id)
        if listing.status != "open" or self._is_expired(listing.expires_at):
            raise PlayerCardValidationError("Swap listing is not available.")
        if listing.owner_user_id == actor.id:
            raise PlayerCardValidationError("You cannot accept your own swap listing.")

        requested_context = self._get_card_context(counterparty_player_card_id)
        if listing.requested_player_card_id and listing.requested_player_card_id != counterparty_player_card_id:
            raise PlayerCardValidationError("This swap listing requires a specific player card.")
        if listing.requested_player_id and listing.requested_player_id != requested_context["player"].id:
            raise PlayerCardValidationError("This swap listing requires a different player.")
        self._validate_swap_desired_filters(listing.desired_filters_json or {}, requested_context)

        owner_holding = self._get_holding(listing.owner_user_id, listing.player_card_id)
        counterparty_holding = self._get_holding(actor.id, counterparty_player_card_id)
        if self._available_holding_quantity(counterparty_holding) < 1:
            raise PlayerCardValidationError("Counterparty card is not available for swap.")

        owner_holding.quantity_reserved = max(owner_holding.quantity_reserved - 1, 0)
        owner_holding.quantity_total = max(owner_holding.quantity_total - 1, 0)
        if owner_holding.quantity_total == 0:
            self.session.delete(owner_holding)
        counterparty_holding.quantity_total = max(counterparty_holding.quantity_total - 1, 0)
        if counterparty_holding.quantity_total == 0:
            self.session.delete(counterparty_holding)

        owner_received = self._get_or_create_holding(listing.owner_user_id, counterparty_player_card_id)
        owner_received.quantity_total += 1
        owner_received.last_acquired_at = datetime.now(UTC)
        actor_received = self._get_or_create_holding(actor.id, listing.player_card_id)
        actor_received.quantity_total += 1
        actor_received.last_acquired_at = datetime.now(UTC)

        previous_status = listing.status
        listing.status = "executed"
        execution = CardSwapExecution(
            listing_id=listing.id,
            owner_user_id=listing.owner_user_id,
            counterparty_user_id=actor.id,
            owner_player_card_id=listing.player_card_id,
            counterparty_player_card_id=counterparty_player_card_id,
            status="executed",
            settled_at=datetime.now(UTC),
            snapshot_json={"desired_filters_json": dict(listing.desired_filters_json or {})},
            metadata_json={"source": "marketplace_v2"},
        )
        self.session.add(execution)
        self._audit(listing_type="swap", action="swap_executed", actor_user_id=actor.id, player_card_id=listing.player_card_id, listing_id=listing.id, swap_execution_id=execution.id, status_from=previous_status, status_to=listing.status)
        self.session.flush()
        return self._swap_execution_payload(execution)
