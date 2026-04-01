from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
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
from app.wallets.rail_service import WalletRailError, WalletRailService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
PAYSTACK_BASE_URL = "https://api.paystack.co"
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
                currency=LedgerUnit.CREDIT.value,
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
        summary = self.wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.CREDIT)
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
            raise WalletFundingError(
                f"Trading is currently disabled for country policy '{policy.country_code}'."
            )

    def initiate_top_up(
        self,
        session: Session,
        user: User,
        *,
        amount: Decimal,
        input_unit: str = "fiat",
        provider: str = "paystack",
        callback_url: str | None = None,
    ) -> WalletTopUpSession:
        normalized_provider = provider.strip().lower()
        if normalized_provider != "paystack":
            raise WalletFundingError("Only Paystack top-up is currently supported.")

        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise WalletFundingError("Top-up amount must be positive.")

        wallet = self.ensure_wallet(session, user)
        policy = PolicyService(session).get_country_policy_for_user(user=user)
        if not policy.deposits_enabled:
            raise WalletFundingError(
                f"Deposits are currently disabled for country policy '{policy.country_code}'."
            )

        settings = self.treasury_service.ensure_settings(session)
        rail_service = WalletRailService(session=session, wallet_service=self.wallet_service)
        try:
            order = rail_service.create_purchase_order(
                user=user,
                settings=settings,
                amount=normalized_amount,
                input_unit=input_unit,
                provider_key=normalized_provider,
                source_scope="wallet",
                unit=LedgerUnit.CREDIT,
                processor_mode="automatic_gateway",
                payout_channel="gateway",
                provider_reference=None,
                notes="wallet_top_up",
            )
        except WalletRailError as exc:
            raise WalletFundingError(str(exc)) from exc

        try:
            payment_session = self._initialize_paystack_transaction(
                order=order,
                user=user,
                settings=settings,
                callback_url=callback_url,
            )
        except httpx.HTTPError as exc:
            raise WalletFundingError("Unable to create a Paystack payment session.") from exc

        order.provider_reference = str(payment_session.get("reference") or order.reference)
        raw_payload = dict(order.raw_payload or {})
        raw_payload["paystack_initialize"] = payment_session
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
            payment_link=str(payment_session.get("authorization_url") or ""),
            amount=transaction.amount,
            currency=wallet.currency,
            provider=normalized_provider,
            status=transaction.status,
            mock_mode=bool(payment_session.get("mock_mode", False)),
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
            verification_payload = self._verify_paystack_transaction(reference=normalized_reference, order=order)
        except httpx.HTTPError as exc:
            raise WalletTopUpVerificationError("Unable to verify the Paystack transaction.") from exc

        data = verification_payload.get("data") if isinstance(verification_payload, dict) else None
        if not isinstance(data, dict):
            raise WalletTopUpVerificationError("Paystack returned an invalid verification payload.")

        payment_status = str(data.get("status") or "").strip().lower()
        if payment_status != "success":
            transaction.status = "failed"
            WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
                order=order,
                status=PurchaseOrderStatus.FAILED,
                actor=user,
                notes=f"paystack_status:{payment_status or 'unknown'}",
            )
            session.flush()
            raise WalletTopUpVerificationError("Payment has not been completed successfully.")

        paid_amount_fiat = self._normalize_paystack_amount(data.get("amount"))
        if paid_amount_fiat != self._normalize_amount(order.amount_fiat):
            transaction.status = "failed"
            WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
                order=order,
                status=PurchaseOrderStatus.FAILED,
                actor=user,
                notes="paystack_amount_mismatch",
            )
            session.flush()
            raise WalletTopUpVerificationError("Verified payment amount does not match the initiated top-up.")

        order.provider_reference = str(data.get("reference") or normalized_reference)
        provider_event_id = data.get("id")
        if provider_event_id is not None:
            order.provider_event_id = str(provider_event_id)
        raw_payload = dict(order.raw_payload or {})
        raw_payload["paystack_verify"] = verification_payload
        order.raw_payload = raw_payload

        WalletRailService(session=session, wallet_service=self.wallet_service).apply_purchase_order_status(
            order=order,
            status=PurchaseOrderStatus.SETTLED,
            actor=user,
        )
        transaction.status = "verified"
        wallet = self.sync_wallet_balance(session, user, wallet=wallet)
        return WalletTopUpVerificationResult(wallet=wallet, transaction=transaction)

    def _initialize_paystack_transaction(
        self,
        *,
        order: FancoinPurchaseOrder,
        user: User,
        settings: TreasurySettings,
        callback_url: str | None,
    ) -> dict[str, Any]:
        secret = self._paystack_secret()
        if not secret:
            return {
                "authorization_url": f"https://mock.paystack.local/{order.reference}",
                "access_code": f"mock-{order.reference}",
                "reference": order.reference,
                "mock_mode": True,
            }

        payload: dict[str, Any] = {
            "email": user.email,
            "amount": int((order.amount_fiat * Decimal("100")).to_integral_value()),
            "currency": settings.currency_code,
            "reference": order.reference,
            "metadata": {
                "purchase_order_reference": order.reference,
                "wallet_top_up": True,
                "user_id": user.id,
            },
        }
        resolved_callback_url = callback_url or self._paystack_callback_url()
        if resolved_callback_url:
            payload["callback_url"] = resolved_callback_url

        response = httpx.post(
            f"{self._paystack_base_url()}/transaction/initialize",
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict) or not data.get("authorization_url"):
            raise WalletFundingError("Paystack did not return an authorization URL.")
        data["mock_mode"] = False
        return data

    def _verify_paystack_transaction(
        self,
        *,
        reference: str,
        order: FancoinPurchaseOrder,
    ) -> dict[str, Any]:
        secret = self._paystack_secret()
        if not secret:
            return {
                "data": {
                    "id": f"mock-{reference}",
                    "status": "success",
                    "reference": reference,
                    "amount": int((self._normalize_amount(order.amount_fiat) * Decimal("100")).to_integral_value()),
                }
            }

        response = httpx.get(
            f"{self._paystack_base_url()}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise WalletTopUpVerificationError("Paystack verification failed.")
        return payload

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

    @staticmethod
    def _normalize_paystack_amount(value: Any) -> Decimal:
        return (Decimal(str(value or 0)) / Decimal("100")).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _paystack_secret() -> str | None:
        for name in ("GTE_PAYSTACK_SECRET_KEY", "PAYSTACK_SECRET_KEY"):
            secret = os.getenv(name)
            if secret and secret.strip():
                return secret.strip()
        return None

    @staticmethod
    def _paystack_callback_url() -> str | None:
        for name in ("GTE_PAYSTACK_CALLBACK_URL", "PAYSTACK_CALLBACK_URL"):
            callback_url = os.getenv(name)
            if callback_url and callback_url.strip():
                return callback_url.strip()
        return None

    @staticmethod
    def _paystack_base_url() -> str:
        raw_value = os.getenv("GTE_PAYSTACK_BASE_URL") or os.getenv("PAYSTACK_BASE_URL")
        if raw_value and raw_value.strip():
            return raw_value.strip().rstrip("/")
        return PAYSTACK_BASE_URL
