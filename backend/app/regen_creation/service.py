from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from hashlib import sha256
from random import Random
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.event_backbone import defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.ingestion.models import Country, Player, PlayerVerification
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardOwnerHistory,
    PlayerCardTier,
)
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.regen import (
    RegenGenerationEvent,
    RegenLegacyRecord,
    RegenLineageProfile,
    RegenOnboardingFlag,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenVisualProfile,
)
from app.models.regen_creation_order import (
    RegenCreationOrder,
    RegenCreationOrderStatus,
    RegenCreationPaymentMethod,
    RegenCreationRequestType,
)
from app.models.regen_ecosystem import CareerEvent, RegenBloodlineLink
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.regen_universe.models import RegenAchievement, RegenStoryEvent
from app.regen_creation.schemas import (
    RegenCreationGeneratedPlayerView,
    RegenCreationOrderListView,
    RegenCreationOrderView,
    RegenCreationParentPlayerView,
    RegenCreationPricingView,
    RegenCreationWalletReservationView,
    RequestSonCountryOptionView,
    RequestSonPreviewRequest,
    RequestSonPreviewView,
    RequestSonPositionOptionView,
    RequestSonWalletAvailabilityView,
    RequestSonCreateRequest,
    RequestSonOptionsView,
)
from app.services.regen_service import OwnerSonContext, OwnerSonRequest, RegenClubContext, RegenGenerationEngine
from app.services.regen_portrait_service import RegenPortraitService
from app.wallets.service import (
    InsufficientBalanceError,
    LedgerPosting,
    WalletService,
    WALLET_RESERVATION_METADATA_KEY,
)

AMOUNT_QUANTUM = Decimal("0.0001")
REQUEST_SON_WALLET_RESERVATION_KIND = "regen_creation_order"
REQUEST_SON_WALLET_RESERVATION_LABEL = "Build-a-Son creation reservation"
REQUEST_SON_PARENT_POSITIONS = {"GK", "CB", "RB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"}
REQUEST_SON_PARENT_POSITION_ALIASES = {
    "CDM": "DM",
    "CAM": "AM",
    "LCB": "CB",
    "RCB": "CB",
    "LWB": "LB",
    "RWB": "RB",
    "LM": "LW",
    "RM": "RW",
    "CF": "ST",
}
REQUEST_SON_POSITION_OPTIONS = (
    ("GK", "Goalkeeper", (), "goalkeeper"),
    ("CB", "Centre Back", ("LCB", "RCB"), "defender"),
    ("RB", "Right Back", ("RWB",), "defender"),
    ("LB", "Left Back", ("LWB",), "defender"),
    ("DM", "Defensive Midfielder", ("CDM",), "midfielder"),
    ("CM", "Central Midfielder", (), "midfielder"),
    ("AM", "Attacking Midfielder", ("CAM",), "midfielder"),
    ("RW", "Right Winger", ("RM",), "forward"),
    ("LW", "Left Winger", ("LM",), "forward"),
    ("ST", "Striker", ("CF",), "forward"),
)


class RegenCreationError(ValueError):
    pass


class RegenCreationNotFoundError(RegenCreationError):
    pass


class RegenCreationValidationError(RegenCreationError):
    pass


class RegenCreationPermissionError(RegenCreationError):
    pass


class RegenCreationPaymentError(RegenCreationError):
    def __init__(self, message: str, *, terminal: bool = False) -> None:
        super().__init__(message)
        self.terminal = terminal


class RegenCreationConflictError(RegenCreationError):
    pass


@dataclass(slots=True)
class RegenCreationService:
    session: Session
    settings: Settings | None = None
    wallet_service: WalletService | None = None
    event_publisher: EventPublisher | None = None
    engine: RegenGenerationEngine | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.event_publisher = (
            self.event_publisher or getattr(self.wallet_service, "event_publisher", None) or InMemoryEventPublisher()
        )
        self.wallet_service = self.wallet_service or WalletService(event_publisher=self.event_publisher)
        self.engine = self.engine or RegenGenerationEngine(self.settings)

    def request_son_options(self, actor: User) -> RequestSonOptionsView:
        club = self._resolve_actor_club(actor)
        pricing = self._pricing_view()
        eligible: list[RegenCreationParentPlayerView] = []
        for player, country in self._eligible_parent_rows(club.id):
            parent = self._parent_player_view(player=player, club=club, country=country)
            if self._parent_canonical_truth_gap(parent) is None:
                eligible.append(parent)
        return RequestSonOptionsView(
            club_id=club.id,
            club_name=club.club_name,
            currency="COIN",
            pricing=pricing,
            nationality_options=self._request_son_country_options(),
            position_options=self._request_son_position_options(),
            default_country_code=self._default_request_son_country_code(),
            default_position="AM",
            eligible_parents=eligible,
        )

    def preview_request_son(
        self,
        *,
        actor: User,
        payload: RequestSonPreviewRequest,
    ) -> RequestSonPreviewView:
        club = self._resolve_actor_club(actor)
        parent_player = self._resolve_parent_player(
            club=club,
            actor=actor,
            parent_player_id=payload.parent_player_id,
        )
        return self._request_son_preview(actor=actor, club=club, parent_player=parent_player, payload=payload)

    def create_request_son_order(
        self,
        *,
        actor: User,
        payload: RequestSonCreateRequest,
    ) -> RegenCreationOrderView:
        if payload.payment_method != RegenCreationPaymentMethod.WALLET.value:
            raise RegenCreationValidationError("request_son_requires_wallet_payment")
        club = self._resolve_actor_club(actor)
        parent_player = self._resolve_parent_player(
            club=club,
            actor=actor,
            parent_player_id=payload.parent_player_id,
        )
        self._enforce_request_limit(actor)
        preview = self._request_son_preview(actor=actor, club=club, parent_player=parent_player, payload=payload)
        if preview.blocked_reason:
            raise RegenCreationValidationError(preview.blocked_reason)
        if payload.payment_method == "wallet" and preview.wallet.blocked_reason:
            raise RegenCreationValidationError(preview.wallet.blocked_reason)

        order = RegenCreationOrder(
            user_id=actor.id,
            club_id=club.id,
            request_type=RegenCreationRequestType.SON,
            parent_player_id=parent_player.id,
            requested_name=payload.requested_name,
            requested_country_code=payload.requested_country_code,
            requested_position=payload.requested_position,
            amount_coin=self._request_son_price(payload),
            amount_minor=None,
            currency="COIN",
            payment_method=RegenCreationPaymentMethod.WALLET,
            payment_provider="wallet",
            status=RegenCreationOrderStatus.PENDING_PAYMENT,
            metadata_json={
                "request_source": "request_son",
                "parent_player_name": parent_player.full_name,
                "club_name": club.club_name,
                "selected_traits": preview.selected_traits,
                "request_son_preview": preview.model_dump(mode="json"),
                "preview_seed": self._preview_seed(
                    actor=actor,
                    club=club,
                    parent_player=parent_player,
                    payload=payload,
                    selected_traits=preview.selected_traits,
                ),
            },
        )
        self.session.add(order)
        self.session.flush()

        self._reserve_wallet_for_order(order=order, actor=actor)
        order.payment_provider = "wallet"

        self.session.flush()
        self._stage_order_event(
            "regen.creation_order.created",
            order=order,
            actor=actor,
            previous_status=None,
        )
        return self._order_view(order)

    def list_orders(self, *, actor: User, limit: int = 20) -> RegenCreationOrderListView:
        resolved_limit = max(1, min(int(limit), 100))
        orders = self.session.scalars(
            select(RegenCreationOrder)
            .where(RegenCreationOrder.user_id == actor.id)
            .order_by(RegenCreationOrder.created_at.desc(), RegenCreationOrder.id.desc())
            .limit(resolved_limit)
        ).all()
        return RegenCreationOrderListView(items=[self._order_view(order) for order in orders])

    def get_order(self, *, actor: User, order_id: str) -> RegenCreationOrderView:
        return self._order_view(self._owned_order(actor=actor, order_id=order_id))

    def pay_with_wallet(self, *, actor: User, order_id: str) -> RegenCreationOrderView:
        order = self._owned_order(actor=actor, order_id=order_id)
        if order.payment_method != RegenCreationPaymentMethod.WALLET:
            raise RegenCreationValidationError("This order is not payable with wallet.")
        if order.status == RegenCreationOrderStatus.GENERATED:
            return self._order_view(order)
        if order.status == RegenCreationOrderStatus.PENDING_PAYMENT:
            previous_status = order.status.value
            self._settle_wallet_for_order(order=order, actor=actor)
            order.status = RegenCreationOrderStatus.PAID
            order.payment_provider = "wallet"
            order.payment_reference = order.payment_reference or f"regen-wallet-{order.id}"
            order.paid_at = order.paid_at or utcnow()
            self.session.flush()
            self._stage_order_event(
                "regen.creation_order.paid",
                order=order,
                actor=actor,
                previous_status=previous_status,
            )
        return self._generate_order(order=order, actor=actor)

    def generate_after_payment(self, *, actor: User, order_id: str) -> RegenCreationOrderView:
        order = self._owned_order(actor=actor, order_id=order_id)
        if order.status == RegenCreationOrderStatus.GENERATED:
            return self._order_view(order)
        if order.payment_method != RegenCreationPaymentMethod.WALLET:
            raise RegenCreationValidationError("request_son_requires_wallet_payment")
        if order.status != RegenCreationOrderStatus.PAID:
            raise RegenCreationPaymentError("Payment must be settled before generation.")
        return self._generate_order(order=order, actor=actor)

    def cancel_order(self, *, actor: User, order_id: str) -> RegenCreationOrderView:
        order = self._owned_order(actor=actor, order_id=order_id)
        if order.status == RegenCreationOrderStatus.CANCELLED:
            return self._order_view(order)
        if order.payment_method != RegenCreationPaymentMethod.WALLET:
            raise RegenCreationValidationError("Only pending wallet creation orders can be cancelled.")
        if order.status != RegenCreationOrderStatus.PENDING_PAYMENT:
            raise RegenCreationPaymentError("Only pending wallet creation orders can be cancelled.")
        previous_status = order.status.value
        self._release_wallet_for_order(order=order, actor=actor)
        order.status = RegenCreationOrderStatus.CANCELLED
        order.payment_provider = "wallet"
        self.session.flush()
        self._stage_order_event(
            "regen.creation_order.cancelled",
            order=order,
            actor=actor,
            previous_status=previous_status,
        )
        return self._order_view(order)

    def _resolve_actor_club(self, actor: User) -> ClubProfile:
        club = self.session.scalar(
            select(ClubProfile)
            .where(ClubProfile.owner_user_id == actor.id)
            .order_by(ClubProfile.created_at.desc(), ClubProfile.id.desc())
        )
        if club is None:
            raise RegenCreationValidationError("No managed club was found for this user.")
        return club

    def _eligible_parent_rows(self, club_id: str) -> list[tuple[Player, Country | None]]:
        return list(
            self.session.execute(
                select(Player, Country)
                .outerjoin(Country, Country.id == Player.country_id)
                .where(Player.current_club_profile_id == club_id)
                .order_by(Player.full_name.asc(), Player.id.asc())
            ).all()
        )

    def _resolve_parent_player(
        self,
        *,
        club: ClubProfile,
        actor: User,
        parent_player_id: str,
    ) -> Player:
        player = self.session.get(Player, parent_player_id)
        if player is None:
            raise RegenCreationNotFoundError("Selected parent player was not found.")
        if player.current_club_profile_id != club.id:
            raise RegenCreationPermissionError("You can only request a son from a player in your own club.")
        del actor
        return player

    def _request_son_preview(
        self,
        *,
        actor: User,
        club: ClubProfile,
        parent_player: Player,
        payload: RequestSonPreviewRequest | RequestSonCreateRequest,
    ) -> RequestSonPreviewView:
        assert self.wallet_service is not None
        if payload.payment_method != RegenCreationPaymentMethod.WALLET.value:
            raise RegenCreationValidationError("request_son_requires_wallet_payment")
        parent_regen = self._parent_regen_profile(parent_player)
        country = self.session.get(Country, parent_player.country_id) if parent_player.country_id else None
        parent = self._parent_player_view(player=parent_player, club=club, country=country, regen=parent_regen)
        parent_truth_gap = self._parent_canonical_truth_gap(parent)
        if parent_truth_gap is not None:
            raise RegenCreationValidationError(parent_truth_gap)
        selected_traits = self._canonical_selected_traits(
            available_traits=parent.traits,
            selected_traits=payload.selected_traits,
        )
        total_cost = self._request_son_price(payload)
        summary = self.wallet_service.get_wallet_summary(self.session, actor, currency=LedgerUnit.COIN)
        wallet_blocked_reason = None
        if summary.available_balance < total_cost:
            wallet_blocked_reason = "insufficient_wallet_balance"
        blocked_reason = self._request_son_limit_blocked_reason(actor)
        projected = self._project_request_son(
            actor=actor,
            club=club,
            parent_player=parent_player,
            payload=payload,
            selected_traits=selected_traits,
            total_cost=total_cost,
        )
        dna_profile = self._projected_dna_profile(projected)
        projected_generation = parent.generation + 1
        return RequestSonPreviewView(
            club_id=club.id,
            club_name=club.club_name,
            parent=parent,
            selected_traits=selected_traits,
            projected_dna=self._projected_dna_bars(
                current_rating=int(projected.current_gsi),
                position=projected.primary_position,
                dna_profile=dna_profile,
            ),
            projected_dna_profile=dna_profile,
            projected_ovr=int(projected.current_gsi),
            projected_pot=int(projected.potential_range.maximum),
            parent_generation=parent.generation,
            projected_generation=projected_generation,
            generation_label=f"GEN-{projected_generation}",
            total_cost_coin=total_cost,
            wallet=RequestSonWalletAvailabilityView(
                available_balance=self._normalize_amount(summary.available_balance),
                reserved_balance=self._normalize_amount(summary.reserved_balance),
                locked_balance=self._normalize_amount(getattr(summary, "locked_balance", summary.reserved_balance)),
                pending_withdrawal_balance=self._normalize_amount(
                    getattr(summary, "pending_withdrawal_balance", Decimal("0.0000"))
                ),
                lock_reasons=self._wallet_lock_reason_messages(getattr(summary, "lock_reasons", ())),
                total_balance=self._normalize_amount(summary.total_balance),
                currency=summary.currency.value,
                can_pay_with_wallet=summary.available_balance >= total_cost,
                blocked_reason=wallet_blocked_reason,
            ),
            blocked_reason=blocked_reason,
        )

    def _project_request_son(
        self,
        *,
        actor: User,
        club: ClubProfile,
        parent_player: Player,
        payload: RequestSonPreviewRequest | RequestSonCreateRequest,
        selected_traits: list[str],
        total_cost: Decimal,
    ):
        assert self.engine is not None
        assert self.settings is not None
        target_country_code = self._target_country_code_for_request(
            requested_country_code=payload.requested_country_code,
            club=club,
            parent_player=parent_player,
        )
        target_region = club.region_name if (club.country_code or "").upper() == target_country_code else None
        target_city = club.city_name if (club.country_code or "").upper() == target_country_code else None
        owner_context = OwnerSonContext(
            owner_user_id=actor.id,
            club_id=club.id,
            club_country_code=target_country_code,
            club_region_name=target_region,
            club_city_name=target_city,
            lifetime_count=self._owner_son_lifetime_count(actor.id),
            lifetime_cap=self.settings.regen_generation.owner_son_lifetime_cap,
        )
        owner_request = OwnerSonRequest(
            request_id=self._preview_seed(
                actor=actor,
                club=club,
                parent_player=parent_player,
                payload=payload,
                selected_traits=selected_traits,
            ),
            club_id=club.id,
            owner_user_id=actor.id,
            created_at=utcnow(),
            customization=self._payload_customization(payload=payload, selected_traits=selected_traits),
            total_cost_coin=int(total_cost),
            target_club_id=club.id,
        )
        generated = self.engine.generate_academy_intake(
            club_id=club.id,
            season_label=self._season_label(),
            club_context=RegenClubContext(
                country_code=target_country_code,
                region_name=target_region,
                city_name=target_city,
                youth_coaching=62.0,
                training_level=60.0,
                academy_level=62.0,
                academy_investment=60.0,
                first_team_gsi=58.0,
                club_reputation=56.0,
                competition_quality=55.0,
                manager_youth_development=61.0,
                urbanicity="urban" if target_city else None,
            ),
            intake_size=1,
            used_names=self._used_names_for_club(club.id),
            rng=Random(
                self._preview_seed(
                    actor=actor,
                    club=club,
                    parent_player=parent_player,
                    payload=payload,
                    selected_traits=selected_traits,
                )
            ),
            owner_context=owner_context,
            owner_son_request=owner_request,
        )
        return generated.regens[0]

    def _request_son_limit_blocked_reason(self, actor: User) -> str | None:
        assert self.settings is not None
        if self._active_request_son_order_count(actor) >= int(
            self.settings.regen_generation.owner_son_paid_request_limit
        ):
            return "owner_son_paid_request_limit_reached"
        return None

    def _enforce_request_limit(self, actor: User) -> None:
        assert self.settings is not None
        if self._active_request_son_order_count(actor) >= int(
            self.settings.regen_generation.owner_son_paid_request_limit
        ):
            raise RegenCreationConflictError("owner_son_paid_request_limit_reached")

    def _active_request_son_order_count(self, actor: User) -> int:
        active_count = self.session.scalar(
            select(func.count(RegenCreationOrder.id)).where(
                RegenCreationOrder.user_id == actor.id,
                RegenCreationOrder.request_type == RegenCreationRequestType.SON,
                RegenCreationOrder.status.in_(
                    (
                        RegenCreationOrderStatus.PENDING_PAYMENT,
                        RegenCreationOrderStatus.PAID,
                        RegenCreationOrderStatus.GENERATING,
                        RegenCreationOrderStatus.GENERATED,
                    )
                ),
            )
        )
        return int(active_count or 0)

    def _request_son_price(self, payload: RequestSonPreviewRequest | RequestSonCreateRequest) -> Decimal:
        assert self.settings is not None
        config = self.settings.regen_generation
        total = Decimal(config.owner_son_paid_request_base_cost)
        if payload.requested_name:
            total += Decimal(config.owner_son_paid_request_name_cost)
        if payload.requested_country_code or payload.requested_position:
            total += Decimal(config.owner_son_paid_request_customization_cost)
        return self._normalize_amount(total)

    def _pricing_view(self) -> RegenCreationPricingView:
        assert self.settings is not None
        config = self.settings.regen_generation
        return RegenCreationPricingView(
            base_cost_coin=self._normalize_amount(config.owner_son_paid_request_base_cost),
            name_cost_coin=self._normalize_amount(config.owner_son_paid_request_name_cost),
            customization_cost_coin=self._normalize_amount(config.owner_son_paid_request_customization_cost),
        )

    def _reserve_wallet_for_order(self, *, order: RegenCreationOrder, actor: User) -> None:
        assert self.wallet_service is not None
        amount = self._normalize_amount(order.amount_coin)
        reference = f"regen-wallet-reserve:{order.id}"
        try:
            self.wallet_service.reserve_order_funds(
                self.session,
                user=actor,
                amount=amount,
                reference=reference,
                description="Wallet reservation for requested son regen order.",
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.COSMETIC_SPEND,
                idempotency_key=reference,
                metadata=self._wallet_reservation_transaction_metadata(
                    order=order,
                    amount=amount,
                    action="reserve",
                    reference=reference,
                ),
            )
        except InsufficientBalanceError as exc:
            raise RegenCreationPaymentError("Wallet balance is insufficient for this request.") from exc
        order.payment_provider = "wallet"
        order.payment_reference = reference
        self._set_order_wallet_reservation(
            order=order,
            status="reserved",
            amount=amount,
            reference=reference,
        )

    def _settle_wallet_for_order(self, *, order: RegenCreationOrder, actor: User) -> None:
        assert self.wallet_service is not None
        amount = self._normalize_amount(order.amount_coin)
        reservation = self._order_wallet_reservation(order)
        if reservation.get("status") != "reserved":
            self._debit_wallet_for_order(order=order, actor=actor)
            return

        reserved_amount = self.wallet_service.get_wallet_reservation_balance(
            self.session,
            user=actor,
            unit=LedgerUnit.COIN,
            reservation_kind=REQUEST_SON_WALLET_RESERVATION_KIND,
            reservation_key=self._wallet_reservation_key(order),
        )
        if reserved_amount < amount:
            raise RegenCreationPaymentError("Reserved wallet balance no longer covers this request.")

        escrow_account = self.wallet_service.get_user_escrow_account(self.session, actor, LedgerUnit.COIN)
        operations_account = self.wallet_service.ensure_operations_account(self.session, LedgerUnit.COIN)
        reference = f"regen-wallet-settle:{order.id}"
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-amount),
                LedgerPosting(account=operations_account, amount=amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.COSMETIC_SPEND,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference=reference,
            description="Wallet settlement for requested son regen order.",
            actor=actor,
            idempotency_key=reference,
            metadata=self._wallet_reservation_transaction_metadata(
                order=order,
                amount=amount,
                action="settle",
                reference=reference,
            ),
        )
        order.payment_reference = f"regen-wallet-{order.id}"
        self._set_order_wallet_reservation(
            order=order,
            status="settled",
            amount=amount,
            reference=reference,
        )

    def _release_wallet_for_order(self, *, order: RegenCreationOrder, actor: User) -> None:
        assert self.wallet_service is not None
        amount = self._normalize_amount(order.amount_coin)
        reservation = self._order_wallet_reservation(order)
        if reservation.get("status") == "released":
            return
        if reservation.get("status") != "reserved":
            raise RegenCreationPaymentError("Reserved wallet balance is not available for release.")

        reserved_amount = self.wallet_service.get_wallet_reservation_balance(
            self.session,
            user=actor,
            unit=LedgerUnit.COIN,
            reservation_kind=REQUEST_SON_WALLET_RESERVATION_KIND,
            reservation_key=self._wallet_reservation_key(order),
        )
        if reserved_amount < amount:
            raise RegenCreationPaymentError("Reserved wallet balance no longer covers this request.")

        reference = f"regen-wallet-release:{order.id}"
        self.wallet_service.release_reserved_funds(
            self.session,
            user=actor,
            amount=amount,
            reference=reference,
            description="Release Build-a-Son wallet reservation.",
            unit=LedgerUnit.COIN,
            source_tag=LedgerSourceTag.COSMETIC_SPEND,
            idempotency_key=reference,
            metadata=self._wallet_reservation_transaction_metadata(
                order=order,
                amount=amount,
                action="release",
                reference=reference,
            ),
        )
        self._set_order_wallet_reservation(
            order=order,
            status="released",
            amount=amount,
            reference=reference,
        )

    def _wallet_reservation_transaction_metadata(
        self,
        *,
        order: RegenCreationOrder,
        amount: Decimal,
        action: str,
        reference: str,
    ) -> dict[str, object]:
        return {
            WALLET_RESERVATION_METADATA_KEY: {
                "kind": REQUEST_SON_WALLET_RESERVATION_KIND,
                "key": self._wallet_reservation_key(order),
                "reservation_id": order.id,
                "regen_creation_order_id": order.id,
                "request_type": order.request_type.value,
                "action": action,
                "amount": str(self._normalize_amount(amount)),
                "currency": LedgerUnit.COIN.value,
                "lock_reason": REQUEST_SON_WALLET_RESERVATION_LABEL,
                "reference": reference,
            }
        }

    def _set_order_wallet_reservation(
        self,
        *,
        order: RegenCreationOrder,
        status: str,
        amount: Decimal,
        reference: str,
    ) -> None:
        metadata = dict(order.metadata_json or {})
        metadata["wallet_reservation"] = {
            "kind": REQUEST_SON_WALLET_RESERVATION_KIND,
            "key": self._wallet_reservation_key(order),
            "status": status,
            "amount_coin": str(self._normalize_amount(amount)),
            "currency": LedgerUnit.COIN.value,
            "reference": reference,
            "lock_reason": REQUEST_SON_WALLET_RESERVATION_LABEL,
            "updated_at": utcnow().isoformat(),
        }
        order.metadata_json = metadata

    @staticmethod
    def _wallet_reservation_key(order: RegenCreationOrder) -> str:
        return order.id

    @staticmethod
    def _order_wallet_reservation(order: RegenCreationOrder) -> dict[str, object]:
        metadata = dict(order.metadata_json or {})
        reservation = metadata.get("wallet_reservation")
        return dict(reservation) if isinstance(reservation, dict) else {}

    @staticmethod
    def _wallet_lock_reason_messages(lock_reasons: object) -> list[str]:
        if not isinstance(lock_reasons, (list, tuple)):
            return []
        messages: list[str] = []
        for reason in lock_reasons:
            message = getattr(reason, "message", None)
            if not isinstance(message, str) or not message.strip():
                message = str(reason)
            if message.strip():
                messages.append(message.strip())
        return messages

    def _debit_wallet_for_order(self, *, order: RegenCreationOrder, actor: User) -> None:
        assert self.wallet_service is not None
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        operations_account = self.wallet_service.ensure_operations_account(self.session, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(account=user_account, amount=-self._normalize_amount(order.amount_coin)),
                    LedgerPosting(account=operations_account, amount=self._normalize_amount(order.amount_coin)),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.COSMETIC_SPEND,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
                reference=f"regen-create-wallet:{order.id}",
                description="Wallet payment for requested son regen order.",
                actor=actor,
                idempotency_key=f"regen-create-wallet:{order.id}",
                metadata={"regen_creation_order_id": order.id, "request_type": order.request_type.value},
            )
        except InsufficientBalanceError as exc:
            raise RegenCreationPaymentError("Wallet balance is insufficient for this request.") from exc

    def _generate_order(self, *, order: RegenCreationOrder, actor: User) -> RegenCreationOrderView:
        if order.generated_player_id and order.generated_regen_profile_id:
            previous_status = order.status.value
            order.status = RegenCreationOrderStatus.GENERATED
            order.generated_at = order.generated_at or utcnow()
            self.session.flush()
            if previous_status != RegenCreationOrderStatus.GENERATED.value:
                self._stage_order_event(
                    "regen.creation_order.generated",
                    order=order,
                    actor=actor,
                    previous_status=previous_status,
                )
            return self._order_view(order)

        if order.status not in {RegenCreationOrderStatus.PAID, RegenCreationOrderStatus.GENERATING}:
            raise RegenCreationPaymentError("Payment must be settled before generation.")

        club = self.session.get(ClubProfile, order.club_id) if order.club_id else None
        if club is None:
            club = self._resolve_actor_club(actor)
            order.club_id = club.id
        parent_player = self.session.get(Player, order.parent_player_id) if order.parent_player_id else None
        if parent_player is None:
            raise RegenCreationNotFoundError("Selected parent player was not found.")

        previous_status = order.status.value
        order.status = RegenCreationOrderStatus.GENERATING
        self.session.flush()

        player, regen = self._persist_requested_son(
            order=order,
            club=club,
            actor=actor,
            parent_player=parent_player,
        )
        order.generated_player_id = player.id
        order.generated_regen_profile_id = regen.id
        order.status = RegenCreationOrderStatus.GENERATED
        order.paid_at = order.paid_at or utcnow()
        order.generated_at = utcnow()
        self.session.flush()
        self._stage_order_event(
            "regen.creation_order.generated",
            order=order,
            actor=actor,
            previous_status=previous_status,
        )
        return self._order_view(order)

    def _persist_requested_son(
        self,
        *,
        order: RegenCreationOrder,
        club: ClubProfile,
        actor: User,
        parent_player: Player,
    ) -> tuple[Player, RegenProfile]:
        assert self.engine is not None
        assert self.settings is not None

        target_country_code = self._target_country_code(order=order, club=club, parent_player=parent_player)
        target_region = club.region_name if (club.country_code or "").upper() == target_country_code else None
        target_city = club.city_name if (club.country_code or "").upper() == target_country_code else None
        owner_context = OwnerSonContext(
            owner_user_id=actor.id,
            club_id=club.id,
            club_country_code=target_country_code,
            club_region_name=target_region,
            club_city_name=target_city,
            lifetime_count=self._owner_son_lifetime_count(actor.id),
            lifetime_cap=self.settings.regen_generation.owner_son_lifetime_cap,
        )
        owner_request = OwnerSonRequest(
            request_id=order.id,
            club_id=club.id,
            owner_user_id=actor.id,
            created_at=order.created_at,
            customization=self._owner_customization(order),
            total_cost_coin=int(self._normalize_amount(order.amount_coin)),
            target_club_id=club.id,
        )
        generated = self.engine.generate_academy_intake(
            club_id=club.id,
            season_label=self._season_label(),
            club_context=RegenClubContext(
                country_code=target_country_code,
                region_name=target_region,
                city_name=target_city,
                youth_coaching=62.0,
                training_level=60.0,
                academy_level=62.0,
                academy_investment=60.0,
                first_team_gsi=58.0,
                club_reputation=56.0,
                competition_quality=55.0,
                manager_youth_development=61.0,
                urbanicity="urban" if target_city else None,
            ),
            intake_size=1,
            used_names=self._used_names_for_club(club.id),
            rng=Random(self._generation_seed(order)),
            owner_context=owner_context,
            owner_son_request=owner_request,
        )
        generated_regen = generated.regens[0]
        generated_metadata = self._generated_request_son_metadata(
            order=order,
            parent_player=parent_player,
            generated_regen=generated_regen,
        )
        preview_current_rating = self._preview_projected_int(
            order=order,
            key="projected_ovr",
            fallback=int(generated_regen.current_gsi),
        )
        preview_potential_rating = self._preview_projected_int(
            order=order,
            key="projected_pot",
            fallback=int(generated_regen.potential_range.maximum),
        )
        if preview_potential_rating < preview_current_rating:
            preview_potential_rating = preview_current_rating
        current_ability_range = {
            "minimum": preview_current_rating,
            "maximum": preview_current_rating,
        }
        potential_range = {
            "minimum": preview_current_rating,
            "maximum": preview_potential_rating,
        }
        country = self._ensure_country(generated_regen.birth_country_code)
        card_tier = self._ensure_regen_card_tier()

        player = Player(
            source_provider="gtex_request_son",
            provider_external_id=f"requested-son:{order.id}",
            country_id=country.id,
            current_club_profile_id=club.id,
            full_name=generated_regen.display_name,
            first_name=generated_regen.display_name.split(" ", 1)[0],
            last_name=generated_regen.display_name.split(" ", 1)[1] if " " in generated_regen.display_name else None,
            short_name=generated_regen.display_name,
            position=generated_regen.primary_position,
            normalized_position=self._normalized_position(generated_regen.primary_position),
            date_of_birth=date.today() - timedelta(days=generated_regen.age * 365),
            preferred_foot="right",
            market_value_eur=float(preview_current_rating) * 12_500.0,
            profile_completeness_score=0.98,
            is_tradable=True,
            dna_profile=dict(generated_metadata.get("dna_profile") or {}),
        )
        self.session.add(player)
        self.session.flush()

        self.session.add(
            PlayerVerification(
                player_id=player.id,
                status="verified",
                verification_source="gtex_requested_son",
                confidence_score=1.0,
                rights_confirmed=True,
                reviewer_notes="GTEX paid request-son generation.",
            )
        )

        card = PlayerCard(
            player_id=player.id,
            tier_id=card_tier.id,
            edition_code="regen_unique",
            display_name=generated_regen.display_name,
            season_label=self._season_label(),
            card_variant="requested_son",
            supply_total=1,
            supply_available=1,
            metadata_json={
                "origin_type": "requested_son",
                "regen_id": generated_regen.regen_id,
                "order_id": order.id,
                "visual_profile": generated_metadata.get("visual_profile", {}),
            },
        )
        self.session.add(card)
        self.session.flush()

        self.session.add(
            PlayerCardHistory(
                player_card_id=card.id,
                event_type="requested_son_created",
                description="Paid request-son unique card created.",
                delta_supply=1,
                delta_available=1,
                actor_user_id=actor.id,
                metadata_json={"order_id": order.id, "regen_id": generated_regen.regen_id},
            )
        )
        self.session.add(
            PlayerCardHolding(
                player_card_id=card.id,
                owner_user_id=actor.id,
                quantity_total=1,
                quantity_reserved=0,
                metadata_json={"origin": "requested_son", "order_id": order.id},
            )
        )
        self.session.add(
            PlayerCardOwnerHistory(
                player_card_id=card.id,
                from_user_id=None,
                to_user_id=actor.id,
                quantity=1,
                event_type="requested_son_created",
                reference_id=order.id,
                metadata_json={"club_id": club.id},
            )
        )
        self.session.add(
            PlayerContract(
                player_id=player.id,
                club_id=club.id,
                status="active",
                wage_amount=Decimal("0.00"),
                release_clause_amount=None,
                signed_on=date.today(),
                starts_on=date.today(),
                ends_on=date.today() + timedelta(days=1_095),
            )
        )
        self.session.add(
            PlayerCareerEntry(
                player_id=player.id,
                club_id=club.id,
                club_name=club.club_name,
                season_label=self._season_label(),
                squad_role="requested_son",
                appearances=0,
                goals=0,
                assists=0,
                honours_json=[],
                notes="GTEX paid request-son regen created for club academy.",
                start_on=date.today(),
                end_on=None,
            )
        )
        self.session.add(
            PlayerLifecycleEvent(
                player_id=player.id,
                club_id=club.id,
                event_type="requested_son_created",
                event_status="recorded",
                occurred_on=date.today(),
                effective_from=date.today(),
                summary="Paid request-son regen created and assigned to club development pathway.",
                details_json={"order_id": order.id, "parent_player_id": parent_player.id, "card_id": card.id},
            )
        )

        regen = RegenProfile(
            regen_id=generated_regen.regen_id,
            player_id=player.id,
            linked_unique_card_id=card.id,
            generated_for_club_id=club.id,
            birth_country_code=generated_regen.birth_country_code,
            birth_region=generated_regen.birth_region,
            birth_city=generated_regen.birth_city,
            primary_position=generated_regen.primary_position,
            secondary_positions_json=list(generated_regen.secondary_positions),
            generated_at=generated_regen.generated_at,
            current_gsi=preview_current_rating,
            current_ability_range_json=current_ability_range,
            potential_range_json=potential_range,
            scout_confidence=generated_regen.scout_confidence,
            generation_source="requested_son",
            is_special_lineage=generated_regen.is_special_lineage,
            status=generated_regen.status,
            club_quality_score=generated_regen.club_quality_score,
            metadata_json=generated_metadata,
        )
        self.session.add(regen)
        self.session.flush()

        self.session.add(
            RegenPersonalityProfile(
                regen_profile_id=regen.id,
                temperament=generated_regen.personality.temperament,
                leadership=generated_regen.personality.leadership,
                ambition=generated_regen.personality.ambition,
                loyalty=generated_regen.personality.loyalty,
                work_rate=generated_regen.personality.work_rate,
                flair=generated_regen.personality.flair,
                resilience=generated_regen.personality.resilience,
                personality_tags_json=list(generated_regen.personality.personality_tags),
            )
        )
        self.session.add(
            RegenOriginMetadata(
                regen_profile_id=regen.id,
                country_code=generated_regen.origin.country_code,
                region_name=generated_regen.origin.region_name,
                city_name=generated_regen.origin.city_name,
                hometown_club_affinity=club.club_name,
                ethnolinguistic_profile=generated_regen.origin.ethnolinguistic_profile,
                religion_naming_pattern=generated_regen.origin.religion_naming_pattern,
                urbanicity=generated_regen.origin.urbanicity,
                metadata_json={"request_son_order_id": order.id},
            )
        )

        visual_profile = dict(generated_metadata.get("visual_profile") or {})
        regen_visual_profile = RegenVisualProfile(
            regen_profile_id=regen.id,
            portrait_seed=str(visual_profile.get("portrait_seed", generated_regen.regen_id)),
            skin_tone=visual_profile.get("skin_tone"),
            hair_profile=visual_profile.get("hair_profile"),
            accessory_profile_json={},
            kit_style=visual_profile.get("kit_style"),
            metadata_json={"request_son_order_id": order.id},
        )
        self.session.add(regen_visual_profile)
        RegenPortraitService(self.session).ensure_player_portrait(
            player,
            regen=regen,
            visual_profile=regen_visual_profile,
        )

        lineage_payload = generated_metadata.get("lineage")
        if isinstance(lineage_payload, dict):
            self.session.add(
                RegenLineageProfile(
                    regen_id=regen.id,
                    relationship_type=str(lineage_payload.get("relationship_type", "son_of_owner")),
                    related_legend_type=str(lineage_payload.get("related_legend_type", "club_owner")),
                    related_legend_ref_id=str(lineage_payload.get("related_legend_ref_id", actor.id)),
                    lineage_country_code=str(lineage_payload.get("lineage_country_code", regen.birth_country_code)),
                    lineage_hometown_code=lineage_payload.get("lineage_hometown_code"),
                    is_owner_son=bool(lineage_payload.get("is_owner_son", True)),
                    is_retired_regen_lineage=bool(lineage_payload.get("is_retired_regen_lineage", False)),
                    is_real_legend_lineage=bool(lineage_payload.get("is_real_legend_lineage", False)),
                    is_celebrity_lineage=bool(lineage_payload.get("is_celebrity_lineage", False)),
                    is_celebrity_licensed=bool(lineage_payload.get("is_celebrity_licensed", False)),
                    lineage_tier=str(lineage_payload.get("lineage_tier", "rare")),
                    narrative_text=lineage_payload.get("narrative_text"),
                    metadata_json=dict(lineage_payload),
                )
            )

        parent_legacy = self.session.scalar(
            select(RegenLegacyRecord).where(RegenLegacyRecord.player_id == parent_player.id)
        )
        self.session.add(
            RegenBloodlineLink(
                regen_profile_id=regen.id,
                parent_legacy_id=parent_legacy.id if parent_legacy is not None else None,
                lineage_depth=1,
                metadata_json={
                    "request_son_order_id": order.id,
                    "parent_player_id": parent_player.id,
                    "parent_player_name": parent_player.full_name,
                    "relationship_type": "requested_son",
                },
            )
        )
        self.session.add(
            CareerEvent(
                player_id=player.id,
                regen_profile_id=regen.id,
                type="requested_son_created",
                occurred_on=date.today(),
                impact_json={"order_id": order.id, "parent_player_id": parent_player.id},
                summary=f"Requested son created from {parent_player.full_name}.",
                metadata_json={"order_id": order.id},
            )
        )
        self.session.add(
            RegenStoryEvent(
                event_key=f"career:{order.id}",
                subject_key=player.id,
                player_id=player.id,
                regen_profile_id=regen.id,
                season_id=None,
                event_type="requested_son_created",
                title="Requested son created",
                summary=f"Requested son created from {parent_player.full_name}.",
                occurred_at=utcnow(),
                metadata_json={
                    "order_id": order.id,
                    "parent_player_id": parent_player.id,
                    "parent_player_name": parent_player.full_name,
                    "player_name": player.full_name,
                    "source_type": "regen",
                },
            )
        )
        self.session.add(
            RegenAchievement(
                achievement_key=f"career:{order.id}",
                subject_key=player.id,
                player_id=player.id,
                regen_profile_id=regen.id,
                season_id=None,
                achievement_type="requested_son_created",
                title="Requested son created",
                description=f"{player.full_name} was generated through the paid request-son flow.",
                earned_at=utcnow(),
                metadata_json={
                    "order_id": order.id,
                    "parent_player_id": parent_player.id,
                    "parent_player_name": parent_player.full_name,
                    "player_name": player.full_name,
                    "source_type": "regen",
                },
            )
        )
        self.session.add(
            RegenGenerationEvent(
                regen_profile_id=regen.id,
                club_id=club.id,
                generation_source="requested_son",
                season_label=self._season_label(),
                event_status="generated",
                probability_score=round(generated_regen.potential_range.maximum / 100.0, 4),
                quality_roll=round(generated_regen.club_quality_score / 100.0, 4),
                metadata_json={"request_son_order_id": order.id, "parent_player_id": parent_player.id},
            )
        )
        self.session.add(
            RegenOnboardingFlag(
                regen_id=regen.id,
                club_id=club.id,
                onboarding_type="requested_son",
                squad_bucket="academy",
                squad_slot=None,
                is_non_tradable=False,
                replacement_only=False,
                metadata_json={"request_son_order_id": order.id},
            )
        )

        customization = self._owner_customization(order)
        raw_foot = customization.get("favorite_foot")
        if isinstance(raw_foot, str):
            player.preferred_foot = raw_foot
        raw_height = customization.get("height_cm")
        if raw_height is not None:
            try:
                player.height_cm = int(raw_height)
            except (TypeError, ValueError):
                pass

        self.session.flush()
        return player, regen

    def _owner_customization(self, order: RegenCreationOrder) -> dict[str, object]:
        customization = self._customization_payload(
            requested_name=order.requested_name,
            requested_position=order.requested_position,
            requested_country_code=order.requested_country_code,
            selected_traits=self._order_selected_traits(order)[:3],
        )
        return customization

    def _generated_request_son_metadata(
        self,
        *,
        order: RegenCreationOrder,
        parent_player: Player,
        generated_regen,
    ) -> dict[str, object]:
        metadata = dict(generated_regen.metadata) if isinstance(generated_regen.metadata, dict) else {}
        order_metadata = dict(order.metadata_json or {})
        preview = order_metadata.get("request_son_preview")
        preview_payload = preview if isinstance(preview, dict) else {}

        parent_generation = self._coerce_int(preview_payload.get("parent_generation"))
        projected_generation = self._coerce_int(preview_payload.get("projected_generation"))
        if projected_generation is None:
            parent_regen = self._parent_regen_profile(parent_player)
            parent_generation = self._parent_generation(player=parent_player, regen=parent_regen)
            projected_generation = (parent_generation or 0) + 1

        preview_traits = self._string_list(preview_payload.get("selected_traits"))
        selected_traits = preview_traits or self._order_selected_traits(order)
        preview_dna = preview_payload.get("projected_dna_profile")
        dna_profile = (
            dict(preview_dna)
            if isinstance(preview_dna, dict) and preview_dna
            else dict(metadata.get("dna_profile") or {})
        )
        if selected_traits:
            dna_profile["traits"] = list(selected_traits)
            dna_profile["selected_traits"] = list(selected_traits)
            metadata["selected_traits"] = list(selected_traits)
        dna_profile["generation"] = projected_generation
        dna_profile["generation_index"] = projected_generation
        dna_profile["generation_label"] = f"GEN-{projected_generation}"
        if parent_generation is not None:
            dna_profile["parent_generation"] = parent_generation
            metadata["parent_generation"] = parent_generation

        metadata["dna_profile"] = dna_profile
        metadata["generation"] = projected_generation
        metadata["generation_index"] = projected_generation
        metadata["generation_label"] = f"GEN-{projected_generation}"
        metadata["parent_player_id"] = parent_player.id
        metadata["parent_player_name"] = parent_player.full_name

        projected_ovr = self._coerce_int(preview_payload.get("projected_ovr"))
        if projected_ovr is not None:
            dna_profile["current_rating"] = projected_ovr
            dna_profile["current_gsi"] = projected_ovr
            dna_profile["ovr"] = projected_ovr
            metadata["current_rating"] = projected_ovr
            metadata["projected_ovr"] = projected_ovr
            projected_value_coin = max(0, projected_ovr * 12_500)
            metadata["projected_value_coin"] = projected_value_coin
            metadata["market_value_coin"] = projected_value_coin
        projected_pot = self._coerce_int(preview_payload.get("projected_pot"))
        if projected_pot is not None:
            potential_rating = max(projected_pot, projected_ovr or projected_pot)
            dna_profile["potential_rating"] = potential_rating
            dna_profile["projected_pot"] = potential_rating
            metadata["potential_rating"] = potential_rating
            metadata["projected_pot"] = potential_rating

        projected_dna = preview_payload.get("projected_dna")
        if isinstance(projected_dna, dict):
            dna_bars: dict[str, int] = {}
            for code in ("PAC", "SHO", "PAS", "DRI", "DEF", "PHY"):
                value = self._coerce_int(projected_dna.get(code) or projected_dna.get(code.lower()))
                if value is not None:
                    dna_bars[code] = max(1, min(99, value))
            if dna_bars:
                metadata["projected_dna"] = dict(dna_bars)
                dna_profile["projected_dna"] = dict(dna_bars)
                dna_profile.update(dna_bars)

        metadata["dna_profile"] = dna_profile

        lineage = dict(metadata.get("lineage") or {})
        lineage.update(
            {
                "parent_player_id": parent_player.id,
                "parent_player_name": parent_player.full_name,
                "generation": projected_generation,
                "generation_index": projected_generation,
                "generation_label": f"GEN-{projected_generation}",
            }
        )
        lineage.setdefault("lineage_tier", "rare")
        if parent_generation is not None:
            lineage["parent_generation"] = parent_generation
        metadata["lineage"] = lineage
        metadata["rarity_tier"] = lineage["lineage_tier"]
        return self._json_safe(metadata)

    def _preview_projected_int(
        self,
        *,
        order: RegenCreationOrder,
        key: str,
        fallback: int,
    ) -> int:
        metadata = dict(order.metadata_json or {})
        preview = metadata.get("request_son_preview")
        preview_payload = preview if isinstance(preview, dict) else {}
        value = self._coerce_int(preview_payload.get(key))
        if value is None:
            return fallback
        return max(1, min(99, value))

    def _payload_customization(
        self,
        *,
        payload: RequestSonPreviewRequest | RequestSonCreateRequest,
        selected_traits: list[str],
    ) -> dict[str, object]:
        return self._customization_payload(
            requested_name=payload.requested_name,
            requested_position=payload.requested_position,
            requested_country_code=payload.requested_country_code,
            selected_traits=selected_traits,
        )

    @staticmethod
    def _customization_payload(
        *,
        requested_name: str | None,
        requested_position: str | None,
        requested_country_code: str | None,
        selected_traits: list[str],
    ) -> dict[str, object]:
        customization: dict[str, object] = {}
        if requested_name:
            customization["name"] = requested_name
        if requested_position:
            customization["position"] = requested_position
        if requested_country_code:
            customization["country_code"] = requested_country_code
        if selected_traits:
            customization["selected_traits"] = list(selected_traits)
        return customization

    def _target_country_code(self, *, order: RegenCreationOrder, club: ClubProfile, parent_player: Player) -> str:
        return self._target_country_code_for_request(
            requested_country_code=order.requested_country_code,
            club=club,
            parent_player=parent_player,
        )

    def _target_country_code_for_request(
        self,
        *,
        requested_country_code: str | None,
        club: ClubProfile,
        parent_player: Player,
    ) -> str:
        if requested_country_code:
            return requested_country_code.strip().upper()
        if club.country_code:
            return club.country_code.strip().upper()
        if parent_player.country_id:
            country = self.session.get(Country, parent_player.country_id)
            if country is not None:
                for candidate in (country.alpha2_code, country.alpha3_code, country.fifa_code):
                    if candidate:
                        return str(candidate).strip().upper()
        assert self.settings is not None
        return self.settings.regen_generation.default_country_code

    def _used_names_for_club(self, club_id: str) -> set[str]:
        names = self.session.scalars(select(Player.full_name).where(Player.current_club_profile_id == club_id)).all()
        return {name for name in names if isinstance(name, str) and name.strip()}

    def _owner_son_lifetime_count(self, user_id: str) -> int:
        count = self.session.scalar(
            select(func.count(RegenLineageProfile.id)).where(
                RegenLineageProfile.is_owner_son.is_(True),
                RegenLineageProfile.related_legend_ref_id == user_id,
            )
        )
        return int(count or 0)

    def _parent_player_view(
        self,
        *,
        player: Player,
        club: ClubProfile,
        country: Country | None,
        regen: RegenProfile | None = None,
    ) -> RegenCreationParentPlayerView:
        parent_regen = regen or self._parent_regen_profile(player)
        nationality = country.name if country is not None else self._country_code(country)
        return RegenCreationParentPlayerView(
            player_id=player.id,
            full_name=player.full_name,
            image_url=self._player_image_url(player),
            portrait_url=self._player_image_url(player),
            position=self._parent_position(player),
            current_rating=self._parent_current_rating(player=player, regen=parent_regen),
            country_code=self._country_code(country),
            country_name=country.name if country is not None else None,
            nationality=nationality,
            club_id=club.id,
            club_name=club.club_name,
            traits=self._parent_traits(player=player, regen=parent_regen),
            lineage=self._parent_lineage(parent_regen),
            generation=self._parent_generation(player=player, regen=parent_regen),
            dna_profile=self._parent_dna_profile(player=player, regen=parent_regen),
        )

    def _parent_canonical_truth_gap(self, parent: RegenCreationParentPlayerView) -> str | None:
        if not parent.position:
            return "request_son_parent_missing_position"
        if parent.current_rating is None or parent.current_rating <= 0:
            return "request_son_parent_missing_current_rating"
        if not (parent.country_code or parent.country_name or parent.nationality):
            return "request_son_parent_missing_nationality"
        if parent.generation is None or parent.generation <= 0:
            return "request_son_parent_missing_generation"
        if not isinstance(parent.dna_profile, dict) or not parent.dna_profile:
            return "request_son_parent_missing_dna_profile"
        if not self._has_selectable_parent_traits(parent.traits):
            return "request_son_parent_missing_traits"
        return None

    def _parent_regen_profile(self, player: Player) -> RegenProfile | None:
        return self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))

    def _parent_position(self, player: Player) -> str | None:
        raw_position = player.position or player.normalized_position
        if not isinstance(raw_position, str):
            return None
        normalized = REQUEST_SON_PARENT_POSITION_ALIASES.get(raw_position.strip().upper(), raw_position.strip().upper())
        if normalized in REQUEST_SON_PARENT_POSITIONS:
            return normalized
        return None

    def _parent_current_rating(self, *, player: Player, regen: RegenProfile | None) -> int | None:
        if regen is not None:
            return int(regen.current_gsi)
        dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
        for key in ("current_rating", "current_gsi", "gsi", "overall", "ovr", "rating"):
            rating = self._coerce_int(dna.get(key))
            if rating is not None:
                return rating
        return None

    def _parent_traits(self, *, player: Player, regen: RegenProfile | None) -> list[str]:
        explicit_traits: list[str] = []
        fallback_traits: list[str] = []
        dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
        regen_metadata = regen.metadata_json if regen is not None and isinstance(regen.metadata_json, dict) else {}
        for source in (dna, regen_metadata):
            for key in ("traits", "selected_traits", "unique_traits"):
                explicit_traits.extend(self._string_list(source.get(key)))
            fallback_traits.extend(self._string_list(source.get("relationship_tags")))
            decision_traits = source.get("decision_traits")
            if isinstance(decision_traits, dict):
                fallback_traits.extend(str(key) for key in decision_traits if isinstance(key, str) and key.strip())
        if explicit_traits:
            return self._dedupe_strings(explicit_traits)
        return self._dedupe_strings(fallback_traits)

    def _parent_lineage(self, regen: RegenProfile | None) -> dict[str, object]:
        if regen is None:
            return {}
        metadata = regen.metadata_json if isinstance(regen.metadata_json, dict) else {}
        lineage = metadata.get("lineage")
        if isinstance(lineage, dict):
            return self._json_safe(lineage)
        lineage_profile = self.session.scalar(
            select(RegenLineageProfile).where(RegenLineageProfile.regen_id == regen.id)
        )
        if lineage_profile is None:
            return {}
        return self._json_safe(
            {
                "relationship_type": lineage_profile.relationship_type,
                "related_legend_type": lineage_profile.related_legend_type,
                "related_legend_ref_id": lineage_profile.related_legend_ref_id,
                "lineage_country_code": lineage_profile.lineage_country_code,
                "lineage_hometown_code": lineage_profile.lineage_hometown_code,
                "lineage_tier": lineage_profile.lineage_tier,
                "narrative_text": lineage_profile.narrative_text,
                **dict(lineage_profile.metadata_json or {}),
            }
        )

    def _parent_generation(self, *, player: Player, regen: RegenProfile | None) -> int | None:
        sources: list[dict[str, object]] = []
        if isinstance(player.dna_profile, dict):
            sources.append(player.dna_profile)
        if regen is not None and isinstance(regen.metadata_json, dict):
            sources.append(regen.metadata_json)
            lineage = regen.metadata_json.get("lineage")
            if isinstance(lineage, dict):
                sources.append(lineage)
        for source in sources:
            for key in ("generation", "generation_index", "generation_number"):
                generation = self._coerce_int(source.get(key))
                if generation is not None:
                    return generation
        return None

    def _parent_dna_profile(self, *, player: Player, regen: RegenProfile | None) -> dict[str, object]:
        if isinstance(player.dna_profile, dict) and player.dna_profile:
            return self._json_safe(player.dna_profile)
        metadata = regen.metadata_json if regen is not None and isinstance(regen.metadata_json, dict) else {}
        dna_profile = metadata.get("dna_profile")
        if isinstance(dna_profile, dict):
            return self._json_safe(dna_profile)
        return {}

    def _canonical_selected_traits(self, *, available_traits: list[str], selected_traits: list[str]) -> list[str]:
        available_by_key = {self._trait_key(trait): trait for trait in available_traits if self._trait_key(trait)}
        if not available_by_key:
            raise RegenCreationValidationError("parent_traits_unavailable")
        canonical: list[str] = []
        missing: list[str] = []
        for trait in selected_traits:
            key = self._trait_key(trait)
            if key not in available_by_key:
                missing.append(trait)
                continue
            if available_by_key[key] in canonical:
                raise RegenCreationValidationError("selected_traits_must_be_three_unique_parent_traits")
            canonical.append(available_by_key[key])
        if missing:
            raise RegenCreationValidationError("selected_traits_must_belong_to_parent")
        if len(canonical) != 3:
            raise RegenCreationValidationError("selected_traits_must_be_three_unique_parent_traits")
        return canonical

    def _has_selectable_parent_traits(self, traits: list[str]) -> bool:
        return len({self._trait_key(trait) for trait in traits if self._trait_key(trait)}) >= 3

    def _projected_dna_profile(self, projected) -> dict[str, object]:
        metadata = projected.metadata if isinstance(projected.metadata, dict) else {}
        dna_profile = metadata.get("dna_profile")
        if isinstance(dna_profile, dict):
            return self._json_safe(dna_profile)
        return {}

    def _projected_dna_bars(
        self,
        *,
        current_rating: int,
        position: str | None,
        dna_profile: dict[str, object],
    ) -> dict[str, int]:
        tempo = self._unit_float(dna_profile.get("tempo"), fallback=0.5)
        risk = self._unit_float(dna_profile.get("risk_taking"), fallback=0.5)
        creativity = self._unit_float(dna_profile.get("creativity"), fallback=0.5)
        discipline = self._unit_float(dna_profile.get("discipline"), fallback=0.5)
        position_key = (position or "").upper()
        defensive_bias = 6 if position_key in {"GK", "CB", "RB", "LB", "DM"} else -2
        forward_bias = 5 if position_key in {"RW", "LW", "ST", "AM"} else -1
        return {
            "PAC": self._rating_bar(current_rating + ((tempo - 0.5) * 26)),
            "SHO": self._rating_bar(current_rating + ((risk - 0.5) * 18) + forward_bias),
            "PAS": self._rating_bar(current_rating + ((creativity - 0.5) * 22) + ((discipline - 0.5) * 8)),
            "DRI": self._rating_bar(current_rating + ((tempo - 0.5) * 12) + ((creativity - 0.5) * 18)),
            "DEF": self._rating_bar(current_rating + ((discipline - 0.5) * 24) + defensive_bias - ((risk - 0.5) * 6)),
            "PHY": self._rating_bar(current_rating + ((discipline - 0.5) * 12) + ((tempo - 0.5) * 10)),
        }

    def _preview_seed(
        self,
        *,
        actor: User,
        club: ClubProfile,
        parent_player: Player,
        payload: RequestSonPreviewRequest | RequestSonCreateRequest,
        selected_traits: list[str],
    ) -> str:
        raw = "|".join(
            (
                actor.id,
                club.id,
                parent_player.id,
                payload.requested_name or "",
                payload.requested_country_code or "",
                payload.requested_position or "",
                ",".join(selected_traits),
            )
        )
        return sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _generation_seed(order: RegenCreationOrder) -> str:
        metadata = dict(order.metadata_json or {})
        seed = metadata.get("preview_seed")
        if isinstance(seed, str) and seed.strip():
            return seed.strip()
        return order.id

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = RegenCreationService._trait_key(value)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        return deduped

    @staticmethod
    def _trait_key(value: str) -> str:
        return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _unit_float(value: object, *, fallback: float) -> float:
        try:
            resolved = float(value)
        except (TypeError, ValueError):
            resolved = fallback
        return max(0.0, min(1.0, resolved))

    @staticmethod
    def _rating_bar(value: float) -> int:
        return max(1, min(99, int(round(value))))

    @staticmethod
    def _order_selected_traits(order: RegenCreationOrder) -> list[str]:
        metadata = dict(order.metadata_json or {})
        return [
            str(value).strip()
            for value in metadata.get("selected_traits", [])
            if isinstance(value, str) and value.strip()
        ]

    def _generated_player_view(self, order: RegenCreationOrder) -> RegenCreationGeneratedPlayerView | None:
        if not order.generated_player_id or not order.generated_regen_profile_id:
            return None
        player = self.session.get(Player, order.generated_player_id)
        regen = self.session.get(RegenProfile, order.generated_regen_profile_id)
        if player is None or regen is None:
            return None
        country = self.session.get(Country, player.country_id) if player.country_id else None
        club = self.session.get(ClubProfile, player.current_club_profile_id) if player.current_club_profile_id else None
        potential = regen.potential_range_json or {}
        metadata = dict(regen.metadata_json or {}) if isinstance(regen.metadata_json, dict) else {}
        lineage_payload = metadata.get("lineage")
        lineage = lineage_payload if isinstance(lineage_payload, dict) else {}
        player_dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        dna_profile = self._generated_son_dna_bars(metadata=metadata, player_dna=player_dna)
        generation_number = (
            self._coerce_int(metadata.get("generation"))
            or self._coerce_int(metadata.get("generation_index"))
            or self._coerce_int(lineage.get("generation"))
        )
        generation_label = self._string_value(metadata.get("generation_label")) or self._string_value(
            lineage.get("generation_label")
        )
        if generation_label is None and generation_number is not None:
            generation_label = f"GEN-{generation_number}"
        return RegenCreationGeneratedPlayerView(
            player_id=player.id,
            regen_profile_id=regen.id,
            full_name=player.full_name,
            image_url=self._player_image_url(player),
            portrait_url=self._player_image_url(player),
            age=self._calculate_age(player.date_of_birth),
            position=regen.primary_position,
            country_code=self._country_code(country),
            country_name=country.name if country is not None else None,
            club_id=club.id if club is not None else None,
            club_name=club.club_name if club is not None else None,
            current_rating=int(regen.current_gsi),
            potential_rating=int(potential.get("maximum") or regen.current_gsi),
            card_id=regen.linked_unique_card_id,
            generation_number=generation_number,
            generation_label=generation_label,
            traits=self._generated_son_traits(metadata=metadata, player_dna=player_dna),
            lineage=self._generated_son_lineage(metadata=metadata, player=player),
            dna_profile=dna_profile,
            origin_story=(
                self._string_value(metadata.get("origin_story"))
                or self._string_value(metadata.get("originStory"))
                or self._string_value(lineage.get("narrative_text"))
            ),
            projected_value_coin=self._generated_son_projected_value(metadata),
            rarity_tier=(
                self._string_value(metadata.get("rarity_tier"))
                or self._string_value(metadata.get("rarityTier"))
                or self._string_value(lineage.get("lineage_tier"))
            ),
        )

    def _generated_son_traits(self, *, metadata: dict[str, object], player_dna: dict[str, object]) -> list[str]:
        traits: list[str] = []
        for source in (metadata, player_dna):
            for key in ("selected_traits", "traits", "trait_names", "unique_traits"):
                traits.extend(self._string_list(source.get(key)))
        return self._dedupe_strings(traits)

    def _generated_son_lineage(self, *, metadata: dict[str, object], player: Player) -> list[str]:
        values: list[str] = []
        lineage_payload = metadata.get("lineage")
        if isinstance(lineage_payload, list):
            values.extend(self._string_list(lineage_payload))
        if isinstance(lineage_payload, dict):
            for key in ("bloodline", "lineage", "lineage_names", "bloodline_names"):
                values.extend(self._string_list(lineage_payload.get(key)))
            parent_name = self._string_value(lineage_payload.get("parent_player_name"))
            if parent_name:
                values.append(parent_name)
        parent_name = self._string_value(metadata.get("parent_player_name"))
        if parent_name:
            values.append(parent_name)
        values.append(player.full_name)
        return self._dedupe_strings(values)

    def _generated_son_dna_bars(
        self,
        *,
        metadata: dict[str, object],
        player_dna: dict[str, object],
    ) -> dict[str, int]:
        projected_dna = metadata.get("projected_dna")
        source = projected_dna if isinstance(projected_dna, dict) else player_dna
        bars: dict[str, int] = {}
        for code in ("PAC", "SHO", "PAS", "DRI", "DEF", "PHY"):
            value = source.get(code) or source.get(code.lower())
            resolved = self._coerce_int(value)
            if resolved is None:
                continue
            bars[code] = max(1, min(99, resolved))
        return bars

    def _generated_son_projected_value(self, metadata: dict[str, object]) -> int | None:
        for key in ("projected_value_coin", "projectedValueCoin", "market_value_coin", "marketValueCoin"):
            value = self._coerce_int(metadata.get(key))
            if value is not None:
                return max(0, value)
        return None

    @staticmethod
    def _string_value(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _player_image_url(self, player: Player) -> str | None:
        dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        for key in ("portraitUrl", "portrait_url", "image_url", "photo_url"):
            value = dna.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for image in sorted(
            player.image_metadata,
            key=lambda item: (
                not item.is_primary,
                item.moderation_status != "approved",
                item.created_at,
                item.id,
            ),
        ):
            if image.moderation_status == "rejected":
                continue
            if image.source_url:
                return image.source_url
            if image.storage_key:
                return image.storage_key
        if not bool(player.is_real_player):
            try:
                return RegenPortraitService(self.session).ensure_player_portrait(player).portrait_url
            except Exception:
                return None
        return None

    def _stage_order_event(
        self,
        event_name: str,
        *,
        order: RegenCreationOrder,
        actor: User,
        previous_status: str | None,
    ) -> None:
        assert self.event_publisher is not None
        defer_event_publish_until_commit(
            self.session,
            publisher=self.event_publisher,
            event=DomainEvent(
                name=event_name,
                payload=self._order_event_payload(
                    order=order,
                    actor=actor,
                    previous_status=previous_status,
                    event_name=event_name,
                ),
                aggregate_id=order.id,
                aggregate_type="regen_creation_order",
                producer="regen_creation_service",
                partition_key=actor.id,
                headers={
                    "audit_reference": self._order_audit_reference(
                        order,
                        event_name=event_name,
                    ),
                },
            ),
        )

    def _order_event_payload(
        self,
        *,
        order: RegenCreationOrder,
        actor: User,
        previous_status: str | None,
        event_name: str,
    ) -> dict[str, object | None]:
        return {
            "order_id": order.id,
            "user_id": order.user_id,
            "actor_user_id": actor.id,
            "club_id": order.club_id,
            "request_type": order.request_type.value,
            "status": order.status.value,
            "previous_status": previous_status,
            "payment_method": order.payment_method.value,
            "payment_provider": order.payment_provider,
            "payment_reference": order.payment_reference,
            "wallet_reservation": self._order_wallet_reservation(order),
            "generated_player_id": order.generated_player_id,
            "generated_regen_profile_id": order.generated_regen_profile_id,
            "amount_coin": str(self._normalize_amount(order.amount_coin)),
            "currency": order.currency,
            "audit_reference": self._order_audit_reference(
                order,
                event_name=event_name,
            ),
        }

    @staticmethod
    def _order_audit_reference(
        order: RegenCreationOrder,
        *,
        event_name: str | None = None,
    ) -> str:
        if event_name:
            action = event_name.rsplit(".", maxsplit=1)[-1]
            return f"regen-creation-order:{order.id}:{action}"
        return f"regen-creation-order:{order.id}"

    def _order_view(self, order: RegenCreationOrder) -> RegenCreationOrderView:
        metadata = dict(order.metadata_json or {})
        return RegenCreationOrderView(
            id=order.id,
            user_id=order.user_id,
            club_id=order.club_id,
            request_type=order.request_type.value,
            parent_player_id=order.parent_player_id,
            selected_traits=self._order_selected_traits(order),
            requested_name=order.requested_name,
            requested_country_code=order.requested_country_code,
            requested_position=order.requested_position,
            amount_coin=self._normalize_amount(order.amount_coin),
            amount_minor=order.amount_minor,
            currency=order.currency,
            payment_method=order.payment_method.value,
            payment_provider=order.payment_provider,
            payment_reference=order.payment_reference,
            audit_reference=self._order_audit_reference(order),
            status=order.status.value,
            generated_player_id=order.generated_player_id,
            generated_regen_profile_id=order.generated_regen_profile_id,
            payment_link=str(metadata.get("payment_link") or "") or None,
            mock_payment=bool(metadata.get("mock_payment", False)),
            wallet_reservation=self._wallet_reservation_view(order),
            created_at=order.created_at,
            updated_at=order.updated_at,
            paid_at=order.paid_at,
            generated_at=order.generated_at,
            generated_player=self._generated_player_view(order),
        )

    def _wallet_reservation_view(self, order: RegenCreationOrder) -> RegenCreationWalletReservationView | None:
        reservation = self._order_wallet_reservation(order)
        if not reservation:
            return None
        raw_amount = reservation.get("amount_coin") or reservation.get("amount") or Decimal("0.0000")
        raw_updated_at = reservation.get("updated_at")
        updated_at = None
        if isinstance(raw_updated_at, datetime):
            updated_at = raw_updated_at
        elif isinstance(raw_updated_at, str) and raw_updated_at.strip():
            try:
                updated_at = datetime.fromisoformat(raw_updated_at)
            except ValueError:
                updated_at = None
        return RegenCreationWalletReservationView(
            kind=str(reservation.get("kind") or REQUEST_SON_WALLET_RESERVATION_KIND),
            key=str(reservation.get("key") or self._wallet_reservation_key(order)),
            status=str(reservation.get("status") or "unknown"),
            amount_coin=self._normalize_amount(raw_amount),
            currency=str(reservation.get("currency") or LedgerUnit.COIN.value),
            reference=str(reservation.get("reference") or "") or None,
            lock_reason=str(reservation.get("lock_reason") or "") or None,
            updated_at=updated_at,
        )

    def _owned_order(self, *, actor: User, order_id: str) -> RegenCreationOrder:
        order = self.session.scalar(
            select(RegenCreationOrder).where(
                RegenCreationOrder.id == order_id,
                RegenCreationOrder.user_id == actor.id,
            )
        )
        if order is None:
            raise RegenCreationNotFoundError("Regen creation order was not found.")
        return order

    def _ensure_country(self, country_code: str) -> Country:
        resolved = (country_code or "").strip().upper()
        country = self.session.scalar(
            select(Country).where(
                (Country.alpha2_code == resolved) | (Country.alpha3_code == resolved) | (Country.fifa_code == resolved)
            )
        )
        if country is not None:
            return country
        country = Country(
            source_provider="gtex_request_son",
            provider_external_id=f"country:{resolved}",
            name=resolved,
            alpha2_code=resolved,
            alpha3_code=resolved,
            fifa_code=resolved,
            confederation_code=None,
            market_region="regen",
            is_enabled_for_universe=True,
        )
        self.session.add(country)
        self.session.flush()
        return country

    def _request_son_country_options(self) -> list[RequestSonCountryOptionView]:
        default_code = self._default_request_son_country_code()
        countries = self.session.scalars(
            select(Country)
            .where(Country.is_enabled_for_universe.is_(True))
            .order_by(Country.name.asc(), Country.alpha2_code.asc())
        ).all()
        options: list[RequestSonCountryOptionView] = []
        seen: set[str] = set()
        for country in countries:
            code = self._country_code(country)
            if not code or code in seen:
                continue
            seen.add(code)
            options.append(
                RequestSonCountryOptionView(
                    code=code,
                    name=country.name,
                    alpha2_code=self._clean_code(country.alpha2_code),
                    alpha3_code=self._clean_code(country.alpha3_code),
                    fifa_code=self._clean_code(country.fifa_code),
                    flag_url=country.flag_url,
                    market_region=country.market_region,
                    is_default=code == default_code,
                )
            )
        if default_code and default_code not in seen:
            options.append(
                RequestSonCountryOptionView(
                    code=default_code,
                    name=default_code,
                    alpha2_code=default_code,
                    alpha3_code=default_code,
                    fifa_code=default_code,
                    market_region="regen",
                    is_default=True,
                )
            )
        return options

    def _request_son_position_options(self) -> list[RequestSonPositionOptionView]:
        return [
            RequestSonPositionOptionView(
                code=code,
                label=label,
                aliases=list(aliases),
                group=group,
                is_default=code == "AM",
            )
            for code, label, aliases, group in REQUEST_SON_POSITION_OPTIONS
        ]

    def _default_request_son_country_code(self) -> str | None:
        assert self.settings is not None
        return self._clean_code(self.settings.regen_generation.default_country_code)

    def _ensure_regen_card_tier(self) -> PlayerCardTier:
        tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == "regen_unique"))
        if tier is not None:
            return tier
        tier = PlayerCardTier(
            code="regen_unique",
            name="Regen Unique",
            rarity_rank=99,
            max_supply=1,
            supply_multiplier=Decimal("1.0000"),
            base_mint_price_credits=Decimal("0.0000"),
            color_hex="#C88C2D",
            is_active=True,
            metadata_json={"origin_type": "regen"},
        )
        self.session.add(tier)
        self.session.flush()
        return tier

    @staticmethod
    def _normalized_position(position: str) -> str:
        if position == "GK":
            return "goalkeeper"
        if position in {"CB", "RB", "LB"}:
            return "defender"
        if position in {"DM", "CM", "AM"}:
            return "midfielder"
        return "forward"

    @staticmethod
    def _calculate_age(date_of_birth: date | None) -> int:
        if date_of_birth is None:
            return 0
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return max(age, 0)

    @staticmethod
    def _country_code(country: Country | None) -> str | None:
        if country is None:
            return None
        for candidate in (country.alpha2_code, country.alpha3_code, country.fifa_code):
            if candidate:
                return str(candidate).strip().upper()
        return None

    @staticmethod
    def _clean_code(value: object) -> str | None:
        if value is None:
            return None
        parsed = str(value).strip().upper()
        return parsed or None

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): RegenCreationService._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [RegenCreationService._json_safe(item) for item in value]
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date,)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _season_label() -> str:
        today = date.today()
        start_year = today.year if today.month >= 7 else today.year - 1
        return f"{start_year}/{start_year + 1}"


__all__ = [
    "RegenCreationConflictError",
    "RegenCreationError",
    "RegenCreationNotFoundError",
    "RegenCreationPaymentError",
    "RegenCreationPermissionError",
    "RegenCreationService",
    "RegenCreationValidationError",
]
