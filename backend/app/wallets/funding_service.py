from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.treasury import TreasurySettings
from app.models.user import User
from app.models.user_wallet import UserWallet, WalletTransactionRecord
from app.models.wallet import LedgerUnit
from app.policies.service import PolicyService
from app.treasury.service import TreasuryService
from app.wallets.constants import SUPPORTED_TOP_UP_PROVIDER_KEYS
from app.wallets.providers.base import CheckoutSession, PaymentVerification
from app.wallets.providers.registry import (
    get_live_provider_adapter,
    get_provider_adapter,
    korapay_enabled,
    paystack_enabled,
    provider_live_deposit_ready,
    provider_runtime_statuses,
)
from app.wallets.rail_service import WalletRailError, WalletRailService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
VERIFIED_COMPLIANCE_STATUS = "verified"


@dataclass(frozen=True, slots=True)
class WalletTopUpSession:
    reference: str
    payment_link: str
    amount: Decimal
    currency: str
    provider: str
    status: str
    mock_mode: bool = False


@dataclass(frozen=True, slots=True)
class WalletTopUpVerificationResult:
    wallet: UserWallet
    transaction: WalletTransactionRecord


class WalletFundingError(ValueError):
    pass


class WalletTopUpNotFoundError(WalletFundingError):
    pass


class WalletTopUpVerificationError(WalletFundingError):
    pass


@dataclass(slots=True)
class WalletFundingService:
    wallet_service: WalletService | None = None
    treasury_service: TreasuryService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.treasury_service is None:
            self.treasury_service = TreasuryService(wallet_service=self.wallet_service)

    def ensure_wallet(self, session: Session, user: User) -> UserWallet:
        self.wallet_service.ensure_default_accounts(session, user)
        wallet = session.scalar(select(UserWallet).where(UserWallet.user_id == user.id))
        if wallet is None:
            wallet = UserWallet(
                user_id=user.id,
                balance=Decimal("0.0000"),
                currency=LedgerUnit.COIN.value,
                compliance_status=VERIFIED_COMPLIANCE_STATUS,
            )
            session.add(wallet)
            session.flush()
        return wallet

    def get_wallet(self, session: Session, user: User) -> UserWallet:
        wallet = self.ensure_wallet(session, user)
        return self.sync_wallet_balance(session, user, wallet=wallet)

    def sync_wallet_balance(
        self,
        session: Session,
        user: User,
        *,
        wallet: UserWallet | None = None,
    ) -> UserWallet:
        wallet = wallet or self.ensure_wallet(session, user)
        summary = self.wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
        wallet.balance = summary.available_balance
        wallet.currency = summary.currency.value
        session.flush()
        return wallet

    def list_transactions(
        self,
        session: Session,
        user: User,
        *,
        limit: int = 50,
    ) -> list[WalletTransactionRecord]:
        self.ensure_wallet(session, user)
        return session.scalars(
            select(WalletTransactionRecord)
            .where(WalletTransactionRecord.user_id == user.id)
            .order_by(WalletTransactionRecord.created_at.desc(), WalletTransactionRecord.id.desc())
            .limit(limit)
        ).all()

    def assert_verified_for_trading(self, session: Session, user: User) -> None:
        wallet = self.ensure_wallet(session, user)
        if not self._is_verified(wallet.compliance_status):
            raise WalletFundingError("Trading is unavailable until wallet compliance is verified.")
        policy = PolicyService(session).get_country_policy_for_user(user=user)
        if not policy.market_trading_enabled:
            raise WalletFundingError(f"Trading is currently disabled for country policy '{policy.country_code}'.")

    def initiate_top_up(
        self,
        session: Session,
        user: User,
        *,
        amount: Decimal,
        input_unit: str = "coin",
        provider: str = "korapay",
        unit: LedgerUnit = LedgerUnit.COIN,
        callback_url: str | None = None,
        source_scope: str = "wallet",
        purchase_purpose: str = "wallet_top_up",
    ) -> WalletTopUpSession:
        normalized_provider = provider.strip().lower()
        if normalized_provider not in SUPPORTED_TOP_UP_PROVIDER_KEYS:
            raise WalletFundingError(
                "KoraPay and Paystack are the live automatic top-up providers. Manual transfer remains available."
            )
        if normalized_provider == "paystack" and not paystack_enabled():
            raise WalletFundingError("Paystack is unavailable. Set live Paystack credentials before accepting payments.")
        if normalized_provider == "korapay" and not korapay_enabled():
            raise WalletFundingError(
                "KoraPay requires live checkout and webhook credentials before it can accept deposits."
            )

        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise WalletFundingError("Top-up amount must be positive.")

        wallet = self.ensure_wallet(session, user)
        policy = PolicyService(session).get_country_policy_for_user(user=user)
        if not policy.deposits_enabled:
            raise WalletFundingError(f"Deposits are currently disabled for country policy '{policy.country_code}'.")

        settings = self.treasury_service.ensure_settings(session)
        rail_service = WalletRailService(session=session, wallet_service=self.wallet_service)
        try:
            order = rail_service.create_purchase_order(
                user=user,
                settings=settings,
                amount=normalized_amount,
                input_unit=input_unit,
                provider_key=normalized_provider,
                source_scope=source_scope,
                unit=unit,
                processor_mode="automatic_gateway",
                payout_channel="gateway",
                provider_reference=None,
                notes=purchase_purpose,
                purchase_purpose=purchase_purpose,
            )
        except WalletRailError as exc:
            raise WalletFundingError(str(exc)) from exc

        try:
            adapter = get_live_provider_adapter(normalized_provider)
            checkout_session: CheckoutSession = adapter.initialize_checkout(
                order_reference=order.reference,
                amount=order.amount_fiat,
                currency=order.currency_code,
                customer_email=user.email,
                customer_name=user.full_name or user.username or user.email,
                callback_url=callback_url,
                metadata={
                    "user_id": user.id,
                    "order_reference": order.reference,
                    "purchase_purpose": purchase_purpose,
                    "unit": unit.value,
                },
                narration=f"GTEX {order.reference}",
            )
        except (httpx.HTTPError, ValueError) as exc:
            provider_label = adapter.display_name if "adapter" in locals() else normalized_provider.title()
            raise WalletFundingError(f"Unable to create a {provider_label} payment session: {exc}") from exc

        order.provider_reference = str(checkout_session.reference or order.provider_reference or order.reference)
        raw_payload = dict(order.raw_payload or {})
        raw_payload[f"{normalized_provider}_initialize"] = checkout_session.raw_response or {
            "checkout_url": checkout_session.checkout_url,
            "reference": checkout_session.reference,
        }
        order.raw_payload = raw_payload
        transaction = self._upsert_transaction(
            session,
            user=user,
            reference=order.reference,
            amount=order.net_amount,
            type_="credit",
            status="pending",
        )
        wallet = self.sync_wallet_balance(session, user, wallet=wallet)
        return WalletTopUpSession(
            reference=transaction.reference,
            payment_link=checkout_session.checkout_url,
            amount=transaction.amount,
            currency=order.unit.value,
            provider=normalized_provider,
            status=transaction.status,
            mock_mode=checkout_session.mock_mode,
        )

    def verify_top_up(
        self,
        session: Session,
        user: User,
        *,
        reference: str,
    ) -> WalletTopUpVerificationResult:
        normalized_reference = reference.strip()
        if not normalized_reference:
            raise WalletTopUpVerificationError("A transaction reference is required.")

        wallet = self.ensure_wallet(session, user)
        transaction = self._get_transaction(session, user=user, reference=normalized_reference)
        order = self._get_purchase_order(session, user=user, reference=normalized_reference)
        if transaction.status == "verified" and order.status == PurchaseOrderStatus.SETTLED:
            wallet = self.sync_wallet_balance(session, user, wallet=wallet)
            return WalletTopUpVerificationResult(wallet=wallet, transaction=transaction)

        try:
            adapter = get_provider_adapter(order.provider_key)
            verification: PaymentVerification = adapter.verify_payment(
                reference=order.provider_reference or normalized_reference
            )
        except (httpx.HTTPError, ValueError) as exc:
            raise WalletTopUpVerificationError(f"Unable to verify the {order.provider_key.title()} transaction: {exc}") from exc

        if verification.status == "pending":
            raise WalletTopUpVerificationError("Payment is still pending confirmation.")
        if verification.status != "success":
            transaction.status = "failed"
            WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
                order=order,
                status=PurchaseOrderStatus.FAILED,
                actor=user,
                notes=f"{order.provider_key}_status:{verification.status}",
            )
            session.flush()
            raise WalletTopUpVerificationError("Payment has not been completed successfully.")

        paid_amount_fiat = self._normalize_amount(verification.amount)
        if paid_amount_fiat != self._normalize_amount(order.amount_fiat):
            transaction.status = "failed"
            WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
                order=order,
                status=PurchaseOrderStatus.FAILED,
                actor=user,
                notes=f"{order.provider_key}_amount_mismatch",
            )
            session.flush()
            raise WalletTopUpVerificationError("Verified payment amount does not match the initiated top-up.")

        order.provider_reference = verification.provider_reference
        if verification.provider_event_id:
            order.provider_event_id = verification.provider_event_id
        if verification.processor_fee is not None:
            order.processor_fee = verification.processor_fee
        raw_payload = dict(order.raw_payload or {})
        raw_payload[f"{order.provider_key}_verify"] = verification.raw_payload
        order.raw_payload = raw_payload

        WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
            order=order,
            status=PurchaseOrderStatus.SETTLED,
            actor=user,
        )
        transaction.status = "verified"
        wallet = self.sync_wallet_balance(session, user, wallet=wallet)
        return WalletTopUpVerificationResult(wallet=wallet, transaction=transaction)

    def payment_provider_status(
        self,
        *,
        gateway_enabled: bool = True,
        enabled_providers: set[str] | None = None,
    ) -> dict[str, str]:
        return provider_runtime_statuses(
            gateway_enabled=gateway_enabled,
            enabled_providers=enabled_providers,
            include_stubbed=True,
        )

    def _get_purchase_order(
        self,
        session: Session,
        *,
        user: User,
        reference: str,
    ) -> FancoinPurchaseOrder:
        order = session.scalar(
            select(FancoinPurchaseOrder).where(
                FancoinPurchaseOrder.user_id == user.id,
                FancoinPurchaseOrder.reference == reference,
            )
        )
        if order is None:
            raise WalletTopUpNotFoundError("Top-up reference was not found.")
        return order

    def _get_transaction(
        self,
        session: Session,
        *,
        user: User,
        reference: str,
    ) -> WalletTransactionRecord:
        transaction = session.scalar(
            select(WalletTransactionRecord).where(
                WalletTransactionRecord.user_id == user.id,
                WalletTransactionRecord.reference == reference,
            )
        )
        if transaction is None:
            raise WalletTopUpNotFoundError("Wallet transaction was not found.")
        return transaction

    def _upsert_transaction(
        self,
        session: Session,
        *,
        user: User,
        reference: str,
        amount: Decimal,
        type_: str,
        status: str,
    ) -> WalletTransactionRecord:
        transaction = session.scalar(
            select(WalletTransactionRecord).where(
                WalletTransactionRecord.user_id == user.id,
                WalletTransactionRecord.reference == reference,
            )
        )
        if transaction is None:
            transaction = WalletTransactionRecord(
                user_id=user.id,
                reference=reference,
                amount=self._normalize_amount(amount),
                type=type_,
                status=status,
            )
            session.add(transaction)
            session.flush()
            return transaction
        transaction.amount = self._normalize_amount(amount)
        transaction.type = type_
        transaction.status = status
        session.flush()
        return transaction

    @staticmethod
    def _is_verified(status: str | None) -> bool:
        return str(status or "").strip().lower() == VERIFIED_COMPLIANCE_STATUS

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)


__all__ = [
    "AMOUNT_QUANTUM",
    "VERIFIED_COMPLIANCE_STATUS",
    "WalletFundingError",
    "WalletFundingService",
    "WalletTopUpNotFoundError",
    "WalletTopUpSession",
    "WalletTopUpVerificationError",
    "WalletTopUpVerificationResult",
]
