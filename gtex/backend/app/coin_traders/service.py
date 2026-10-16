from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.coin_trader import (
    CoinTradeDirection,
    CoinTradeOrder,
    CoinTradeOrderStatus,
    CoinTraderProfile,
    CoinTraderProfileStatus,
    CoinTraderRate,
)
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.notifications.service import NotificationEventMatrixService
from app.wallets.service import LedgerPosting, WalletService
from app.coin_traders.governance import CoinTraderPricingGovernanceService
from app.coin_traders.schemas import (
    CoinTraderAdminLiquidityRequest,
    CoinTraderAdminLiquidityTransferView,
    CoinTradeAdminResolutionRequest,
    CoinTradeDisputeRequest,
    CoinTradeOrderCreateRequest,
    CoinTradeOrderView,
    CoinTradeProofRequest,
    CoinTraderAdminDecisionRequest,
    CoinTraderAdminRejectRequest,
    CoinTraderProfileCreateRequest,
    CoinTraderProfileUpdateRequest,
    CoinTraderProfileView,
    CoinTraderRateUpsertRequest,
    CoinTraderRateView,
)


class CoinTraderError(Exception):
    """Base coin trader error."""


class CoinTraderNotFoundError(CoinTraderError):
    """Raised when a coin trader resource is missing."""


class CoinTraderPermissionError(CoinTraderError):
    """Raised when a user cannot operate a trader resource."""


class CoinTraderValidationError(CoinTraderError):
    """Raised when a coin trader action is invalid."""


@dataclass(slots=True)
class CoinTraderService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)

    def list_traders(
        self,
        *,
        country_code: str | None = None,
        coin_unit: LedgerUnit | None = None,
        approved_only: bool = True,
    ) -> list[CoinTraderProfileView]:
        statement = select(CoinTraderProfile).order_by(
            CoinTraderProfile.tier.desc(),
            CoinTraderProfile.completion_rate.desc(),
            CoinTraderProfile.updated_at.desc(),
        )
        if approved_only:
            statement = statement.where(CoinTraderProfile.status == CoinTraderProfileStatus.APPROVED.value)
        if country_code:
            statement = statement.where(CoinTraderProfile.country_code == country_code.upper())
        profiles = list(self.session.scalars(statement).all())
        if coin_unit is not None:
            profiles = [
                profile
                for profile in profiles
                if any(rate.coin_unit == coin_unit and rate.is_active for rate in self._rates_for_profile(profile.id))
            ]
        return [self.to_profile_view(profile) for profile in profiles]

    def get_profile(self, profile_id: str) -> CoinTraderProfileView:
        profile = self._require_profile(profile_id)
        if profile.status != CoinTraderProfileStatus.APPROVED.value:
            raise CoinTraderNotFoundError("Approved coin trader profile was not found.")
        return self.to_profile_view(profile)

    def get_my_profile(self, actor: User) -> CoinTraderProfileView:
        profile = self.session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == actor.id))
        if profile is None:
            raise CoinTraderNotFoundError("Coin trader profile was not found for this user.")
        return self.to_profile_view(profile)

    def create_or_update_profile(
        self, payload: CoinTraderProfileCreateRequest, *, actor: User
    ) -> CoinTraderProfileView:
        profile = self.session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == actor.id))
        if profile is None:
            profile = CoinTraderProfile(
                user_id=actor.id,
                display_name=payload.display_name,
                country_code=payload.country_code.upper() if payload.country_code else None,
                status=CoinTraderProfileStatus.APPLIED.value,
                terms_json=dict(payload.terms),
                payment_methods_json=list(payload.payment_methods),
                bank_accounts_json=list(payload.bank_accounts),
                metadata_json=dict(payload.metadata_json),
            )
            self.session.add(profile)
        else:
            profile.display_name = payload.display_name
            profile.country_code = payload.country_code.upper() if payload.country_code else None
            profile.terms_json = dict(payload.terms)
            profile.payment_methods_json = list(payload.payment_methods)
            profile.bank_accounts_json = list(payload.bank_accounts)
            profile.metadata_json = dict(payload.metadata_json)
            if profile.status == CoinTraderProfileStatus.REJECTED.value:
                profile.status = CoinTraderProfileStatus.APPLIED.value
        self.session.commit()
        self.session.refresh(profile)
        return self.to_profile_view(profile)

    def update_my_profile(self, payload: CoinTraderProfileUpdateRequest, *, actor: User) -> CoinTraderProfileView:
        profile = self._require_profile_for_user(actor)
        if payload.display_name is not None:
            profile.display_name = payload.display_name
        if payload.country_code is not None:
            profile.country_code = payload.country_code.upper()
        if payload.terms is not None:
            profile.terms_json = dict(payload.terms)
        if payload.payment_methods is not None:
            profile.payment_methods_json = list(payload.payment_methods)
        if payload.bank_accounts is not None:
            profile.bank_accounts_json = list(payload.bank_accounts)
        if payload.metadata_json is not None:
            profile.metadata_json = dict(payload.metadata_json)
        self.session.commit()
        self.session.refresh(profile)
        return self.to_profile_view(profile)

    def upsert_rate(self, payload: CoinTraderRateUpsertRequest, *, actor: User) -> CoinTraderRateView:
        profile = self._require_approved_profile_for_user(actor)
        governance = CoinTraderPricingGovernanceService(self.session)
        result = governance.evaluate_values(
            coin_unit=payload.coin_unit,
            buy_rate_fiat=payload.buy_rate_fiat,
            sell_rate_fiat=payload.sell_rate_fiat,
        )
        try:
            governance.block_if_invalid(
                result=result,
                actor=actor,
                trader_profile=profile,
                proposed_rate_payload={
                    "coin_unit": payload.coin_unit.value,
                    "fiat_currency": payload.fiat_currency.upper(),
                    "buy_rate_fiat": str(payload.buy_rate_fiat),
                    "sell_rate_fiat": str(payload.sell_rate_fiat),
                },
                action="upsert",
            )
        except ValueError as exc:
            raise CoinTraderValidationError(str(exc)) from exc
        rate = self.session.scalar(
            select(CoinTraderRate).where(
                CoinTraderRate.trader_profile_id == profile.id,
                CoinTraderRate.coin_unit == payload.coin_unit,
                CoinTraderRate.fiat_currency == payload.fiat_currency.upper(),
            )
        )
        if rate is None:
            rate = CoinTraderRate(
                trader_profile_id=profile.id,
                coin_unit=payload.coin_unit,
                fiat_currency=payload.fiat_currency.upper(),
            )
            self.session.add(rate)
        rate.buy_rate_fiat = payload.buy_rate_fiat
        rate.sell_rate_fiat = payload.sell_rate_fiat
        rate.min_coin_amount = payload.min_coin_amount
        rate.max_coin_amount = payload.max_coin_amount
        rate.available_liquidity = payload.available_liquidity
        rate.is_active = payload.is_active
        rate.metadata_json = dict(payload.metadata_json)
        self.session.flush()
        profile.liquidity_snapshot_json = self._liquidity_snapshot(profile.id)
        self.session.commit()
        self.session.refresh(rate)
        return self.to_rate_view(rate)

    def create_order(self, payload: CoinTradeOrderCreateRequest, *, actor: User) -> CoinTradeOrderView:
        if payload.idempotency_key:
            existing = self.session.scalar(
                select(CoinTradeOrder).where(CoinTradeOrder.idempotency_key == payload.idempotency_key)
            )
            if existing is not None:
                if existing.user_id != actor.id:
                    raise CoinTraderValidationError("Idempotency key is already used by another order.")
                return self.to_order_view(existing)
        profile = self._require_profile(payload.trader_profile_id)
        if profile.status != CoinTraderProfileStatus.APPROVED.value:
            raise CoinTraderValidationError("Coin trader is not approved for orders.")
        if profile.user_id == actor.id:
            raise CoinTraderValidationError("Traders cannot create orders against their own desk.")
        direction = self._direction_value(payload.direction)
        rate = self._active_rate(profile.id, payload.coin_unit, payload.fiat_currency)
        governance = CoinTraderPricingGovernanceService(self.session)
        result = governance.evaluate_rate(rate)
        try:
            governance.block_if_invalid(
                result=result,
                actor=actor,
                trader_profile=profile,
                proposed_rate_payload={
                    "coin_unit": rate.coin_unit.value,
                    "fiat_currency": rate.fiat_currency,
                    "buy_rate_fiat": str(rate.buy_rate_fiat),
                    "sell_rate_fiat": str(rate.sell_rate_fiat),
                    "order_coin_amount": str(payload.coin_amount),
                },
                action="order",
            )
        except ValueError as exc:
            raise CoinTraderValidationError(str(exc)) from exc
        quoted_rate = rate.sell_rate_fiat if direction == CoinTradeDirection.USER_BUYS.value else rate.buy_rate_fiat
        if quoted_rate <= Decimal("0"):
            raise CoinTraderValidationError("Coin trader rate is not available.")
        if payload.coin_amount < rate.min_coin_amount:
            raise CoinTraderValidationError("Order is below the trader minimum.")
        if rate.max_coin_amount > Decimal("0") and payload.coin_amount > rate.max_coin_amount:
            raise CoinTraderValidationError("Order exceeds the trader maximum.")
        if (
            direction == CoinTradeDirection.USER_BUYS.value
            and self._effective_available_liquidity(rate) < payload.coin_amount
        ):
            raise CoinTraderValidationError("Trader liquidity is below requested amount.")
        fiat_total = payload.coin_amount * quoted_rate
        order = CoinTradeOrder(
            trader_profile_id=profile.id,
            user_id=actor.id,
            direction=direction,
            coin_unit=payload.coin_unit,
            coin_amount=payload.coin_amount,
            quoted_rate_fiat=quoted_rate,
            fiat_total=fiat_total,
            fiat_currency=payload.fiat_currency.upper(),
            status=CoinTradeOrderStatus.CREATED.value,
            payment_method=payload.payment_method,
            idempotency_key=payload.idempotency_key,
            terms_snapshot_json=dict(profile.terms_json or {}),
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return self.to_order_view(order)

    def list_orders(self, *, actor: User, trader: bool = False) -> list[CoinTradeOrderView]:
        if trader:
            profile = self._require_profile_for_user(actor)
            statement = select(CoinTradeOrder).where(CoinTradeOrder.trader_profile_id == profile.id)
        else:
            statement = select(CoinTradeOrder).where(CoinTradeOrder.user_id == actor.id)
        statement = statement.order_by(CoinTradeOrder.created_at.desc())
        return [self.to_order_view(order) for order in self.session.scalars(statement).all()]

    def accept_order(self, order_id: str, *, actor: User) -> CoinTradeOrderView:
        order = self._require_order(order_id)
        profile = self._require_approved_profile(order.trader_profile_id)
        if profile.user_id != actor.id:
            raise CoinTraderPermissionError("Only the selected trader can accept this order.")
        if order.status != CoinTradeOrderStatus.CREATED.value:
            raise CoinTraderValidationError("Only created orders can be accepted.")
        trader_user = self._require_user(profile.user_id)
        order_user = self._require_user(order.user_id)
        escrow_owner = trader_user if order.direction == CoinTradeDirection.USER_BUYS.value else order_user
        entries = self.wallet_service.reserve_order_funds(
            self.session,
            user=escrow_owner,
            amount=order.coin_amount,
            unit=order.coin_unit,
            reference=f"coin-trade:{order.id}:escrow",
            description="Coin trader order escrow lock",
            source_tag=LedgerSourceTag.COIN_TRADER_ESCROW_LOCK,
        )
        now = utcnow()
        order.escrow_owner_user_id = escrow_owner.id
        order.status = CoinTradeOrderStatus.PAYMENT_PENDING.value
        order.accepted_at = now
        order.payment_window_expires_at = now + timedelta(minutes=45)
        order.ledger_refs_json = {
            **dict(order.ledger_refs_json or {}),
            "escrow_lock_entry_ids": [entry.id for entry in entries],
        }
        self.session.commit()
        self.session.refresh(order)
        self._publish_order_matrix_notifications(
            order,
            event_key="coin_trader_order_accepted",
            target_user_ids=[order.user_id],
            message="A coin trader accepted your order.",
        )
        self._publish_order_matrix_notifications(
            order,
            event_key="escrow_locked",
            target_user_ids=[order.user_id, profile.user_id],
            message="Coin trader escrow has been locked for this order.",
        )
        return self.to_order_view(order)

    def submit_proof(self, order_id: str, payload: CoinTradeProofRequest, *, actor: User) -> CoinTradeOrderView:
        order = self._require_participating_order(order_id, actor)
        profile = self._require_profile(order.trader_profile_id)
        proof_submitter_user_id = (
            order.user_id if order.direction == CoinTradeDirection.USER_BUYS.value else profile.user_id
        )
        if actor.id != proof_submitter_user_id:
            raise CoinTraderPermissionError("Payment proof must be submitted by the fiat sender.")
        if order.status not in {CoinTradeOrderStatus.PAYMENT_PENDING.value, CoinTradeOrderStatus.PROOF_SUBMITTED.value}:
            raise CoinTraderValidationError("Payment proof can only be added while payment is pending.")
        order.status = CoinTradeOrderStatus.PROOF_SUBMITTED.value
        order.proof_submitted_at = utcnow()
        order.proof_json = {
            "proof_reference": payload.proof_reference,
            "proof_url": payload.proof_url,
            "note": payload.note,
            "submitted_by_user_id": actor.id,
        }
        self.session.commit()
        self.session.refresh(order)
        return self.to_order_view(order)

    def confirm_and_release(self, order_id: str, *, actor: User) -> CoinTradeOrderView:
        order = self._require_order(order_id)
        profile = self._require_approved_profile(order.trader_profile_id)
        confirmer_user_id = profile.user_id if order.direction == CoinTradeDirection.USER_BUYS.value else order.user_id
        if actor.id != confirmer_user_id:
            raise CoinTraderPermissionError("This order requires confirmation from the fiat receiver.")
        if order.status != CoinTradeOrderStatus.PROOF_SUBMITTED.value:
            raise CoinTraderValidationError("Order is not ready for release.")
        view = self._release_order(order, admin_actor=None, source_tag=LedgerSourceTag.COIN_TRADER_ESCROW_RELEASE)
        self._publish_order_matrix_notifications(
            order,
            event_key="payment_confirmed",
            target_user_ids=[order.user_id, profile.user_id],
            message="Coin trader payment has been confirmed.",
        )
        return view

    def cancel_order(self, order_id: str, *, actor: User) -> CoinTradeOrderView:
        order = self._require_participating_order(order_id, actor)
        if order.status == CoinTradeOrderStatus.CREATED.value:
            order.status = CoinTradeOrderStatus.CANCELLED.value
            order.cancelled_at = utcnow()
            self.session.commit()
            self.session.refresh(order)
            return self.to_order_view(order)
        if order.status not in {CoinTradeOrderStatus.PAYMENT_PENDING.value, CoinTradeOrderStatus.PROOF_SUBMITTED.value}:
            raise CoinTraderValidationError("Order cannot be cancelled from its current state.")
        return self._refund_order(order, actor=actor, admin=False)

    def dispute_order(self, order_id: str, payload: CoinTradeDisputeRequest, *, actor: User) -> CoinTradeOrderView:
        order = self._require_participating_order(order_id, actor)
        if order.status not in {CoinTradeOrderStatus.PAYMENT_PENDING.value, CoinTradeOrderStatus.PROOF_SUBMITTED.value}:
            raise CoinTraderValidationError("Only active escrow orders can be disputed.")
        order.status = CoinTradeOrderStatus.DISPUTED.value
        order.disputed_at = utcnow()
        order.metadata_json = {
            **dict(order.metadata_json or {}),
            "dispute": {"reason": payload.reason, "evidence": payload.evidence, "opened_by_user_id": actor.id},
        }
        profile = self._require_profile(order.trader_profile_id)
        self.session.flush()
        self._refresh_profile_metrics(profile)
        self.session.commit()
        self.session.refresh(order)
        self._publish_order_matrix_notifications(
            order,
            event_key="dispute_opened",
            target_user_ids=[order.user_id, profile.user_id],
            message="A coin trader dispute has been opened.",
            metadata={"reason": payload.reason},
        )
        return self.to_order_view(order)

    def approve_trader(
        self,
        profile_id: str,
        payload: CoinTraderAdminDecisionRequest,
        *,
        admin: User,
    ) -> CoinTraderProfileView:
        profile = self._require_profile(profile_id)
        if profile.user_id == admin.id:
            raise CoinTraderValidationError("Admins cannot approve their own trader profile.")
        user = self._require_user(profile.user_id)
        now = utcnow()
        profile.status = CoinTraderProfileStatus.APPROVED.value
        profile.tier = str(payload.tier.value if hasattr(payload.tier, "value") else payload.tier)
        profile.approved_by_user_id = admin.id
        profile.approved_at = now
        profile.rejected_at = None
        profile.frozen_at = None
        profile.metadata_json = {**dict(profile.metadata_json or {}), "approval_note": payload.note or ""}
        user.role = UserRole.COIN_TRADER
        self.session.commit()
        self.session.refresh(profile)
        return self.to_profile_view(profile)

    def reject_trader(
        self,
        profile_id: str,
        payload: CoinTraderAdminRejectRequest,
        *,
        admin: User,
    ) -> CoinTraderProfileView:
        del admin
        profile = self._require_profile(profile_id)
        profile.status = CoinTraderProfileStatus.REJECTED.value
        profile.rejected_at = utcnow()
        profile.metadata_json = {**dict(profile.metadata_json or {}), "rejection_note": payload.note or ""}
        self.session.commit()
        self.session.refresh(profile)
        return self.to_profile_view(profile)

    def freeze_trader(self, profile_id: str, *, admin: User, note: str | None = None) -> CoinTraderProfileView:
        del admin
        profile = self._require_profile(profile_id)
        profile.status = CoinTraderProfileStatus.FROZEN.value
        profile.frozen_at = utcnow()
        profile.metadata_json = {**dict(profile.metadata_json or {}), "freeze_note": note or ""}
        self.session.commit()
        self.session.refresh(profile)
        return self.to_profile_view(profile)

    def admin_list_profiles(self) -> list[CoinTraderProfileView]:
        statement = select(CoinTraderProfile).order_by(CoinTraderProfile.created_at.desc())
        return [self.to_profile_view(profile) for profile in self.session.scalars(statement).all()]

    def admin_list_orders(self) -> list[CoinTradeOrderView]:
        statement = select(CoinTradeOrder).order_by(CoinTradeOrder.created_at.desc())
        return [self.to_order_view(order) for order in self.session.scalars(statement).all()]

    def admin_issue_liquidity(
        self,
        profile_id: str,
        payload: CoinTraderAdminLiquidityRequest,
        *,
        admin: User,
    ) -> CoinTraderAdminLiquidityTransferView:
        return self._admin_transfer_liquidity(profile_id, payload, admin=admin, flow="issue")

    def admin_redeem_liquidity(
        self,
        profile_id: str,
        payload: CoinTraderAdminLiquidityRequest,
        *,
        admin: User,
    ) -> CoinTraderAdminLiquidityTransferView:
        return self._admin_transfer_liquidity(profile_id, payload, admin=admin, flow="redeem")

    def admin_resolve_order(
        self,
        order_id: str,
        payload: CoinTradeAdminResolutionRequest,
        *,
        admin: User,
    ) -> CoinTradeOrderView:
        order = self._require_order(order_id)
        if order.status not in {
            CoinTradeOrderStatus.PAYMENT_PENDING.value,
            CoinTradeOrderStatus.PROOF_SUBMITTED.value,
            CoinTradeOrderStatus.DISPUTED.value,
        }:
            raise CoinTraderValidationError("Only active or disputed escrow orders can be resolved.")
        if payload.resolution == "release":
            view = self._release_order(
                order, admin_actor=admin, source_tag=LedgerSourceTag.COIN_TRADER_ADMIN_RESOLUTION
            )
            order.status = CoinTradeOrderStatus.ADMIN_RELEASED.value
        else:
            view = self._refund_order(order, actor=admin, admin=True)
            order.status = CoinTradeOrderStatus.ADMIN_REFUNDED.value
        order.metadata_json = {**dict(order.metadata_json or {}), "admin_resolution_note": payload.note or ""}
        self.session.commit()
        self.session.refresh(order)
        return self.to_order_view(order) if view.id == order.id else view

    def _release_order(
        self,
        order: CoinTradeOrder,
        *,
        admin_actor: User | None,
        source_tag: LedgerSourceTag,
    ) -> CoinTradeOrderView:
        profile = self._require_profile(order.trader_profile_id)
        escrow_owner = self._require_user(order.escrow_owner_user_id or "")
        destination_user = self._require_user(
            order.user_id if order.direction == CoinTradeDirection.USER_BUYS.value else profile.user_id
        )
        escrow_account = self.wallet_service.get_user_escrow_account(self.session, escrow_owner, order.coin_unit)
        destination_account = self.wallet_service.get_user_account(self.session, destination_user, order.coin_unit)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-order.coin_amount),
                LedgerPosting(account=destination_account, amount=order.coin_amount),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=source_tag,
            transaction_type=(
                LedgerTransactionType.TRADE_BUY
                if order.direction == CoinTradeDirection.USER_BUYS.value
                else LedgerTransactionType.TRADE_SELL
            ),
            reference=f"coin-trade:{order.id}:release",
            description="Coin trader escrow release",
            actor=admin_actor or destination_user,
            metadata={"order_id": order.id, "direction": order.direction},
        )
        order.status = CoinTradeOrderStatus.RELEASED.value
        order.released_at = utcnow()
        order.ledger_refs_json = {
            **dict(order.ledger_refs_json or {}),
            "release_entry_ids": [entry.id for entry in entries],
        }
        self.session.flush()
        self._refresh_profile_metrics(profile)
        self.session.commit()
        self.session.refresh(order)
        self._publish_order_matrix_notifications(
            order,
            event_key="coins_released",
            target_user_ids=[order.user_id, profile.user_id],
            message="Coin trader escrow has been released.",
        )
        return self.to_order_view(order)

    def _refund_order(self, order: CoinTradeOrder, *, actor: User, admin: bool) -> CoinTradeOrderView:
        escrow_owner = self._require_user(order.escrow_owner_user_id or "")
        entries = self.wallet_service.release_reserved_funds(
            self.session,
            user=escrow_owner,
            amount=order.coin_amount,
            unit=order.coin_unit,
            reference=f"coin-trade:{order.id}:refund",
            description="Coin trader escrow refund",
            source_tag=(
                LedgerSourceTag.COIN_TRADER_ADMIN_RESOLUTION if admin else LedgerSourceTag.COIN_TRADER_ESCROW_REFUND
            ),
        )
        order.status = CoinTradeOrderStatus.ADMIN_REFUNDED.value if admin else CoinTradeOrderStatus.REFUNDED.value
        order.cancelled_at = utcnow()
        order.ledger_refs_json = {
            **dict(order.ledger_refs_json or {}),
            "refund_entry_ids": [entry.id for entry in entries],
            "refund_actor_user_id": actor.id,
        }
        profile = self._require_profile(order.trader_profile_id)
        self.session.flush()
        self._refresh_profile_metrics(profile)
        self.session.commit()
        self.session.refresh(order)
        return self.to_order_view(order)

    def _admin_transfer_liquidity(
        self,
        profile_id: str,
        payload: CoinTraderAdminLiquidityRequest,
        *,
        admin: User,
        flow: str,
    ) -> CoinTraderAdminLiquidityTransferView:
        profile = self._require_approved_profile(profile_id)
        trader_user = self._require_user(profile.user_id)
        amount = self.wallet_service._normalize_amount(payload.amount)
        if amount <= Decimal("0.0000"):
            raise CoinTraderValidationError("Liquidity amount must be positive.")

        trader_account = self.wallet_service.get_user_account(self.session, trader_user, payload.coin_unit)
        platform_account = self.wallet_service.ensure_market_liquidity_account(self.session, payload.coin_unit)
        if flow == "issue":
            postings = [
                LedgerPosting(account=platform_account, amount=-amount),
                LedgerPosting(account=trader_account, amount=amount),
            ]
            transaction_type = LedgerTransactionType.TRADE_BUY
            description = "Admin issued coin trader liquidity"
        elif flow == "redeem":
            available_balance = self.wallet_service.get_balance(self.session, trader_account)
            if available_balance < amount:
                raise CoinTraderValidationError("Trader wallet balance is below redemption amount.")
            postings = [
                LedgerPosting(account=trader_account, amount=-amount),
                LedgerPosting(account=platform_account, amount=amount),
            ]
            transaction_type = LedgerTransactionType.TRADE_SELL
            description = "Admin redeemed coin trader liquidity"
        else:
            raise CoinTraderValidationError("Unsupported liquidity flow.")

        reference = payload.reference or f"coin-trader:{profile.id}:liquidity:{flow}"
        idempotency_key = (
            f"coin-trader-liquidity:{profile.id}:{flow}:{payload.idempotency_key}" if payload.idempotency_key else None
        )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.COIN_TRADER_ADMIN_RESOLUTION,
            transaction_type=transaction_type,
            reference=reference,
            description=description,
            external_reference=reference,
            actor=admin,
            idempotency_key=idempotency_key,
            metadata={
                "coin_trader_liquidity_flow": flow,
                "trader_profile_id": profile.id,
                "trader_user_id": trader_user.id,
                "coin_unit": payload.coin_unit.value,
                "amount": str(amount),
                "fiat_total": str(payload.fiat_total) if payload.fiat_total is not None else None,
                "note": payload.note or "",
                "metadata_json": dict(payload.metadata_json),
            },
        )
        self._assert_admin_liquidity_idempotency_matches(
            entries=entries,
            profile=profile,
            payload=payload,
            flow=flow,
            amount=amount,
            reference=reference,
        )
        profile.liquidity_snapshot_json = self._liquidity_snapshot(profile.id)
        profile.metadata_json = {
            **dict(profile.metadata_json or {}),
            "last_admin_liquidity_flow": {
                "flow": flow,
                "coin_unit": payload.coin_unit.value,
                "amount": str(amount),
                "reference": reference,
                "admin_user_id": admin.id,
            },
        }
        self.session.commit()
        self.session.refresh(profile)
        return CoinTraderAdminLiquidityTransferView(
            trader_profile_id=profile.id,
            trader_user_id=trader_user.id,
            flow=flow,  # type: ignore[arg-type]
            coin_unit=payload.coin_unit,
            amount=amount,
            reference=reference,
            transaction_id=entries[0].transaction_id if entries else None,
            ledger_entry_ids=[entry.id for entry in entries],
            available_balance=self._trader_available_balance(profile, payload.coin_unit),
            liquidity_snapshot=self._liquidity_snapshot(profile.id),
        )

    def _assert_admin_liquidity_idempotency_matches(
        self,
        *,
        entries: list[LedgerEntry],
        profile: CoinTraderProfile,
        payload: CoinTraderAdminLiquidityRequest,
        flow: str,
        amount: Decimal,
        reference: str,
    ) -> None:
        if not payload.idempotency_key or not entries:
            return
        transaction = entries[0].transaction
        metadata = dict(transaction.metadata_json or {}) if transaction is not None else {}
        expected = {
            "coin_trader_liquidity_flow": flow,
            "trader_profile_id": profile.id,
            "coin_unit": payload.coin_unit.value,
            "amount": str(amount),
        }
        mismatched = any(metadata.get(key) != value for key, value in expected.items())
        if mismatched or transaction.reference != reference:
            raise CoinTraderValidationError("Liquidity idempotency key was already used for a different transfer.")

    def _require_participating_order(self, order_id: str, actor: User) -> CoinTradeOrder:
        order = self._require_order(order_id)
        profile = self._require_profile(order.trader_profile_id)
        if actor.id not in {order.user_id, profile.user_id}:
            raise CoinTraderPermissionError("Only order participants can perform this action.")
        return order

    def _publish_order_matrix_notifications(
        self,
        order: CoinTradeOrder,
        *,
        event_key: str,
        target_user_ids: list[str | None],
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if not self._notification_tables_available():
            return
        normalized_targets = [user_id for user_id in target_user_ids if user_id]
        if not normalized_targets:
            return
        records = NotificationEventMatrixService(self.session).publish_event(
            event_key=event_key,
            target_user_ids=normalized_targets,
            resource_id=order.id,
            message=message,
            metadata_json={
                "order_id": order.id,
                "trader_profile_id": order.trader_profile_id,
                "direction": order.direction,
                "coin_unit": str(order.coin_unit.value if hasattr(order.coin_unit, "value") else order.coin_unit),
                "coin_amount": str(order.coin_amount),
                "route": "/app/coin-traders",
                **(metadata or {}),
            },
        )
        if records:
            self.session.commit()

    def _notification_tables_available(self) -> bool:
        inspector = inspect(self.session.connection())
        return all(
            inspector.has_table(table_name)
            for table_name in ("notification_records", "notification_preferences", "users")
        )

    def _require_order(self, order_id: str) -> CoinTradeOrder:
        order = self.session.get(CoinTradeOrder, order_id)
        if order is None:
            raise CoinTraderNotFoundError(f"Coin trader order {order_id} was not found.")
        return order

    def _require_profile(self, profile_id: str) -> CoinTraderProfile:
        profile = self.session.get(CoinTraderProfile, profile_id)
        if profile is None:
            raise CoinTraderNotFoundError(f"Coin trader profile {profile_id} was not found.")
        return profile

    def _require_profile_for_user(self, actor: User) -> CoinTraderProfile:
        profile = self.session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == actor.id))
        if profile is None:
            raise CoinTraderNotFoundError("Coin trader profile was not found for this user.")
        return profile

    def _require_approved_profile_for_user(self, actor: User) -> CoinTraderProfile:
        profile = self._require_profile_for_user(actor)
        if profile.status != CoinTraderProfileStatus.APPROVED.value or actor.role != UserRole.COIN_TRADER:
            raise CoinTraderPermissionError("Approved coin trader access is required.")
        return profile

    def _require_approved_profile(self, profile_id: str) -> CoinTraderProfile:
        profile = self._require_profile(profile_id)
        if profile.status != CoinTraderProfileStatus.APPROVED.value:
            raise CoinTraderPermissionError("Approved coin trader access is required.")
        return profile

    def _require_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise CoinTraderNotFoundError(f"User {user_id} was not found.")
        return user

    def _active_rate(self, profile_id: str, coin_unit: LedgerUnit, fiat_currency: str) -> CoinTraderRate:
        rate = self.session.scalar(
            select(CoinTraderRate).where(
                CoinTraderRate.trader_profile_id == profile_id,
                CoinTraderRate.coin_unit == coin_unit,
                CoinTraderRate.fiat_currency == fiat_currency.upper(),
                CoinTraderRate.is_active.is_(True),
            )
        )
        if rate is None:
            raise CoinTraderNotFoundError("Active trader rate was not found.")
        return rate

    def _rates_for_profile(self, profile_id: str) -> list[CoinTraderRate]:
        return list(
            self.session.scalars(
                select(CoinTraderRate)
                .where(CoinTraderRate.trader_profile_id == profile_id)
                .order_by(CoinTraderRate.coin_unit, CoinTraderRate.fiat_currency)
            ).all()
        )

    def _liquidity_snapshot(self, profile_id: str) -> dict[str, object]:
        rates = self._rates_for_profile(profile_id)
        return {
            f"{rate.coin_unit.value}:{rate.fiat_currency}": {
                "available_liquidity": str(self._effective_available_liquidity(rate)),
                "claimed_available_liquidity": str(self.wallet_service._normalize_amount(rate.available_liquidity)),
                "buy_rate_fiat": str(rate.buy_rate_fiat),
                "sell_rate_fiat": str(rate.sell_rate_fiat),
            }
            for rate in rates
        }

    def _trader_available_balance(self, profile: CoinTraderProfile, unit: LedgerUnit) -> Decimal:
        account = self.session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.code == self.wallet_service._user_account_code(profile.user_id, unit)
            )
        )
        if account is None:
            return Decimal("0.0000")
        balance = self.wallet_service.get_balance(self.session, account)
        return max(balance, Decimal("0.0000"))

    def _effective_available_liquidity(self, rate: CoinTraderRate) -> Decimal:
        profile = self._require_profile(rate.trader_profile_id)
        claimed_liquidity = self.wallet_service._normalize_amount(rate.available_liquidity)
        return min(claimed_liquidity, self._trader_available_balance(profile, rate.coin_unit))

    def _refresh_profile_metrics(self, profile: CoinTraderProfile) -> None:
        orders = list(
            self.session.scalars(select(CoinTradeOrder).where(CoinTradeOrder.trader_profile_id == profile.id)).all()
        )
        completed_statuses = {CoinTradeOrderStatus.RELEASED.value, CoinTradeOrderStatus.ADMIN_RELEASED.value}
        terminal_statuses = completed_statuses | {
            CoinTradeOrderStatus.REFUNDED.value,
            CoinTradeOrderStatus.ADMIN_REFUNDED.value,
            CoinTradeOrderStatus.CANCELLED.value,
        }
        completed_orders = [order for order in orders if order.status in completed_statuses]
        terminal_orders = [order for order in orders if order.status in terminal_statuses]
        disputed_orders = [
            order
            for order in orders
            if order.disputed_at is not None or order.status == CoinTradeOrderStatus.DISPUTED.value
        ]
        profile.completed_volume_fiat = sum((order.fiat_total for order in completed_orders), Decimal("0.0000"))
        profile.completion_rate = (
            float((Decimal(len(completed_orders)) / Decimal(len(terminal_orders))) * Decimal("100"))
            if terminal_orders
            else 0.0
        )
        release_minutes: list[float] = []
        for order in completed_orders:
            if order.accepted_at is None or order.released_at is None:
                continue
            accepted_at = order.accepted_at
            released_at = order.released_at
            if accepted_at.tzinfo is None and released_at.tzinfo is not None:
                released_at = released_at.replace(tzinfo=None)
            elif accepted_at.tzinfo is not None and released_at.tzinfo is None:
                accepted_at = accepted_at.replace(tzinfo=None)
            release_minutes.append((released_at - accepted_at).total_seconds() / 60)
        profile.average_release_minutes = sum(release_minutes) / len(release_minutes) if release_minutes else 0.0
        profile.dispute_score = (
            float((Decimal(len(disputed_orders)) / Decimal(len(orders))) * Decimal("100")) if orders else 0.0
        )
        profile.liquidity_snapshot_json = self._liquidity_snapshot(profile.id)

    def _direction_value(self, direction: CoinTradeDirection | str) -> str:
        return direction.value if hasattr(direction, "value") else str(direction)

    def to_profile_view(self, profile: CoinTraderProfile) -> CoinTraderProfileView:
        return CoinTraderProfileView(
            id=profile.id,
            user_id=profile.user_id,
            display_name=profile.display_name,
            country_code=profile.country_code,
            status=profile.status,
            tier=profile.tier,
            verification_level=profile.verification_level,
            completion_rate=profile.completion_rate,
            average_release_minutes=profile.average_release_minutes,
            rating=profile.rating,
            completed_volume_fiat=profile.completed_volume_fiat,
            dispute_score=profile.dispute_score,
            terms=dict(profile.terms_json or {}),
            payment_methods=list(profile.payment_methods_json or []),
            bank_accounts=list(profile.bank_accounts_json or []),
            liquidity_snapshot=dict(profile.liquidity_snapshot_json or {}),
            rates=[self.to_rate_view(rate) for rate in self._rates_for_profile(profile.id)],
            metadata_json=dict(profile.metadata_json or {}),
        )

    def to_rate_view(self, rate: CoinTraderRate) -> CoinTraderRateView:
        governance_result = CoinTraderPricingGovernanceService(self.session).evaluate_rate(rate)
        return CoinTraderRateView(
            id=rate.id,
            trader_profile_id=rate.trader_profile_id,
            coin_unit=rate.coin_unit,
            fiat_currency=rate.fiat_currency,
            buy_rate_fiat=rate.buy_rate_fiat,
            sell_rate_fiat=rate.sell_rate_fiat,
            min_coin_amount=rate.min_coin_amount,
            max_coin_amount=rate.max_coin_amount,
            available_liquidity=self._effective_available_liquidity(rate),
            is_active=rate.is_active,
            spread_fiat=governance_result.spread_fiat,
            treasury_deposit_rate_fiat=governance_result.treasury_deposit_rate_fiat,
            treasury_withdrawal_rate_fiat=governance_result.treasury_withdrawal_rate_fiat,
            min_trader_buy_rate_fiat=governance_result.min_trader_buy_rate_fiat,
            max_trader_buy_rate_fiat=governance_result.max_trader_buy_rate_fiat,
            min_trader_sell_rate_fiat=governance_result.min_trader_sell_rate_fiat,
            max_trader_sell_rate_fiat=governance_result.max_trader_sell_rate_fiat,
            max_trader_spread_fiat=governance_result.max_trader_spread_fiat,
            governance_status=governance_result.governance_status,
            governance_reasons=list(governance_result.governance_reasons),
            metadata_json=dict(rate.metadata_json or {}),
        )

    def to_order_view(self, order: CoinTradeOrder) -> CoinTradeOrderView:
        return CoinTradeOrderView(
            id=order.id,
            trader_profile_id=order.trader_profile_id,
            user_id=order.user_id,
            direction=order.direction,
            coin_unit=order.coin_unit,
            coin_amount=order.coin_amount,
            quoted_rate_fiat=order.quoted_rate_fiat,
            fiat_total=order.fiat_total,
            fiat_currency=order.fiat_currency,
            status=order.status,
            escrow_owner_user_id=order.escrow_owner_user_id,
            idempotency_key=order.idempotency_key,
            payment_method=order.payment_method,
            payment_window_expires_at=order.payment_window_expires_at,
            accepted_at=order.accepted_at,
            proof_submitted_at=order.proof_submitted_at,
            released_at=order.released_at,
            cancelled_at=order.cancelled_at,
            disputed_at=order.disputed_at,
            proof=dict(order.proof_json or {}),
            terms_snapshot=dict(order.terms_snapshot_json or {}),
            ledger_refs=dict(order.ledger_refs_json or {}),
            metadata_json=dict(order.metadata_json or {}),
        )


__all__ = [
    "CoinTraderError",
    "CoinTraderNotFoundError",
    "CoinTraderPermissionError",
    "CoinTraderService",
    "CoinTraderValidationError",
]
