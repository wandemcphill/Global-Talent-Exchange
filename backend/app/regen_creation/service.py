from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import os
from random import Random
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
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
    RequestSonCreateRequest,
    RequestSonOptionsView,
)
from app.services.regen_service import OwnerSonContext, OwnerSonRequest, RegenClubContext, RegenGenerationEngine
from app.treasury.service import TreasuryError, TreasuryService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
KORAPAY_BASE_URL = "https://api.korapay.com/merchant/api/v1"


class RegenCreationError(ValueError):
    pass


class RegenCreationNotFoundError(RegenCreationError):
    pass


class RegenCreationValidationError(RegenCreationError):
    pass


class RegenCreationPermissionError(RegenCreationError):
    pass


class RegenCreationPaymentError(RegenCreationError):
    pass


class RegenCreationConflictError(RegenCreationError):
    pass


@dataclass(slots=True)
class RegenCreationService:
    session: Session
    settings: Settings | None = None
    wallet_service: WalletService | None = None
    treasury_service: TreasuryService | None = None
    engine: RegenGenerationEngine | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.wallet_service = self.wallet_service or WalletService()
        self.treasury_service = self.treasury_service or TreasuryService(wallet_service=self.wallet_service)
        self.engine = self.engine or RegenGenerationEngine(self.settings)

    def request_son_options(self, actor: User) -> RequestSonOptionsView:
        club = self._resolve_actor_club(actor)
        pricing = self._pricing_view()
        eligible = [
            self._parent_player_view(player=player, club=club, country=country)
            for player, country in self._eligible_parent_rows(club.id)
        ]
        return RequestSonOptionsView(
            club_id=club.id,
            club_name=club.club_name,
            currency="COIN",
            pricing=pricing,
            eligible_parents=eligible,
        )

    def create_request_son_order(
        self,
        *,
        actor: User,
        payload: RequestSonCreateRequest,
    ) -> RegenCreationOrderView:
        club = self._resolve_actor_club(actor)
        parent_player = self._resolve_parent_player(
            club=club,
            actor=actor,
            parent_player_id=payload.parent_player_id,
        )
        self._enforce_request_limit(actor)

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
            payment_method=RegenCreationPaymentMethod(payload.payment_method),
            payment_provider=(None if payload.payment_method == RegenCreationPaymentMethod.WALLET.value else "korapay"),
            status=RegenCreationOrderStatus.PENDING_PAYMENT,
            metadata_json={
                "request_source": "request_son",
                "parent_player_name": parent_player.full_name,
                "club_name": club.club_name,
            },
        )
        self.session.add(order)
        self.session.flush()

        if order.payment_method == RegenCreationPaymentMethod.KORAPAY:
            self._configure_korapay_checkout(order=order, actor=actor)

        self.session.flush()
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
            self._debit_wallet_for_order(order=order, actor=actor)
            order.status = RegenCreationOrderStatus.PAID
            order.payment_provider = "wallet"
            order.payment_reference = order.payment_reference or f"regen-wallet-{order.id}"
            order.paid_at = order.paid_at or utcnow()
            self.session.flush()
        return self._generate_order(order=order, actor=actor)

    def generate_after_payment(self, *, actor: User, order_id: str) -> RegenCreationOrderView:
        order = self._owned_order(actor=actor, order_id=order_id)
        if order.status == RegenCreationOrderStatus.GENERATED:
            return self._order_view(order)
        if order.payment_method == RegenCreationPaymentMethod.WALLET:
            if order.status != RegenCreationOrderStatus.PAID:
                raise RegenCreationPaymentError("Payment must be settled before generation.")
            return self._generate_order(order=order, actor=actor)
        if order.status == RegenCreationOrderStatus.PENDING_PAYMENT:
            self._verify_and_mark_korapay_paid(order)
        if order.status not in {RegenCreationOrderStatus.PAID, RegenCreationOrderStatus.GENERATING}:
            raise RegenCreationPaymentError("Payment must be settled before generation.")
        return self._generate_order(order=order, actor=actor)

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

    def _enforce_request_limit(self, actor: User) -> None:
        assert self.settings is not None
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
        if int(active_count or 0) >= int(self.settings.regen_generation.owner_son_paid_request_limit):
            raise RegenCreationConflictError("owner_son_paid_request_limit_reached")

    def _request_son_price(self, payload: RequestSonCreateRequest) -> Decimal:
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

    def _configure_korapay_checkout(self, *, order: RegenCreationOrder, actor: User) -> None:
        assert self.treasury_service is not None
        settings = self.treasury_service.ensure_settings(self.session)
        try:
            quote = self.treasury_service.compute_deposit_quote(
                settings,
                amount=self._normalize_amount(order.amount_coin),
                input_unit="coin",
            )
        except TreasuryError as exc:
            raise RegenCreationPaymentError(str(exc)) from exc

        reference = order.payment_reference or f"regen-kora-{order.id}"
        metadata = dict(order.metadata_json or {})
        metadata["amount_fiat"] = str(quote.amount_fiat)
        metadata["currency_code"] = quote.currency_code

        secret = self._korapay_secret()
        if not secret:
            if self._is_production_environment():
                raise RegenCreationPaymentError("KoraPay secret key is not configured.")
            checkout = {
                "checkout_url": f"https://mock.korapay.local/{reference}",
                "payment_reference": reference,
                "mock_mode": True,
            }
        else:
            response = httpx.post(
                f"{self._korapay_base_url()}/charges/initialize",
                json={
                    "amount": self._normalize_korapay_amount(quote.amount_fiat),
                    "currency": quote.currency_code,
                    "reference": reference,
                    "customer": {
                        "email": actor.email,
                        "name": (actor.full_name or actor.username or actor.email).strip(),
                    },
                    "narration": f"GTEX regen request {order.id}",
                    "merchant_bears_cost": True,
                    "metadata": {
                        "regen_creation_order_id": order.id,
                        "request_type": order.request_type.value,
                    },
                },
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, dict) or not data.get("checkout_url"):
                raise RegenCreationPaymentError("KoraPay did not return a checkout URL.")
            data["mock_mode"] = False
            checkout = data

        order.amount_minor = self._normalize_korapay_amount(quote.amount_fiat)
        order.currency = quote.currency_code
        order.payment_provider = "korapay"
        order.payment_reference = str(checkout.get("payment_reference") or checkout.get("reference") or reference)
        metadata["payment_link"] = str(checkout.get("checkout_url") or "")
        metadata["mock_payment"] = bool(checkout.get("mock_mode", False))
        metadata["korapay_initialize"] = self._json_safe(checkout)
        order.metadata_json = metadata

    def _verify_and_mark_korapay_paid(self, order: RegenCreationOrder) -> None:
        if not order.payment_reference:
            raise RegenCreationPaymentError("KoraPay payment has not been initialized for this order.")
        verification_payload = self._verify_korapay_transaction(reference=order.payment_reference)
        data = verification_payload.get("data") if isinstance(verification_payload, dict) else None
        if not isinstance(data, dict):
            raise RegenCreationPaymentError("KoraPay returned an invalid verification payload.")

        payment_status = str(data.get("status") or data.get("transaction_status") or "").strip().lower()
        if payment_status in {"pending", "processing"}:
            raise RegenCreationPaymentError("Payment is still pending confirmation.")
        if payment_status not in {"success", "successful", "completed"}:
            order.status = RegenCreationOrderStatus.FAILED
            self.session.flush()
            raise RegenCreationPaymentError("Payment has not been completed successfully.")

        expected_amount = self._normalize_amount((order.metadata_json or {}).get("amount_fiat") or Decimal("0.0000"))
        paid_amount = self._normalize_amount(data.get("amount") or Decimal("0.0000"))
        if expected_amount > Decimal("0.0000") and paid_amount != expected_amount:
            order.status = RegenCreationOrderStatus.FAILED
            self.session.flush()
            raise RegenCreationPaymentError("Verified payment amount does not match the initiated request.")

        metadata = dict(order.metadata_json or {})
        metadata["korapay_verify"] = self._json_safe(verification_payload)
        order.metadata_json = metadata
        order.payment_provider = "korapay"
        order.payment_reference = str(data.get("payment_reference") or data.get("reference") or order.payment_reference)
        order.status = RegenCreationOrderStatus.PAID
        order.paid_at = order.paid_at or utcnow()
        self.session.flush()

    def _generate_order(self, *, order: RegenCreationOrder, actor: User) -> RegenCreationOrderView:
        if order.generated_player_id and order.generated_regen_profile_id:
            order.status = RegenCreationOrderStatus.GENERATED
            order.generated_at = order.generated_at or utcnow()
            self.session.flush()
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
            rng=Random(order.id),
            owner_context=owner_context,
            owner_son_request=owner_request,
        )
        generated_regen = generated.regens[0]
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
            market_value_eur=float(generated_regen.current_gsi) * 12_500.0,
            profile_completeness_score=0.98,
            is_tradable=True,
            dna_profile=dict(generated_regen.metadata.get("dna_profile") or {}),
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
                "visual_profile": generated_regen.metadata.get("visual_profile", {}),
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
            current_gsi=generated_regen.current_gsi,
            current_ability_range_json={
                "minimum": generated_regen.current_ability_range.minimum,
                "maximum": generated_regen.current_ability_range.maximum,
            },
            potential_range_json={
                "minimum": generated_regen.potential_range.minimum,
                "maximum": generated_regen.potential_range.maximum,
            },
            scout_confidence=generated_regen.scout_confidence,
            generation_source="requested_son",
            is_special_lineage=generated_regen.is_special_lineage,
            status=generated_regen.status,
            club_quality_score=generated_regen.club_quality_score,
            metadata_json=dict(generated_regen.metadata),
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

        visual_profile = dict(generated_regen.metadata.get("visual_profile") or {})
        self.session.add(
            RegenVisualProfile(
                regen_profile_id=regen.id,
                portrait_seed=str(visual_profile.get("portrait_seed", generated_regen.regen_id)),
                skin_tone=visual_profile.get("skin_tone"),
                hair_profile=visual_profile.get("hair_profile"),
                accessory_profile_json={},
                kit_style=visual_profile.get("kit_style"),
                metadata_json={"request_son_order_id": order.id},
            )
        )

        lineage_payload = (
            generated_regen.metadata.get("lineage") if isinstance(generated_regen.metadata, dict) else None
        )
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
        customization: dict[str, object] = {}
        if order.requested_name:
            customization["name"] = order.requested_name
        if order.requested_position:
            customization["position"] = order.requested_position
        if order.requested_country_code:
            customization["country_code"] = order.requested_country_code
        return customization

    def _target_country_code(self, *, order: RegenCreationOrder, club: ClubProfile, parent_player: Player) -> str:
        if order.requested_country_code:
            return order.requested_country_code.strip().upper()
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
    ) -> RegenCreationParentPlayerView:
        return RegenCreationParentPlayerView(
            player_id=player.id,
            full_name=player.full_name,
            position=player.position or player.normalized_position,
            country_code=self._country_code(country),
            country_name=country.name if country is not None else None,
            club_id=club.id,
            club_name=club.club_name,
        )

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
        return RegenCreationGeneratedPlayerView(
            player_id=player.id,
            regen_profile_id=regen.id,
            full_name=player.full_name,
            age=self._calculate_age(player.date_of_birth),
            position=regen.primary_position,
            country_code=self._country_code(country),
            country_name=country.name if country is not None else None,
            club_id=club.id if club is not None else None,
            club_name=club.club_name if club is not None else None,
            current_rating=int(regen.current_gsi),
            potential_rating=int(potential.get("maximum") or regen.current_gsi),
            card_id=regen.linked_unique_card_id,
        )

    def _order_view(self, order: RegenCreationOrder) -> RegenCreationOrderView:
        metadata = dict(order.metadata_json or {})
        return RegenCreationOrderView(
            id=order.id,
            user_id=order.user_id,
            club_id=order.club_id,
            request_type=order.request_type.value,
            parent_player_id=order.parent_player_id,
            requested_name=order.requested_name,
            requested_country_code=order.requested_country_code,
            requested_position=order.requested_position,
            amount_coin=self._normalize_amount(order.amount_coin),
            amount_minor=order.amount_minor,
            currency=order.currency,
            payment_method=order.payment_method.value,
            payment_provider=order.payment_provider,
            payment_reference=order.payment_reference,
            status=order.status.value,
            generated_player_id=order.generated_player_id,
            generated_regen_profile_id=order.generated_regen_profile_id,
            payment_link=str(metadata.get("payment_link") or "") or None,
            mock_payment=bool(metadata.get("mock_payment", False)),
            created_at=order.created_at,
            updated_at=order.updated_at,
            paid_at=order.paid_at,
            generated_at=order.generated_at,
            generated_player=self._generated_player_view(order),
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
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _normalize_korapay_amount(value: Decimal | int | float | str) -> int:
        return int((Decimal(str(value)) * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))

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

    @staticmethod
    def _korapay_secret() -> str | None:
        for name in ("GTE_KORAPAY_SECRET_KEY", "KORAPAY_SECRET_KEY"):
            secret = os.getenv(name)
            if secret and secret.strip():
                return secret.strip()
        return None

    @staticmethod
    def _korapay_base_url() -> str:
        raw_value = os.getenv("GTE_KORAPAY_BASE_URL") or os.getenv("KORAPAY_BASE_URL")
        if raw_value and raw_value.strip():
            return raw_value.strip().rstrip("/")
        return KORAPAY_BASE_URL

    @staticmethod
    def _is_production_environment() -> bool:
        environment = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
        return environment in {"production", "prod", "release"}

    def _verify_korapay_transaction(self, *, reference: str) -> dict[str, Any]:
        secret = self._korapay_secret()
        if not secret:
            raise RegenCreationPaymentError("KoraPay secret key is not configured.")
        normalized_reference = str(reference).strip()
        if not normalized_reference:
            raise RegenCreationPaymentError("KoraPay transaction reference is missing.")

        response = httpx.get(
            f"{self._korapay_base_url()}/charges/{normalized_reference}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RegenCreationPaymentError("KoraPay verification failed.")
        return payload


__all__ = [
    "RegenCreationConflictError",
    "RegenCreationError",
    "RegenCreationNotFoundError",
    "RegenCreationPaymentError",
    "RegenCreationPermissionError",
    "RegenCreationService",
    "RegenCreationValidationError",
]
