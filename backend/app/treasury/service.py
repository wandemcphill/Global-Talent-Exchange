from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin_godmode.service import DEFAULT_COMMISSION_SETTINGS
from app.models.analytics_event import AnalyticsEvent
from app.models.attachment import Attachment
from app.models.base import generate_uuid, utcnow
from app.models.dispute import Dispute, DisputeMessage, DisputeStatus
from app.models.notification_record import NotificationRecord
from app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    PaymentMode,
    RateDirection,
    TreasuryAuditEvent,
    TreasuryBankAccount,
    TreasurySettings,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
    UserBankAccount,
)
from app.models.withdrawal_review import WithdrawalReview
from app.models.risk_ops import RiskSeverity, SystemEventSeverity
from app.models.user import KycStatus, User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit, PayoutRequest, PayoutStatus
from app.risk_ops_engine.service import RiskActionBlockedError, RiskOpsService
from app.treasury.commission_policy import resolve_commission_policy
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_WHATSAPP = "+2347000000000"
PROTECTED_APP_ENVS = {"production", "prod", "staging", "release"}
PLACEHOLDER_TREASURY_BANK_NAME = "GTEX Treasury"
PLACEHOLDER_TREASURY_ACCOUNT_NUMBER = "0000000000"
PLACEHOLDER_TREASURY_ACCOUNT_NAME = "GTEX Treasury Desk"
WITHDRAWAL_RISK_AMOUNT_THRESHOLD = Decimal("5000.0000")
WITHDRAWAL_RISK_FREQUENCY_THRESHOLD = 3
WITHDRAWAL_RISK_WINDOW_HOURS = 24
GTEX_PLATFORM_POSITIONING = "GTex is a gaming platform using virtual currency for in-app competition and trading."
GTEX_LEGAL_DISCLOSURES = (
    "No guaranteed profit.",
    "Prices are volatile.",
    "Platform controls mechanics.",
    "Rewards are promotional for GTEX competitions.",
)
KYC_LIMITS: dict[str, Decimal] = {
    "basic": Decimal("50000.0000"),
    "verified": Decimal("500000.0000"),
}


class TreasuryError(ValueError):
    pass


class TreasuryNotFoundError(TreasuryError):
    pass


class TreasuryConflictError(TreasuryError):
    pass


def _is_protected_app_env() -> bool:
    environment = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    return environment in PROTECTED_APP_ENVS


def _is_placeholder_treasury_bank_account(bank_account: TreasuryBankAccount) -> bool:
    return (
        bank_account.bank_name == PLACEHOLDER_TREASURY_BANK_NAME
        and bank_account.account_number == PLACEHOLDER_TREASURY_ACCOUNT_NUMBER
        and bank_account.account_name == PLACEHOLDER_TREASURY_ACCOUNT_NAME
    )


@dataclass(slots=True, frozen=True)
class WithdrawalEligibility:
    available_balance: Decimal
    withdrawable_now: Decimal
    remaining_allowance: Decimal
    next_eligible_at: datetime | None
    kyc_status: KycStatus
    kyc_tier: str
    per_request_limit_fiat: Decimal | None
    requires_kyc: bool
    requires_bank_account: bool
    pending_withdrawals: Decimal
    country_code: str = "GLOBAL"
    country_withdrawals_enabled: bool = True
    missing_required_policies: tuple[str, ...] = ()
    policy_blocked: bool = False
    policy_block_reason: str | None = None
    platform_positioning: str = GTEX_PLATFORM_POSITIONING
    legal_disclosures: tuple[str, ...] = GTEX_LEGAL_DISCLOSURES


@dataclass(slots=True, frozen=True)
class DepositQuote:
    amount_fiat: Decimal
    amount_coin: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: RateDirection


class TreasuryService:
    def __init__(self, wallet_service: WalletService | None = None) -> None:
        self.wallet_service = wallet_service or WalletService()

    def ensure_settings(self, session: Session) -> TreasurySettings:
        settings = session.scalar(select(TreasurySettings).where(TreasurySettings.settings_key == "default"))
        if settings is None:
            settings = TreasurySettings(
                settings_key="default",
                currency_code="NGN",
                deposit_rate_value=Decimal("900.0000"),
                withdrawal_rate_value=Decimal("880.0000"),
                deposit_rate_direction=RateDirection.FIAT_PER_COIN,
                withdrawal_rate_direction=RateDirection.FIAT_PER_COIN,
                min_trader_buy_rate_fiat=Decimal("820.0000"),
                max_trader_buy_rate_fiat=Decimal("890.0000"),
                min_trader_sell_rate_fiat=Decimal("900.0000"),
                max_trader_sell_rate_fiat=Decimal("980.0000"),
                max_trader_spread_fiat=Decimal("120.0000"),
                max_buy_above_withdrawal_fiat=Decimal("10.0000"),
                max_sell_below_deposit_fiat=Decimal("0.0000"),
                min_deposit=Decimal("5.0000"),
                max_deposit=Decimal("500000.0000"),
                min_withdrawal=Decimal("10.0000"),
                max_withdrawal=Decimal("500000.0000"),
                deposit_mode=PaymentMode.MANUAL,
                withdrawal_mode=PaymentMode.MANUAL,
                whatsapp_number=DEFAULT_WHATSAPP,
            )
            session.add(settings)
            session.flush()
        if settings.active_bank_account_id is None:
            bank_account = session.scalar(select(TreasuryBankAccount).where(TreasuryBankAccount.is_active.is_(True)))
            if bank_account is None and not _is_protected_app_env():
                bank_account = TreasuryBankAccount(
                    currency_code=settings.currency_code,
                    bank_name=PLACEHOLDER_TREASURY_BANK_NAME,
                    account_number=PLACEHOLDER_TREASURY_ACCOUNT_NUMBER,
                    account_name=PLACEHOLDER_TREASURY_ACCOUNT_NAME,
                    bank_code=None,
                    is_active=True,
                )
                session.add(bank_account)
                session.flush()
            if bank_account is not None:
                settings.active_bank_account_id = bank_account.id
                session.flush()
        return settings

    def ensure_user_bank_account(self, session: Session, user: User) -> UserBankAccount | None:
        return session.scalar(
            select(UserBankAccount)
            .where(UserBankAccount.user_id == user.id, UserBankAccount.is_active.is_(True))
            .order_by(UserBankAccount.updated_at.desc())
        )

    def get_active_bank_account(self, session: Session, settings: TreasurySettings) -> TreasuryBankAccount:
        bank_account = None
        if settings.active_bank_account_id:
            bank_account = session.get(TreasuryBankAccount, settings.active_bank_account_id)
        if bank_account is None:
            bank_account = session.scalar(select(TreasuryBankAccount).where(TreasuryBankAccount.is_active.is_(True)))
        if bank_account is None:
            raise TreasuryError("No active treasury bank account is configured.")
        if _is_protected_app_env() and _is_placeholder_treasury_bank_account(bank_account):
            raise TreasuryError(
                "Active treasury bank account is a placeholder. Configure a real treasury bank account before "
                "accepting manual deposits."
            )
        return bank_account

    def compute_deposit_quote(
        self,
        settings: TreasurySettings,
        *,
        amount: Decimal,
        input_unit: str,
    ) -> DepositQuote:
        if amount <= Decimal("0.0000"):
            raise TreasuryError("Deposit amount must be positive.")
        rate_value = Decimal(settings.deposit_rate_value)
        if rate_value <= Decimal("0.0000"):
            raise TreasuryError("Deposit rate is not configured.")
        input_unit = input_unit.lower().strip()
        if input_unit not in {"fiat", "coin"}:
            raise TreasuryError("Input unit must be fiat or coin.")
        amount_fiat, amount_coin = self._compute_amounts(
            amount=amount,
            input_unit=input_unit,
            rate_value=rate_value,
            rate_direction=settings.deposit_rate_direction,
        )
        return DepositQuote(
            amount_fiat=amount_fiat,
            amount_coin=amount_coin,
            currency_code=settings.currency_code,
            rate_value=rate_value,
            rate_direction=settings.deposit_rate_direction,
        )

    def create_deposit_request(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        input_unit: str,
    ) -> DepositRequest:
        self._assert_deposit_allowed(session, user)
        settings = self.ensure_settings(session)
        if settings.deposit_mode not in {PaymentMode.MANUAL, PaymentMode.HYBRID}:
            raise TreasuryConflictError("Manual bank-transfer deposits are currently disabled.")

        quote = self.compute_deposit_quote(settings, amount=amount, input_unit=input_unit)
        self._enforce_deposit_limits(settings, quote.amount_coin)
        bank_account = self.get_active_bank_account(session, settings)
        reference = self._generate_reference(session, prefix="DEP", model=DepositRequest)
        request = DepositRequest(
            user_id=user.id,
            reference=reference,
            status=DepositStatus.AWAITING_PAYMENT,
            amount_fiat=quote.amount_fiat,
            amount_coin=quote.amount_coin,
            currency_code=quote.currency_code,
            rate_value=quote.rate_value,
            rate_direction=quote.rate_direction,
            bank_name=bank_account.bank_name,
            bank_account_number=bank_account.account_number,
            bank_account_name=bank_account.account_name,
            bank_code=bank_account.bank_code,
            bank_snapshot_json={
                "bank_name": bank_account.bank_name,
                "account_number": bank_account.account_number,
                "account_name": bank_account.account_name,
                "bank_code": bank_account.bank_code,
                "currency_code": bank_account.currency_code,
            },
        )
        session.add(request)
        session.flush()
        self.track_event(session, "deposit_quote_created", user=user, metadata={"deposit_request_id": request.id})
        self.create_notification(
            session,
            user=user,
            topic="wallet",
            message="Deposit request created.",
            resource_type="deposit_request",
            resource_id=request.id,
            metadata={"reference": request.reference},
        )
        return request

    def submit_deposit_request(
        self,
        session: Session,
        *,
        user: User,
        deposit_request_id: str,
        payer_name: str | None,
        sender_bank: str | None,
        transfer_reference: str | None,
        proof_attachment_id: str | None,
    ) -> DepositRequest:
        request = self._get_user_deposit(session, user, deposit_request_id)
        if request.status in {DepositStatus.CONFIRMED, DepositStatus.REJECTED, DepositStatus.EXPIRED}:
            raise TreasuryConflictError("This deposit request can no longer be updated.")
        if proof_attachment_id is not None:
            attachment = session.get(Attachment, proof_attachment_id)
            if attachment is None or attachment.created_by_user_id not in {None, user.id}:
                raise TreasuryError("Proof attachment was not found.")

        request.payer_name = payer_name or request.payer_name
        request.sender_bank = sender_bank or request.sender_bank
        request.transfer_reference = transfer_reference or request.transfer_reference
        request.proof_attachment_id = proof_attachment_id or request.proof_attachment_id
        request.status = DepositStatus.PAYMENT_SUBMITTED
        request.submitted_at = utcnow()
        session.flush()
        self.track_event(session, "deposit_submitted", user=user, metadata={"deposit_request_id": request.id})
        self.create_notification(
            session,
            user=user,
            topic="wallet",
            message="Deposit marked as paid. Awaiting admin confirmation.",
            resource_type="deposit_request",
            resource_id=request.id,
            metadata={"reference": request.reference},
        )
        return request

    def list_user_deposits(self, session: Session, user: User) -> list[DepositRequest]:
        return session.scalars(
            select(DepositRequest).where(DepositRequest.user_id == user.id).order_by(DepositRequest.created_at.desc())
        ).all()

    def confirm_deposit(
        self,
        session: Session,
        *,
        actor: User,
        deposit_request_id: str,
        admin_notes: str | None = None,
    ) -> DepositRequest:
        request = self._get_deposit_or_raise(session, deposit_request_id)
        if request.status == DepositStatus.CONFIRMED and request.ledger_transaction_id:
            return request
        if request.status not in {DepositStatus.PAYMENT_SUBMITTED, DepositStatus.UNDER_REVIEW}:
            raise TreasuryConflictError("Deposit cannot be confirmed in its current state.")
        user = session.get(User, request.user_id)
        if user is None:
            raise TreasuryError("Deposit request references missing user.")
        user_account = self.wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        treasury_account = self.wallet_service.ensure_treasury_account(session, LedgerUnit.COIN)
        operations_account = self.wallet_service.ensure_operations_account(session, LedgerUnit.COIN)
        entries = self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=request.amount_coin),
                LedgerPosting(account=treasury_account, amount=request.amount_coin),
                LedgerPosting(account=operations_account, amount=-(request.amount_coin * Decimal("2.0000"))),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            source_tag=LedgerSourceTag.MARKET_TOPUP,
            reference=request.reference,
            description="Manual bank transfer deposit confirmed.",
            external_reference=request.reference,
            actor=actor,
        )
        request.status = DepositStatus.CONFIRMED
        request.confirmed_at = utcnow()
        request.reviewed_at = utcnow()
        request.admin_user_id = actor.id
        request.admin_notes = admin_notes
        request.ledger_transaction_id = entries[0].transaction_id if entries else request.ledger_transaction_id
        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.deposit.confirmed",
            resource_type="deposit_request",
            resource_id=request.id,
            summary=f"Confirmed deposit {request.reference}.",
            payload={"reference": request.reference},
        )
        self.track_event(session, "deposit_confirmed", user=user, metadata={"deposit_request_id": request.id})
        self.create_notification(
            session,
            user=user,
            topic="wallet",
            message="Deposit confirmed. Wallet credited.",
            resource_type="deposit_request",
            resource_id=request.id,
            metadata={"reference": request.reference},
        )
        return request

    def reject_deposit(
        self,
        session: Session,
        *,
        actor: User,
        deposit_request_id: str,
        admin_notes: str | None = None,
    ) -> DepositRequest:
        request = self._get_deposit_or_raise(session, deposit_request_id)
        if request.status == DepositStatus.REJECTED:
            return request
        if request.status == DepositStatus.CONFIRMED:
            raise TreasuryConflictError("Confirmed deposits cannot be rejected.")
        request.status = DepositStatus.REJECTED
        request.rejected_at = utcnow()
        request.reviewed_at = utcnow()
        request.admin_user_id = actor.id
        request.admin_notes = admin_notes
        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.deposit.rejected",
            resource_type="deposit_request",
            resource_id=request.id,
            summary=f"Rejected deposit {request.reference}.",
            payload={"reference": request.reference, "notes": admin_notes or ""},
        )
        user = session.get(User, request.user_id)
        if user is not None:
            self.track_event(session, "deposit_rejected", user=user, metadata={"deposit_request_id": request.id})
            self.create_notification(
                session,
                user=user,
                topic="wallet",
                message="Deposit rejected. Please contact support if this is a mistake.",
                resource_type="deposit_request",
                resource_id=request.id,
                metadata={"reference": request.reference},
            )
        return request

    def mark_deposit_under_review(
        self,
        session: Session,
        *,
        actor: User,
        deposit_request_id: str,
        admin_notes: str | None = None,
    ) -> DepositRequest:
        request = self._get_deposit_or_raise(session, deposit_request_id)
        if request.status == DepositStatus.CONFIRMED:
            return request
        request.status = DepositStatus.UNDER_REVIEW
        request.reviewed_at = utcnow()
        request.admin_user_id = actor.id
        request.admin_notes = admin_notes
        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.deposit.review",
            resource_type="deposit_request",
            resource_id=request.id,
            summary=f"Marked deposit {request.reference} under review.",
            payload={"reference": request.reference},
        )
        return request

    def _resolve_user_policy_state(self, session: Session, user: User) -> tuple[str, bool, tuple[str, ...]]:
        from app.policies.service import PolicyService

        policy_service = PolicyService(session)
        country_policy = policy_service.get_country_policy_for_user(user=user)
        missing_documents = tuple(
            version.document.document_key for version in policy_service.list_missing_acceptances(user_id=user.id)
        )
        return country_policy.country_code, bool(country_policy.platform_reward_withdrawals_enabled), missing_documents

    def _assert_deposit_allowed(self, session: Session, user: User) -> None:
        from app.policies.service import PolicyService

        policy_service = PolicyService(session)
        country_policy = policy_service.get_country_policy_for_user(user=user)
        if not country_policy.deposits_enabled:
            raise TreasuryConflictError(
                f"Deposits are currently disabled for country policy '{country_policy.country_code}'."
            )
        if not self._deposit_policy_acceptance_required():
            return
        missing = policy_service.list_missing_acceptances(user_id=user.id)
        if missing:
            names = ", ".join(version.document.title for version in missing[:3])
            suffix = "" if len(missing) <= 3 else ", ..."
            raise TreasuryConflictError(f"Accept the latest required policies before making a deposit: {names}{suffix}")

    def _assert_withdrawal_policy(self, session: Session, user: User, source_scope: str) -> None:
        from app.policies.service import PolicyService

        policy_service = PolicyService(session)
        country_policy = policy_service.get_country_policy_for_user(user=user)
        scope = (source_scope or "trade").strip().lower()
        allowed = {
            "trade": country_policy.market_trading_enabled,
            "competition": country_policy.platform_reward_withdrawals_enabled,
            "user_hosted_gift": country_policy.user_hosted_gift_withdrawals_enabled,
            "gtex_competition_gift": country_policy.gtex_competition_gift_withdrawals_enabled,
            "national_reward": country_policy.national_reward_withdrawals_enabled,
        }
        if not allowed.get(scope, False):
            raise TreasuryConflictError(
                f"Withdrawals are disabled for source scope '{scope}' in {country_policy.country_code}."
            )
        missing = policy_service.list_missing_acceptances(user_id=user.id)
        if missing:
            names = ", ".join(version.document.title for version in missing[:3])
            suffix = "" if len(missing) <= 3 else ", ..."
            raise TreasuryConflictError(
                f"Accept the latest required policies before requesting withdrawals: {names}{suffix}"
            )

    @staticmethod
    def resolve_kyc_tier(kyc_status: KycStatus) -> str:
        if kyc_status == KycStatus.VERIFIED:
            return "verified"
        if kyc_status == KycStatus.UNDER_REVIEW:
            return "review"
        return "unverified"

    @classmethod
    def kyc_limit_for_status(cls, kyc_status: KycStatus) -> Decimal | None:
        return KYC_LIMITS.get(cls.resolve_kyc_tier(kyc_status))

    def legal_disclosures(self) -> tuple[str, ...]:
        return GTEX_LEGAL_DISCLOSURES

    @staticmethod
    def _deposit_policy_acceptance_required() -> bool:
        raw_value = os.getenv("GTE_REQUIRE_POLICY_ACCEPTANCE_FOR_DEPOSITS", "")
        return raw_value.strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def platform_positioning() -> str:
        return GTEX_PLATFORM_POSITIONING

    def _coin_limit_from_fiat_limit(self, *, settings: TreasurySettings, fiat_limit: Decimal | None) -> Decimal | None:
        if fiat_limit is None:
            return None
        rate_value = Decimal(settings.withdrawal_rate_value or 0)
        if rate_value <= Decimal("0.0000"):
            return None
        if settings.withdrawal_rate_direction == RateDirection.FIAT_PER_COIN:
            return (fiat_limit / rate_value).quantize(AMOUNT_QUANTUM)
        return (fiat_limit * rate_value).quantize(AMOUNT_QUANTUM)

    def get_withdrawal_eligibility(
        self,
        session: Session,
        user: User,
        *,
        settings: TreasurySettings | None = None,
        summary=None,
        country_code: str | None = None,
        country_withdrawals_enabled: bool | None = None,
        missing_required_policies: tuple[str, ...] | None = None,
        has_active_bank_account: bool | None = None,
    ) -> WithdrawalEligibility:
        settings = settings or self.ensure_settings(session)
        summary = summary or self.wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
        available = Decimal(summary.available_balance)
        kyc_status = user.kyc_status
        kyc_tier = self.resolve_kyc_tier(kyc_status)
        per_request_limit_fiat = self.kyc_limit_for_status(kyc_status)
        per_request_limit_coin = self._coin_limit_from_fiat_limit(
            settings=settings,
            fiat_limit=per_request_limit_fiat,
        )
        if country_code is None or country_withdrawals_enabled is None or missing_required_policies is None:
            country_code, country_withdrawals_enabled, missing_required_policies = self._resolve_user_policy_state(
                session, user
            )
        requires_kyc = kyc_status in {
            KycStatus.UNVERIFIED,
            KycStatus.PENDING,
            KycStatus.UNDER_REVIEW,
            KycStatus.REJECTED,
        }
        requires_bank = (
            self.ensure_user_bank_account(session, user) is None
            if has_active_bank_account is None
            else not has_active_bank_account
        )
        pending_withdrawals = self._pending_withdrawal_amount(session, user)
        policy_blocked = (not country_withdrawals_enabled) or bool(missing_required_policies)
        policy_block_reason = (
            f"Withdrawals are disabled for country policy {country_code}."
            if not country_withdrawals_enabled
            else (
                "Accept the latest required policies before requesting withdrawals."
                if missing_required_policies
                else None
            )
        )
        if requires_kyc:
            return WithdrawalEligibility(
                available_balance=available,
                withdrawable_now=Decimal("0.0000"),
                remaining_allowance=Decimal("0.0000"),
                next_eligible_at=None,
                kyc_status=kyc_status,
                kyc_tier=kyc_tier,
                per_request_limit_fiat=per_request_limit_fiat,
                requires_kyc=True,
                requires_bank_account=requires_bank,
                pending_withdrawals=pending_withdrawals,
                country_code=country_code,
                country_withdrawals_enabled=country_withdrawals_enabled,
                missing_required_policies=missing_required_policies,
                policy_blocked=policy_blocked,
                policy_block_reason=policy_block_reason,
            )

        remaining = available
        if per_request_limit_coin is not None:
            remaining = self._normalize_amount(per_request_limit_coin - pending_withdrawals)
            if remaining < Decimal("0.0000"):
                remaining = Decimal("0.0000")
        withdrawable = min(available, remaining)
        if policy_blocked:
            withdrawable = Decimal("0.0000")
            remaining = Decimal("0.0000")
        return WithdrawalEligibility(
            available_balance=available,
            withdrawable_now=withdrawable,
            remaining_allowance=remaining,
            next_eligible_at=None,
            kyc_status=kyc_status,
            kyc_tier=kyc_tier,
            per_request_limit_fiat=per_request_limit_fiat,
            requires_kyc=False,
            requires_bank_account=requires_bank,
            pending_withdrawals=pending_withdrawals,
            country_code=country_code,
            country_withdrawals_enabled=country_withdrawals_enabled,
            missing_required_policies=missing_required_policies,
            policy_blocked=policy_blocked,
            policy_block_reason=policy_block_reason,
        )

    def create_withdrawal_request(
        self,
        session: Session,
        *,
        user: User,
        amount_coin: Decimal,
        bank_account_id: str | None,
        source_scope: str = "trade",
        notes: str | None = None,
    ) -> TreasuryWithdrawalRequest:
        settings = self.ensure_settings(session)
        use_manual_payout = settings.withdrawal_mode in {PaymentMode.MANUAL, PaymentMode.HYBRID}
        processor_mode = "manual_bank_transfer" if use_manual_payout else "automatic_gateway"
        payout_channel = "bank_transfer" if use_manual_payout else "gateway"

        try:
            RiskOpsService(session).assert_withdrawal_allowed(user.id)
        except RiskActionBlockedError as exc:
            raise TreasuryConflictError(str(exc)) from exc

        eligibility = self.get_withdrawal_eligibility(session, user)
        if eligibility.requires_kyc:
            raise TreasuryConflictError("KYC is required before withdrawals can be requested.")
        if eligibility.policy_blocked:
            raise TreasuryConflictError(
                eligibility.policy_block_reason or "Withdrawal policy requirements are not satisfied."
            )
        if eligibility.requires_bank_account:
            raise TreasuryConflictError("Bank account details are required before withdrawals can be requested.")
        if amount_coin > eligibility.withdrawable_now:
            raise TreasuryConflictError("Withdrawal amount exceeds available withdrawable balance.")

        bank_account = self._resolve_user_bank_account(session, user, bank_account_id)
        self._assert_withdrawal_policy(session, user, source_scope)
        self._enforce_withdrawal_limits(settings, amount_coin)
        rate_value = Decimal(settings.withdrawal_rate_value)
        if rate_value <= Decimal("0.0000"):
            raise TreasuryError("Withdrawal rate is not configured.")
        amount_fiat, amount_coin = self._compute_amounts(
            amount=amount_coin,
            input_unit="coin",
            rate_value=rate_value,
            rate_direction=settings.withdrawal_rate_direction,
        )
        commission_policy = resolve_commission_policy(session)
        try:
            result = self.wallet_service.request_payout(
                session,
                user=user,
                amount=amount_coin,
                destination_reference=f"bank:{bank_account.id}",
                unit=LedgerUnit.COIN,
                source_scope=source_scope,
                withdrawal_fee_bps=commission_policy.withdrawal_fee_bps,
                minimum_fee=commission_policy.minimum_withdrawal_fee_credits,
                actor=user,
                notes=notes,
                extra_meta={
                    "processor_mode": processor_mode,
                    "payout_channel": payout_channel,
                    "source_scope": source_scope,
                    "kyc_tier": eligibility.kyc_tier,
                    "per_request_limit_fiat": (
                        str(eligibility.per_request_limit_fiat)
                        if eligibility.per_request_limit_fiat is not None
                        else None
                    ),
                    "platform_positioning": eligibility.platform_positioning,
                    "legal_disclosures": list(eligibility.legal_disclosures),
                },
            )
        except InsufficientBalanceError as exc:
            raise TreasuryConflictError(str(exc)) from exc

        reference = self._generate_reference(session, prefix="WDL", model=TreasuryWithdrawalRequest)
        withdrawal = TreasuryWithdrawalRequest(
            payout_request_id=result.payout_request.id,
            user_id=user.id,
            reference=reference,
            status=TreasuryWithdrawalStatus.PENDING_REVIEW,
            unit=LedgerUnit.COIN,
            amount_coin=amount_coin,
            amount_fiat=amount_fiat,
            fee_amount=result.fee_amount,
            net_amount=result.payout_request.amount,
            currency_code=settings.currency_code,
            rate_value=rate_value,
            rate_direction=settings.withdrawal_rate_direction,
            bank_name=bank_account.bank_name,
            bank_account_number=bank_account.account_number,
            bank_account_name=bank_account.account_name,
            bank_code=bank_account.bank_code,
            bank_snapshot_json={
                "bank_name": bank_account.bank_name,
                "account_number": bank_account.account_number,
                "account_name": bank_account.account_name,
                "bank_code": bank_account.bank_code,
                "currency_code": bank_account.currency_code,
            },
            kyc_status_snapshot=user.kyc_status.value,
            kyc_tier_snapshot=eligibility.kyc_tier,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
            source_scope=source_scope,
            notes=notes,
        )
        session.add(withdrawal)
        result.payout_request.status = PayoutStatus.REVIEWING
        session.flush()
        self._flag_withdrawal_risk(session, withdrawal)
        self.track_event(session, "withdrawal_requested", user=user, metadata={"withdrawal_id": withdrawal.id})
        self.create_notification(
            session,
            user=user,
            topic="wallet",
            message="Withdrawal requested. Awaiting admin review.",
            resource_type="withdrawal_request",
            resource_id=withdrawal.id,
            metadata={"reference": withdrawal.reference},
        )
        return withdrawal

    def review_withdrawal_status(
        self,
        session: Session,
        *,
        actor: User,
        withdrawal_id: str,
        status: TreasuryWithdrawalStatus,
        admin_notes: str | None = None,
    ) -> TreasuryWithdrawalRequest:
        request = self._get_withdrawal_or_raise(session, withdrawal_id)
        payout_request = session.get(PayoutRequest, request.payout_request_id)
        if payout_request is None:
            raise TreasuryError("Withdrawal request references missing payout request.")

        previous = request.status
        if previous == TreasuryWithdrawalStatus.PAID:
            return request

        request.status = status
        request.admin_user_id = actor.id
        request.admin_notes = admin_notes
        now = utcnow()
        if status == TreasuryWithdrawalStatus.APPROVED:
            request.approved_at = now
            payout_request.status = PayoutStatus.REVIEWING
            self.track_event(session, "withdrawal_approved", user_id=request.user_id)
        elif status == TreasuryWithdrawalStatus.PROCESSING:
            request.processed_at = now
            payout_request.status = PayoutStatus.PROCESSING
        elif status == TreasuryWithdrawalStatus.PAID:
            request.paid_at = now
            payout_request.status = PayoutStatus.COMPLETED
            self.wallet_service.complete_payout_request(session, payout_request, actor=actor)
            self.track_event(session, "withdrawal_paid", user_id=request.user_id)
        elif status == TreasuryWithdrawalStatus.REJECTED:
            request.rejected_at = now
            payout_request.status = PayoutStatus.REJECTED
            if payout_request.settlement_transaction_id is None:
                self.wallet_service.release_payout_request(
                    session, payout_request, actor=actor, failure_reason="rejected"
                )
            self.track_event(session, "withdrawal_rejected", user_id=request.user_id)
        elif status == TreasuryWithdrawalStatus.CANCELLED:
            request.cancelled_at = now
            payout_request.status = PayoutStatus.REJECTED
            if payout_request.settlement_transaction_id is None:
                self.wallet_service.release_payout_request(
                    session, payout_request, actor=actor, failure_reason="cancelled"
                )
        elif status == TreasuryWithdrawalStatus.DISPUTED:
            payout_request.status = PayoutStatus.HELD
        elif status == TreasuryWithdrawalStatus.PENDING_REVIEW:
            payout_request.status = PayoutStatus.REVIEWING

        request.reviewed_at = now
        review = WithdrawalReview(
            withdrawal_request_id=request.id,
            payout_request_id=request.payout_request_id,
            reviewer_user_id=actor.id,
            status_from=previous.value,
            status_to=status.value,
            processor_mode=request.processor_mode,
            payout_channel=request.payout_channel,
            source_scope=request.source_scope,
            gross_amount=request.amount_coin,
            fee_amount=request.fee_amount,
            net_amount=request.net_amount,
            notes=admin_notes,
            metadata_json={
                "payout_status": payout_request.status.value if payout_request else None,
            },
        )
        session.add(review)
        if status == TreasuryWithdrawalStatus.DISPUTED:
            RiskOpsService(session).create_system_event(
                actor_user_id=actor.id,
                event_key=f"withdrawal-disputed-{request.id}",
                event_type="finance_alert",
                severity=SystemEventSeverity.CRITICAL,
                title="Withdrawal marked as disputed",
                body="Withdrawal has been marked disputed and should be reviewed.",
                subject_type="treasury_withdrawal",
                subject_id=request.id,
                metadata_json={
                    "withdrawal_id": request.id,
                    "reference": request.reference,
                    "user_id": request.user_id,
                    "amount_fiat": str(request.amount_fiat),
                },
            )
        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.withdrawal.status_changed",
            resource_type="treasury_withdrawal",
            resource_id=request.id,
            summary=f"Changed withdrawal {request.reference} to {status.value}.",
            payload={"status": status.value, "previous": previous.value},
        )
        user = session.get(User, request.user_id)
        if user is not None:
            message = f"Withdrawal status updated to {status.value.replace('_', ' ')}."
            self.create_notification(
                session,
                user=user,
                topic="wallet",
                message=message,
                resource_type="withdrawal_request",
                resource_id=request.id,
                metadata={"reference": request.reference, "status": status.value},
            )
        return request

    def create_withdrawal_batch(
        self,
        session: Session,
        *,
        actor: User,
        statuses: tuple[TreasuryWithdrawalStatus, ...],
        limit: int = 50,
        notes: str | None = None,
    ) -> dict[str, Any]:
        selected = session.scalars(
            select(TreasuryWithdrawalRequest)
            .where(TreasuryWithdrawalRequest.status.in_(statuses))
            .order_by(TreasuryWithdrawalRequest.created_at.asc(), TreasuryWithdrawalRequest.id.asc())
            .limit(limit)
        ).all()
        if not selected:
            raise TreasuryConflictError("No withdrawals matched the requested batch filter.")

        batch_id = f"WDBATCH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        created_at = utcnow()
        gross_amount = Decimal("0.0000")
        fee_amount = Decimal("0.0000")
        net_amount = Decimal("0.0000")
        withdrawal_ids: list[str] = []

        for index, request in enumerate(selected, start=1):
            payout_request = session.get(PayoutRequest, request.payout_request_id)
            if payout_request is None:
                raise TreasuryError("Withdrawal request references missing payout request.")

            previous = request.status
            request.status = TreasuryWithdrawalStatus.PROCESSING
            request.processed_at = created_at
            request.reviewed_at = created_at
            request.admin_user_id = actor.id
            request.admin_notes = notes
            payout_request.status = PayoutStatus.PROCESSING
            session.add(
                WithdrawalReview(
                    withdrawal_request_id=request.id,
                    payout_request_id=request.payout_request_id,
                    reviewer_user_id=actor.id,
                    status_from=previous.value,
                    status_to=TreasuryWithdrawalStatus.PROCESSING.value,
                    processor_mode=request.processor_mode,
                    payout_channel=request.payout_channel,
                    source_scope=request.source_scope,
                    gross_amount=request.amount_coin,
                    fee_amount=request.fee_amount,
                    net_amount=request.net_amount,
                    notes=notes,
                    metadata_json={
                        "batch_id": batch_id,
                        "sequence": index,
                        "batched_at": created_at.isoformat(),
                        "batched_from_status": previous.value,
                        "payout_status": payout_request.status.value,
                    },
                )
            )
            gross_amount += Decimal(request.amount_coin or 0)
            fee_amount += Decimal(request.fee_amount or 0)
            net_amount += Decimal(request.net_amount or 0)
            withdrawal_ids.append(request.id)

        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.withdrawal.batch.created",
            resource_type="withdrawal_batch",
            resource_id=batch_id,
            summary=f"Created withdrawal batch {batch_id}.",
            payload={
                "batch_id": batch_id,
                "statuses": [status.value for status in statuses],
                "item_count": len(withdrawal_ids),
                "withdrawal_ids": withdrawal_ids,
                "gross_amount": str(gross_amount.quantize(AMOUNT_QUANTUM)),
                "fee_amount": str(fee_amount.quantize(AMOUNT_QUANTUM)),
                "net_amount": str(net_amount.quantize(AMOUNT_QUANTUM)),
            },
        )
        return {
            "batch_id": batch_id,
            "created_at": created_at,
            "actor_user_id": actor.id,
            "item_count": len(withdrawal_ids),
            "gross_amount": gross_amount.quantize(AMOUNT_QUANTUM),
            "fee_amount": fee_amount.quantize(AMOUNT_QUANTUM),
            "net_amount": net_amount.quantize(AMOUNT_QUANTUM),
            "statuses": list(statuses),
            "withdrawal_ids": withdrawal_ids,
            "notes": notes,
        }

    def list_withdrawal_batches(self, session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
        reviews = session.scalars(
            select(WithdrawalReview)
            .order_by(WithdrawalReview.created_at.desc(), WithdrawalReview.id.desc())
            .limit(max(limit * 20, limit))
        ).all()
        grouped: dict[str, dict[str, Any]] = {}
        for review in reviews:
            batch_id = str((review.metadata_json or {}).get("batch_id") or "").strip()
            if not batch_id:
                continue
            item = grouped.get(batch_id)
            if item is None:
                item = {
                    "batch_id": batch_id,
                    "created_at": review.created_at,
                    "actor_user_id": review.reviewer_user_id,
                    "item_count": 0,
                    "gross_amount": Decimal("0.0000"),
                    "fee_amount": Decimal("0.0000"),
                    "net_amount": Decimal("0.0000"),
                    "statuses": set(),
                    "withdrawal_ids": [],
                    "notes": review.notes,
                }
                grouped[batch_id] = item
            item["item_count"] += 1
            item["gross_amount"] += Decimal(review.gross_amount or 0)
            item["fee_amount"] += Decimal(review.fee_amount or 0)
            item["net_amount"] += Decimal(review.net_amount or 0)
            item["statuses"].add(TreasuryWithdrawalStatus(review.status_to))
            item["withdrawal_ids"].append(review.withdrawal_request_id)

        batches = sorted(grouped.values(), key=lambda item: item["created_at"], reverse=True)[:limit]
        payload: list[dict[str, Any]] = []
        for item in batches:
            payload.append(
                {
                    "batch_id": item["batch_id"],
                    "created_at": item["created_at"],
                    "actor_user_id": item["actor_user_id"],
                    "item_count": item["item_count"],
                    "gross_amount": Decimal(item["gross_amount"]).quantize(AMOUNT_QUANTUM),
                    "fee_amount": Decimal(item["fee_amount"]).quantize(AMOUNT_QUANTUM),
                    "net_amount": Decimal(item["net_amount"]).quantize(AMOUNT_QUANTUM),
                    "statuses": sorted(item["statuses"], key=lambda status: status.value),
                    "withdrawal_ids": item["withdrawal_ids"],
                    "notes": item["notes"],
                }
            )
        return payload

    def get_or_create_kyc_profile(self, session: Session, user: User) -> KycProfile:
        profile = session.scalar(select(KycProfile).where(KycProfile.user_id == user.id))
        if profile is None:
            profile = KycProfile(user_id=user.id, status=KycStatus.UNVERIFIED)
            session.add(profile)
            session.flush()
        return profile

    def submit_kyc(
        self,
        session: Session,
        *,
        user: User,
        nin: str | None,
        bvn: str | None,
        address_line1: str,
        address_line2: str | None,
        city: str | None,
        state: str | None,
        country: str | None,
        id_document_attachment_id: str | None,
        government_id_attachment_id: str | None = None,
        selfie_attachment_id: str | None = None,
        proof_of_address_attachment_id: str | None = None,
        country_confirmation: str | None = None,
    ) -> KycProfile:
        profile = self.get_or_create_kyc_profile(session, user)
        profile.nin = nin
        profile.bvn = bvn
        profile.address_line1 = address_line1
        profile.address_line2 = address_line2
        profile.city = city
        profile.state = state
        profile.country = country
        profile.id_document_attachment_id = id_document_attachment_id
        profile.government_id_attachment_id = government_id_attachment_id or id_document_attachment_id
        profile.selfie_attachment_id = selfie_attachment_id
        profile.proof_of_address_attachment_id = proof_of_address_attachment_id
        profile.country_confirmation = country_confirmation or country
        profile.status = KycStatus.UNDER_REVIEW
        profile.submitted_at = utcnow()
        user.kyc_status = KycStatus.UNDER_REVIEW
        session.flush()
        self.track_event(session, "kyc_submitted", user=user, metadata={"kyc_profile_id": profile.id})
        self.create_notification(
            session,
            user=user,
            topic="wallet",
            message="KYC submitted. Awaiting review.",
            resource_type="kyc_profile",
            resource_id=profile.id,
            metadata={},
        )
        return profile

    def review_kyc(
        self,
        session: Session,
        *,
        actor: User,
        profile_id: str,
        status: KycStatus,
        rejection_reason: str | None = None,
    ) -> KycProfile:
        profile = session.get(KycProfile, profile_id)
        if profile is None:
            raise TreasuryNotFoundError("KYC profile not found.")
        profile.status = status
        profile.reviewed_at = utcnow()
        profile.reviewer_user_id = actor.id
        profile.rejection_reason = rejection_reason
        user = session.get(User, profile.user_id)
        if user is not None:
            user.kyc_status = status
        session.flush()
        self._audit(
            session,
            actor=actor,
            event_type="treasury.kyc.reviewed",
            resource_type="kyc_profile",
            resource_id=profile.id,
            summary=f"KYC {profile.id} reviewed as {status.value}.",
            payload={"status": status.value, "reason": rejection_reason or ""},
        )
        if user is not None:
            event_name = "kyc_approved" if status == KycStatus.VERIFIED else "kyc_rejected"
            self.track_event(session, event_name, user=user, metadata={"kyc_profile_id": profile.id})
            message = "KYC approved." if event_name == "kyc_approved" else "KYC rejected."
            self.create_notification(
                session,
                user=user,
                topic="wallet",
                message=message,
                resource_type="kyc_profile",
                resource_id=profile.id,
                metadata={"status": status.value, "reason": rejection_reason or ""},
            )
        return profile

    def create_user_bank_account(
        self,
        session: Session,
        *,
        user: User,
        bank_name: str,
        account_number: str,
        account_name: str,
        bank_code: str | None,
        currency_code: str,
        set_active: bool,
    ) -> UserBankAccount:
        account = UserBankAccount(
            user_id=user.id,
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
            bank_code=bank_code,
            currency_code=currency_code,
            is_active=set_active,
        )
        session.add(account)
        session.flush()
        if set_active:
            self._deactivate_other_user_bank_accounts(session, user.id, account.id)
        self.track_event(session, "bank_details_created", user=user, metadata={"bank_account_id": account.id})
        return account

    def update_user_bank_account(
        self,
        session: Session,
        *,
        user: User,
        bank_account_id: str,
        updates: dict[str, object],
    ) -> UserBankAccount:
        account = session.scalar(
            select(UserBankAccount).where(UserBankAccount.id == bank_account_id, UserBankAccount.user_id == user.id)
        )
        if account is None:
            raise TreasuryNotFoundError("Bank account not found.")
        for key, value in updates.items():
            if value is None:
                continue
            setattr(account, key, value)
        session.flush()
        if updates.get("is_active") is True:
            self._deactivate_other_user_bank_accounts(session, user.id, account.id)
        self.track_event(session, "bank_details_updated", user=user, metadata={"bank_account_id": account.id})
        return account

    def list_user_bank_accounts(self, session: Session, user: User) -> list[UserBankAccount]:
        return session.scalars(
            select(UserBankAccount)
            .where(UserBankAccount.user_id == user.id)
            .order_by(UserBankAccount.created_at.desc())
        ).all()

    def open_dispute(
        self,
        session: Session,
        *,
        user: User,
        resource_type: str,
        resource_id: str,
        reference: str,
        subject: str | None,
        message: str,
        attachment_id: str | None,
    ) -> Dispute:
        dispute = Dispute(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            reference=reference,
            status=DisputeStatus.OPEN,
            subject=subject,
            metadata_json={},
            last_message_at=utcnow(),
        )
        session.add(dispute)
        session.flush()
        self.add_dispute_message(
            session,
            dispute=dispute,
            sender=user,
            sender_role="user",
            message=message,
            attachment_id=attachment_id,
        )
        self.track_event(session, "dispute_opened", user=user, metadata={"dispute_id": dispute.id})
        self.create_notification(
            session,
            user=user,
            topic="support",
            message="Dispute opened. Support will respond shortly.",
            resource_type="dispute",
            resource_id=dispute.id,
            metadata={"reference": reference},
        )
        return dispute

    def add_dispute_message(
        self,
        session: Session,
        *,
        dispute: Dispute,
        sender: User | None,
        sender_role: str,
        message: str,
        attachment_id: str | None,
    ) -> DisputeMessage:
        record = DisputeMessage(
            dispute_id=dispute.id,
            sender_user_id=sender.id if sender else None,
            sender_role=sender_role,
            message=message,
            attachment_id=attachment_id,
        )
        session.add(record)
        dispute.last_message_at = utcnow()
        if sender_role == "admin":
            dispute.status = DisputeStatus.AWAITING_USER
        else:
            dispute.status = DisputeStatus.AWAITING_ADMIN
        session.flush()
        if sender_role == "admin" and dispute.user_id:
            user = session.get(User, dispute.user_id)
            if user is not None:
                self.create_notification(
                    session,
                    user=user,
                    topic="support",
                    message="New admin reply on your dispute.",
                    resource_type="dispute",
                    resource_id=dispute.id,
                    metadata={"reference": dispute.reference},
                )
        return record

    def list_user_disputes(self, session: Session, user: User) -> list[Dispute]:
        return session.scalars(
            select(Dispute).where(Dispute.user_id == user.id).order_by(Dispute.updated_at.desc())
        ).all()

    def get_dispute(self, session: Session, dispute_id: str) -> Dispute | None:
        return session.get(Dispute, dispute_id)

    def create_notification(
        self,
        session: Session,
        *,
        user: User,
        topic: str,
        message: str,
        resource_type: str | None,
        resource_id: str | None,
        metadata: dict[str, Any],
    ) -> NotificationRecord:
        record = NotificationRecord(
            user_id=user.id,
            topic=topic,
            template_key=None,
            resource_type=resource_type,
            resource_id=resource_id,
            message=message,
            metadata_json=metadata,
        )
        session.add(record)
        session.flush()
        return record

    def track_event(
        self,
        session: Session,
        name: str,
        *,
        user: User | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AnalyticsEvent:
        record = AnalyticsEvent(
            name=name,
            user_id=user.id if user is not None else user_id,
            metadata_json=metadata or {},
        )
        session.add(record)
        session.flush()
        return record

    def _audit(
        self,
        session: Session,
        *,
        actor: User,
        event_type: str,
        resource_type: str,
        resource_id: str,
        summary: str,
        payload: dict[str, Any],
    ) -> TreasuryAuditEvent:
        audit = TreasuryAuditEvent(
            event_type=event_type,
            actor_user_id=actor.id,
            actor_email=actor.email,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary,
            payload=payload,
        )
        session.add(audit)
        session.flush()
        return audit

    def _commission_settings(self) -> dict[str, Any]:
        return dict(DEFAULT_COMMISSION_SETTINGS)

    def _flag_withdrawal_risk(self, session: Session, withdrawal: TreasuryWithdrawalRequest) -> None:
        amount_signal = Decimal(str(withdrawal.amount_fiat or withdrawal.amount_coin or 0))
        risk_service = RiskOpsService(session)
        if amount_signal >= WITHDRAWAL_RISK_AMOUNT_THRESHOLD:
            risk_service.create_aml_case(
                actor_user_id=None,
                user_id=withdrawal.user_id,
                trigger_source="withdrawal_request",
                title="Large withdrawal request",
                description="Withdrawal request exceeded large-value threshold.",
                severity=RiskSeverity.HIGH,
                amount_signal=amount_signal,
                country_code=None,
                metadata_json={"withdrawal_id": withdrawal.id},
            )
        window_start = utcnow() - timedelta(hours=WITHDRAWAL_RISK_WINDOW_HOURS)
        recent_count = session.scalar(
            select(func.count())
            .select_from(TreasuryWithdrawalRequest)
            .where(
                TreasuryWithdrawalRequest.user_id == withdrawal.user_id,
                TreasuryWithdrawalRequest.created_at >= window_start,
            )
        )
        if int(recent_count or 0) >= WITHDRAWAL_RISK_FREQUENCY_THRESHOLD:
            risk_service.create_system_event(
                actor_user_id=None,
                event_key=f"withdrawal-frequency-{withdrawal.user_id}-{withdrawal.id}",
                event_type="finance_alert",
                severity=SystemEventSeverity.WARNING,
                title="High frequency withdrawal requests",
                body="User submitted multiple withdrawal requests within 24 hours.",
                subject_type="treasury_withdrawal",
                subject_id=withdrawal.id,
                metadata_json={
                    "user_id": withdrawal.user_id,
                    "recent_count": int(recent_count or 0),
                },
            )

    def _enforce_deposit_limits(self, settings: TreasurySettings, amount_coin: Decimal) -> None:
        if settings.min_deposit and amount_coin < Decimal(settings.min_deposit):
            raise TreasuryConflictError("Deposit amount is below the minimum.")
        if settings.max_deposit and amount_coin > Decimal(settings.max_deposit):
            raise TreasuryConflictError("Deposit amount exceeds the maximum.")

    def _enforce_withdrawal_limits(self, settings: TreasurySettings, amount_coin: Decimal) -> None:
        if settings.min_withdrawal and amount_coin < Decimal(settings.min_withdrawal):
            raise TreasuryConflictError("Withdrawal amount is below the minimum.")
        if settings.max_withdrawal and amount_coin > Decimal(settings.max_withdrawal):
            raise TreasuryConflictError("Withdrawal amount exceeds the maximum.")

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        return Decimal(str(value or "0.0000")).quantize(AMOUNT_QUANTUM)

    def _compute_amounts(
        self,
        *,
        amount: Decimal,
        input_unit: str,
        rate_value: Decimal,
        rate_direction: RateDirection,
    ) -> tuple[Decimal, Decimal]:
        input_unit = input_unit.lower()
        amount = Decimal(amount)
        if rate_direction == RateDirection.FIAT_PER_COIN:
            if input_unit == "fiat":
                amount_fiat = amount
                amount_coin = (amount / rate_value).quantize(AMOUNT_QUANTUM)
            else:
                amount_coin = amount
                amount_fiat = (amount * rate_value).quantize(AMOUNT_QUANTUM)
        else:
            if input_unit == "fiat":
                amount_fiat = amount
                amount_coin = (amount * rate_value).quantize(AMOUNT_QUANTUM)
            else:
                amount_coin = amount
                amount_fiat = (amount / rate_value).quantize(AMOUNT_QUANTUM)
        return (
            amount_fiat.quantize(AMOUNT_QUANTUM),
            amount_coin.quantize(AMOUNT_QUANTUM),
        )

    def _generate_reference(
        self,
        session: Session,
        *,
        prefix: str,
        model: type[DepositRequest] | type[TreasuryWithdrawalRequest],
    ) -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(10):
            token = uuid4().hex[:6].upper()
            candidate = f"{prefix}-{date_part}-{token}"
            exists = session.scalar(select(model).where(model.reference == candidate))
            if exists is None:
                return candidate
        return f"{prefix}-{date_part}-{generate_uuid()[:8].upper()}"

    def _get_user_deposit(self, session: Session, user: User, deposit_request_id: str) -> DepositRequest:
        request = session.scalar(
            select(DepositRequest).where(
                DepositRequest.id == deposit_request_id,
                DepositRequest.user_id == user.id,
            )
        )
        if request is None:
            raise TreasuryNotFoundError("Deposit request not found.")
        return request

    def _get_deposit_or_raise(self, session: Session, deposit_request_id: str) -> DepositRequest:
        request = session.get(DepositRequest, deposit_request_id)
        if request is None:
            raise TreasuryNotFoundError("Deposit request not found.")
        return request

    def _get_withdrawal_or_raise(self, session: Session, withdrawal_id: str) -> TreasuryWithdrawalRequest:
        request = session.get(TreasuryWithdrawalRequest, withdrawal_id)
        if request is None:
            raise TreasuryNotFoundError("Withdrawal request not found.")
        return request

    def _resolve_user_bank_account(
        self,
        session: Session,
        user: User,
        bank_account_id: str | None,
    ) -> UserBankAccount:
        if bank_account_id:
            account = session.scalar(
                select(UserBankAccount).where(
                    UserBankAccount.id == bank_account_id,
                    UserBankAccount.user_id == user.id,
                )
            )
            if account is None:
                raise TreasuryNotFoundError("Bank account not found.")
            return account
        account = self.ensure_user_bank_account(session, user)
        if account is None:
            raise TreasuryNotFoundError("Bank account not found.")
        return account

    def _deactivate_other_user_bank_accounts(self, session: Session, user_id: str, active_id: str) -> None:
        session.execute(
            UserBankAccount.__table__.update()
            .where(UserBankAccount.user_id == user_id, UserBankAccount.id != active_id)
            .values(is_active=False)
        )
        session.flush()

    def _withdrawal_window_sum(self, session: Session, user: User, window_start: datetime) -> Decimal:
        statuses = (
            TreasuryWithdrawalStatus.PENDING_REVIEW,
            TreasuryWithdrawalStatus.APPROVED,
            TreasuryWithdrawalStatus.PROCESSING,
            TreasuryWithdrawalStatus.PAID,
        )
        total = session.scalar(
            select(func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_coin), 0)).where(
                TreasuryWithdrawalRequest.user_id == user.id,
                TreasuryWithdrawalRequest.created_at >= window_start,
                TreasuryWithdrawalRequest.status.in_(statuses),
            )
        )
        return Decimal(total or 0)

    def _next_withdrawal_window_time(self, session: Session, user: User, window_start: datetime) -> datetime | None:
        statuses = (
            TreasuryWithdrawalStatus.PENDING_REVIEW,
            TreasuryWithdrawalStatus.APPROVED,
            TreasuryWithdrawalStatus.PROCESSING,
            TreasuryWithdrawalStatus.PAID,
        )
        oldest = session.scalar(
            select(func.min(TreasuryWithdrawalRequest.created_at)).where(
                TreasuryWithdrawalRequest.user_id == user.id,
                TreasuryWithdrawalRequest.created_at >= window_start,
                TreasuryWithdrawalRequest.status.in_(statuses),
            )
        )
        if oldest is None:
            return None
        return oldest + timedelta(hours=24)

    def _pending_withdrawal_amount(self, session: Session, user: User) -> Decimal:
        statuses = (
            TreasuryWithdrawalStatus.PENDING_REVIEW,
            TreasuryWithdrawalStatus.APPROVED,
            TreasuryWithdrawalStatus.PROCESSING,
        )
        total = session.scalar(
            select(func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_coin), 0)).where(
                TreasuryWithdrawalRequest.user_id == user.id,
                TreasuryWithdrawalRequest.status.in_(statuses),
            )
        )
        return Decimal(total or 0)
