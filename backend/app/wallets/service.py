from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
import json

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.user import User
from backend.app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
    PayoutRequest,
    PayoutStatus,
)

AMOUNT_QUANTUM = Decimal("0.0001")


class LedgerError(ValueError):
    pass


class InsufficientBalanceError(LedgerError):
    pass


class UnbalancedTransactionError(LedgerError):
    pass


@dataclass(frozen=True, slots=True)
class LedgerPosting:
    account: LedgerAccount
    amount: Decimal
    source_tag: LedgerSourceTag | None = None


@dataclass(frozen=True, slots=True)
class WalletSummary:
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    currency: LedgerUnit


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    user_id: str
    currency: LedgerUnit
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    holdings: list[dict[str, Decimal | str]]


@dataclass(frozen=True, slots=True)
class WalletLedgerPage:
    page: int
    page_size: int
    total: int
    items: list[LedgerEntry]


@dataclass(frozen=True, slots=True)
class WithdrawalRequestResult:
    payout_request: PayoutRequest
    fee_amount: Decimal
    total_debit: Decimal
    source_scope: str


class WalletService:
    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.trade_settlement_reason = LedgerEntryReason.TRADE_SETTLEMENT

    def ensure_default_accounts(self, session: Session, user: User) -> dict[LedgerUnit, LedgerAccount]:
        accounts: dict[LedgerUnit, LedgerAccount] = {}
        for unit, label in ((LedgerUnit.COIN, "Coins"), (LedgerUnit.CREDIT, "Credits")):
            code = self._user_account_code(user.id, unit)
            account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
            if account is None:
                account = LedgerAccount(
                    owner_user_id=user.id,
                    code=code,
                    label=label,
                    unit=unit,
                    kind=LedgerAccountKind.USER,
                )
                session.add(account)
                session.flush()
            accounts[unit] = account
        return accounts

    def list_accounts_for_user(self, session: Session, user: User) -> list[LedgerAccount]:
        accounts = session.scalars(
            select(LedgerAccount)
            .where(
                LedgerAccount.owner_user_id == user.id,
                LedgerAccount.code.like(f"user:{user.id}:%"),
            )
            .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
        ).all()
        if not accounts:
            self.ensure_default_accounts(session, user)
            accounts = session.scalars(
                select(LedgerAccount)
                .where(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"user:{user.id}:%"),
                )
                .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
            ).all()
        return accounts

    def get_user_account(self, session: Session, user: User, unit: LedgerUnit) -> LedgerAccount:
        code = self._user_account_code(user.id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = self.ensure_default_accounts(session, user)[unit]
        return account

    def get_user_escrow_account(self, session: Session, user: User, unit: LedgerUnit) -> LedgerAccount:
        code = self._user_escrow_account_code(user.id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                owner_user_id=user.id,
                code=code,
                label=f"{unit.value.capitalize()} Escrow",
                unit=unit,
                kind=LedgerAccountKind.ESCROW,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_platform_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        code = f"platform:{unit.value}:clearing"
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Platform {unit.value.capitalize()} Clearing",
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=True,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_platform_burn_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        code = f"platform:{unit.value}:burn"
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Platform {unit.value.capitalize()} Burn",
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=False,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_promo_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        code = f"platform:{unit.value}:promo_pool"
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Platform {unit.value.capitalize()} Promo Pool",
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=False,
            )
            session.add(account)
            session.flush()
        return account

    def get_position_account(self, session: Session, user: User, player_id: str) -> LedgerAccount:
        code = self._position_account_code(user.id, player_id)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Player {player_id} Position",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.USER,
            )
            session.add(account)
            session.flush()
        return account

    def get_position_escrow_account(self, session: Session, user: User, player_id: str) -> LedgerAccount:
        code = self._position_escrow_account_code(user.id, player_id)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Player {player_id} Position Escrow",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.ESCROW,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_platform_position_account(self, session: Session, player_id: str) -> LedgerAccount:
        code = self._platform_position_account_code(player_id)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Platform {player_id} Inventory",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=True,
            )
            session.add(account)
            session.flush()
        return account

    def create_payment_event(
        self,
        session: Session,
        *,
        user: User,
        provider: PaymentProvider | str,
        provider_reference: str,
        amount: Decimal,
        pack_code: str | None = None,
    ) -> PaymentEvent:
        normalized_provider = PaymentProvider(provider)
        event = PaymentEvent(
            user_id=user.id,
            provider=normalized_provider,
            provider_reference=provider_reference.strip(),
            pack_code=pack_code,
            amount=self._normalize_amount(amount),
            unit=LedgerUnit.COIN,
            status=PaymentStatus.PENDING,
            raw_payload={},
        )
        session.add(event)
        try:
            session.flush()
        except IntegrityError as exc:
            raise LedgerError("Provider reference already exists.") from exc
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.payment.created",
                payload={
                    "payment_event_id": event.id,
                    "user_id": user.id,
                    "provider": normalized_provider.value,
                    "amount": str(event.amount),
                },
            )
        )
        return event

    def verify_payment_event(self, session: Session, payment_event: PaymentEvent, *, actor: User | None = None) -> PaymentEvent:
        if payment_event.status != PaymentStatus.PENDING:
            raise LedgerError("Only pending payment events can be verified.")

        user = session.get(User, payment_event.user_id)
        if user is None:
            raise LedgerError("Payment event references a missing user.")

        user_account = self.get_user_account(session, user, payment_event.unit)
        platform_account = self.ensure_platform_account(session, payment_event.unit)
        source_tag = (
            LedgerSourceTag.MARKET_TOPUP
            if payment_event.unit == LedgerUnit.COIN
            else LedgerSourceTag.FANCOIN_PURCHASE
        )
        entries = self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=payment_event.amount),
                LedgerPosting(account=platform_account, amount=-payment_event.amount),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            source_tag=source_tag,
            reference=payment_event.provider_reference,
            description=f"Verified {PaymentProvider(payment_event.provider).value} deposit",
            external_reference=payment_event.provider_reference,
            actor=actor,
        )
        payment_event.status = PaymentStatus.VERIFIED
        payment_event.verified_at = utcnow()
        payment_event.processed_at = utcnow()
        payment_event.ledger_transaction_id = entries[0].transaction_id
        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.payment.verified",
                payload={
                    "payment_event_id": payment_event.id,
                    "user_id": user.id,
                    "transaction_id": payment_event.ledger_transaction_id,
                    "amount": str(payment_event.amount),
                },
            )
        )
        return payment_event



    def competition_reward_balance(self, session: Session, user: User, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        account = self.get_user_account(session, user, unit)
        reward_total = session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.reason == LedgerEntryReason.COMPETITION_REWARD,
                LedgerEntry.amount > 0,
            )
        )
        return self._normalize_amount(reward_total)

    def competition_reward_withdrawable_balance(self, session: Session, user: User, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        rewards_total = self.competition_reward_balance(session, user, unit)
        requests = session.scalars(select(PayoutRequest).where(PayoutRequest.user_id == user.id, PayoutRequest.unit == unit)).all()
        reserved_or_paid = Decimal("0.0000")
        for request in requests:
            meta = self._parse_payout_meta(request.notes)
            if meta.get("source_scope") != "competition":
                continue
            if request.status in {PayoutStatus.REJECTED, PayoutStatus.FAILED}:
                continue
            reserved_or_paid += self._normalize_amount(request.amount)
        remaining = rewards_total - reserved_or_paid
        if remaining < Decimal("0.0000"):
            remaining = Decimal("0.0000")
        return self._normalize_amount(remaining)

    def list_payout_requests_for_user(self, session: Session, user: User) -> list[PayoutRequest]:
        return session.scalars(
            select(PayoutRequest).where(PayoutRequest.user_id == user.id).order_by(PayoutRequest.created_at.desc())
        ).all()

    def request_payout(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        destination_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_scope: str = "trade",
        withdrawal_fee_bps: int = 1000,
        minimum_fee: Decimal = Decimal("5.0000"),
        actor: User | None = None,
        notes: str | None = None,
        extra_meta: dict[str, object] | None = None,
    ) -> WithdrawalRequestResult:
        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise LedgerError("Withdrawal amount must be positive.")
        if source_scope not in {"trade", "competition", "user_hosted_gift", "gtex_competition_gift", "national_reward"}:
            raise LedgerError("Withdrawal source must be trade, competition, user_hosted_gift, gtex_competition_gift, or national_reward.")

        user_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        fee_amount = self._normalize_amount(max((normalized_amount * Decimal(withdrawal_fee_bps) / Decimal(10_000)), self._normalize_amount(minimum_fee)))
        total_debit = self._normalize_amount(normalized_amount + fee_amount)
        available_balance = self.get_balance(session, user_account)
        if available_balance < total_debit:
            raise InsufficientBalanceError("Available balance is lower than the requested withdrawal plus fee.")
        if source_scope == "competition":
            reward_balance = self.competition_reward_withdrawable_balance(session, user, unit)
            if reward_balance < normalized_amount:
                raise InsufficientBalanceError("Competition reward balance is lower than the requested e-game withdrawal.")

        reference = f"payout-request:{generate_uuid()}"
        postings = [
            LedgerPosting(account=user_account, amount=-normalized_amount, source_tag=net_tag),
            LedgerPosting(account=escrow_account, amount=normalized_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=user_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=escrow_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal hold for {source_scope} payout to {destination_reference}",
            external_reference=reference,
            actor=actor or user,
        )
        meta = {
            "source_scope": source_scope,
            "fee_amount": str(fee_amount),
            "total_debit": str(total_debit),
            "requested_net_amount": str(normalized_amount),
            "destination_reference": destination_reference,
            "user_notes": notes or "",
        }
        if extra_meta:
            meta.update(extra_meta)
        payout_request = PayoutRequest(
            user_id=user.id,
            account_id=user_account.id,
            amount=normalized_amount,
            unit=unit,
            status=PayoutStatus.REQUESTED,
            destination_reference=destination_reference.strip(),
            hold_transaction_id=entries[0].transaction_id if entries else None,
            notes=json.dumps(meta, sort_keys=True),
        )
        session.add(payout_request)
        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.withdrawal.requested",
                payload={
                    "payout_request_id": payout_request.id,
                    "user_id": user.id,
                    "source_scope": source_scope,
                    "amount": str(normalized_amount),
                    "fee_amount": str(fee_amount),
                    "total_debit": str(total_debit),
                },
            )
        )
        return WithdrawalRequestResult(payout_request=payout_request, fee_amount=fee_amount, total_debit=total_debit, source_scope=source_scope)

    def complete_payout_request(self, session: Session, payout_request: PayoutRequest, *, actor: User | None = None) -> PayoutRequest:
        if payout_request.settlement_transaction_id is not None:
            return payout_request
        user = session.get(User, payout_request.user_id)
        if user is None:
            raise LedgerError("Payout request references a missing user.")
        escrow_account = self.get_user_escrow_account(session, user, payout_request.unit)
        platform_account = self.ensure_platform_account(session, payout_request.unit)
        meta = self._parse_payout_meta(payout_request.notes)
        net_amount = self._normalize_amount(payout_request.amount)
        total_debit = self._normalize_amount(meta.get("total_debit", net_amount))
        fee_amount = self._normalize_amount(meta.get("fee_amount", total_debit - net_amount))
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        if fee_amount < Decimal("0.0000"):
            fee_amount = Decimal("0.0000")
        reference = f"payout-settlement:{payout_request.id}"
        postings = [
            LedgerPosting(account=escrow_account, amount=-net_amount, source_tag=net_tag),
            LedgerPosting(account=platform_account, amount=net_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=escrow_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=platform_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.WITHDRAWAL_SETTLEMENT,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal settled to {payout_request.destination_reference}",
            external_reference=reference,
            actor=actor,
        )
        payout_request.settlement_transaction_id = entries[0].transaction_id if entries else None
        return payout_request

    def release_payout_request(self, session: Session, payout_request: PayoutRequest, *, actor: User | None = None, failure_reason: str | None = None) -> PayoutRequest:
        if payout_request.settlement_transaction_id is not None:
            return payout_request
        user = session.get(User, payout_request.user_id)
        if user is None:
            raise LedgerError("Payout request references a missing user.")
        escrow_account = self.get_user_escrow_account(session, user, payout_request.unit)
        user_account = self.get_user_account(session, user, payout_request.unit)
        meta = self._parse_payout_meta(payout_request.notes)
        net_amount = self._normalize_amount(payout_request.amount)
        total_debit = self._normalize_amount(meta.get("total_debit", net_amount))
        fee_amount = self._normalize_amount(meta.get("fee_amount", total_debit - net_amount))
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        if fee_amount < Decimal("0.0000"):
            fee_amount = Decimal("0.0000")
        reference = f"payout-release:{payout_request.id}"
        postings = [
            LedgerPosting(account=escrow_account, amount=-net_amount, source_tag=net_tag),
            LedgerPosting(account=user_account, amount=net_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=escrow_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=user_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal released back to user after {failure_reason or 'cancel'}",
            external_reference=reference,
            actor=actor,
        )
        payout_request.settlement_transaction_id = entries[0].transaction_id if entries else None
        return payout_request

    def _parse_payout_meta(self, notes: str | None) -> dict[str, object]:
        raw = (notes or "").strip()
        if not raw:
            return {}
        if raw.startswith("{"):
            try:
                value = json.loads(raw)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                return {"raw_notes": raw}
        return {"raw_notes": raw}

    def get_adaptive_overview(self, session: Session, user: User) -> dict[str, object]:
        summary = self.get_wallet_summary(session, user)
        requested_statuses = {PayoutStatus.REQUESTED, PayoutStatus.REVIEWING, PayoutStatus.HELD, PayoutStatus.PROCESSING}
        pending_withdrawals = session.scalar(
            select(func.count()).select_from(PayoutRequest).where(
                PayoutRequest.user_id == user.id,
                PayoutRequest.status.in_(tuple(requested_statuses)),
            )
        ) or 0
        provider_status = {provider.value: 'available' for provider in PaymentProvider}
        insights: list[dict[str, str]] = []
        if summary.available_balance <= Decimal('0.0000'):
            insights.append({'label': 'Liquidity posture', 'value': 'Wallet is empty. Deposit or complete a sale to unlock actions.', 'tone': 'warning'})
        elif summary.reserved_balance > summary.available_balance:
            insights.append({'label': 'Reserved pressure', 'value': 'Reserved commitments are heavier than free balance. Review open market and withdrawal holds.', 'tone': 'warning'})
        else:
            insights.append({'label': 'Withdrawal readiness', 'value': 'Withdrawable balance is healthy relative to current holds.', 'tone': 'success'})
        if pending_withdrawals:
            insights.append({'label': 'Withdrawal queue', 'value': f'{pending_withdrawals} payout request(s) still moving through review or processing.', 'tone': 'info'})
        return {
            'available_balance': summary.available_balance,
            'reserved_balance': summary.reserved_balance,
            'total_balance': summary.total_balance,
            'currency': summary.currency,
            'withdrawable_balance': summary.available_balance,
            'pending_withdrawals': int(pending_withdrawals),
            'payment_provider_status': provider_status,
            'insights': insights,
        }

    def append_transaction(
        self,
        session: Session,
        *,
        postings: list[LedgerPosting],
        reason: LedgerEntryReason,
        source_tag: LedgerSourceTag | None = None,
        reference: str | None = None,
        description: str | None = None,
        external_reference: str | None = None,
        actor: User | None = None,
    ) -> list[LedgerEntry]:
        if len(postings) < 2:
            raise UnbalancedTransactionError("Ledger transactions require at least two postings.")

        normalized_postings: list[LedgerPosting] = []
        unit_set: set[LedgerUnit] = set()
        total = Decimal("0.0000")
        delta_by_account: dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
        for posting in postings:
            amount = self._normalize_amount(posting.amount)
            if amount == Decimal("0.0000"):
                raise LedgerError("Zero-value ledger entries are not allowed.")
            if not posting.account.is_active:
                raise LedgerError(f"Ledger account {posting.account.code} is inactive.")
            normalized_postings.append(
                LedgerPosting(
                    account=posting.account,
                    amount=amount,
                    source_tag=posting.source_tag,
                )
            )
            unit_set.add(posting.account.unit)
            total += amount
            delta_by_account[posting.account.id] += amount

        if len(unit_set) != 1:
            raise LedgerError("All postings in a transaction must use the same ledger unit.")
        if total != Decimal("0.0000"):
            raise UnbalancedTransactionError("Ledger transactions must net to zero.")

        for account_id, delta in delta_by_account.items():
            account = next(posting.account for posting in normalized_postings if posting.account.id == account_id)
            projected_balance = self.get_balance(session, account) + delta
            if projected_balance < Decimal("0.0000") and not account.allow_negative:
                raise InsufficientBalanceError(f"Account {account.code} does not have enough balance.")

        transaction_id = generate_uuid()
        entries: list[LedgerEntry] = []
        for posting in normalized_postings:
            resolved_tag = posting.source_tag or source_tag or LedgerSourceTag.ADMIN_ADJUSTMENT
            entries.append(
                LedgerEntry(
                    transaction_id=transaction_id,
                    account_id=posting.account.id,
                    created_by_user_id=actor.id if actor is not None else None,
                    amount=posting.amount,
                    unit=posting.account.unit,
                    source_tag=resolved_tag,
                    reason=reason,
                    reference=reference,
                    external_reference=external_reference,
                    description=description,
                )
            )
        session.add_all(entries)
        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.transaction.appended",
                payload={
                    "transaction_id": transaction_id,
                    "reason": reason.value,
                    "source_tag": source_tag.value if source_tag is not None else None,
                    "reference": reference,
                    "external_reference": external_reference,
                    "account_ids": [posting.account.id for posting in normalized_postings],
                },
            )
        )
        for entry in entries:
            event_name = "wallet_credit_applied" if entry.amount > 0 else "wallet_debit_applied"
            self.event_publisher.publish(
                DomainEvent(
                    name=event_name,
                    payload={
                        "transaction_id": entry.transaction_id,
                        "entry_id": entry.id,
                        "account_id": entry.account_id,
                        "owner_user_id": entry.account.owner_user_id if entry.account else None,
                        "amount": str(entry.amount),
                        "unit": entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                        "reason": entry.reason.value,
                        "source_tag": entry.source_tag.value,
                        "reference": entry.reference,
                        "external_reference": entry.external_reference,
                    },
                )
            )
        return entries

    def get_balance(self, session: Session, account: LedgerAccount) -> Decimal:
        value = session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
        )
        return self._normalize_amount(value)

    def get_wallet_summary(self, session: Session, user: User, *, currency: LedgerUnit = LedgerUnit.CREDIT) -> WalletSummary:
        available_account = self.get_user_account(session, user, currency)
        reserved_balance = self._get_user_account_balance_by_kind(session, user, currency, LedgerAccountKind.ESCROW)
        available_balance = self.get_balance(session, available_account)
        return WalletSummary(
            available_balance=available_balance,
            reserved_balance=reserved_balance,
            total_balance=self._normalize_amount(available_balance + reserved_balance),
            currency=currency,
        )

    def build_portfolio_snapshot(self, session: Session, user: User) -> PortfolioSnapshot:
        from backend.app.portfolio.service import PortfolioService

        summary = self.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
        portfolio_snapshot = PortfolioService(wallet_service=self).build_for_user(session, user)
        return PortfolioSnapshot(
            user_id=user.id,
            currency=summary.currency,
            available_balance=summary.available_balance,
            reserved_balance=summary.reserved_balance,
            total_balance=summary.total_balance,
            holdings=[asdict(holding) for holding in portfolio_snapshot.holdings],
        )

    def list_ledger_entries_for_user(
        self,
        session: Session,
        user: User,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> WalletLedgerPage:
        total = session.scalar(
            select(func.count(LedgerEntry.id))
            .select_from(LedgerEntry)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                or_(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"position:{user.id}:%"),
                )
            )
        )
        items = session.scalars(
            select(LedgerEntry)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                or_(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"position:{user.id}:%"),
                )
            )
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return WalletLedgerPage(
            page=page,
            page_size=page_size,
            total=int(total or 0),
            items=items,
        )

    def reserve_order_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        reserved_amount = self._normalize_amount(amount)
        if reserved_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-reserved_amount),
                LedgerPosting(account=escrow_account, amount=reserved_amount),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
        )

    def release_reserved_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        released_amount = self._normalize_amount(amount)
        if released_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-released_amount),
                LedgerPosting(account=available_account, amount=released_amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
        )

    def settle_reserved_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_amount = self._normalize_amount(amount)
        if settled_amount <= Decimal("0.0000"):
            return []

        escrow_account = self.get_user_escrow_account(session, user, unit)
        platform_account = self.ensure_platform_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-settled_amount),
                LedgerPosting(account=platform_account, amount=settled_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def settle_available_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_amount = self._normalize_amount(amount)
        if settled_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        platform_account = self.ensure_platform_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-settled_amount),
                LedgerPosting(account=platform_account, amount=settled_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def credit_trade_proceeds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        credited_amount = self._normalize_amount(amount)
        if credited_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        platform_account = self.ensure_platform_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=credited_amount),
                LedgerPosting(account=platform_account, amount=-credited_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def reserve_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        reserved_quantity = self._normalize_amount(quantity)
        if reserved_quantity <= Decimal("0.0000"):
            return []

        position_account = self.get_position_account(session, user, player_id)
        escrow_account = self.get_position_escrow_account(session, user, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=position_account, amount=-reserved_quantity),
                LedgerPosting(account=escrow_account, amount=reserved_quantity),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
        )

    def settle_reserved_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_quantity = self._normalize_amount(quantity)
        if settled_quantity <= Decimal("0.0000"):
            return []

        escrow_account = self.get_position_escrow_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-settled_quantity),
                LedgerPosting(account=platform_account, amount=settled_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def settle_available_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_quantity = self._normalize_amount(quantity)
        if settled_quantity <= Decimal("0.0000"):
            return []

        available_account = self.get_position_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-settled_quantity),
                LedgerPosting(account=platform_account, amount=settled_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def credit_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        credited_quantity = self._normalize_amount(quantity)
        if credited_quantity <= Decimal("0.0000"):
            return []

        position_account = self.get_position_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=position_account, amount=credited_quantity),
                LedgerPosting(account=platform_account, amount=-credited_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def get_available_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._position_account_code(user.id, player_id))
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    def get_reserved_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._position_escrow_account_code(user.id, player_id))
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    def get_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        return self._normalize_amount(
            self.get_available_position_quantity(session, user, player_id)
            + self.get_reserved_position_quantity(session, user, player_id)
        )

    def get_reserved_cash_balance(self, session: Session, user: User) -> Decimal:
        escrow_account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._user_escrow_account_code(user.id, LedgerUnit.COIN))
        )
        if escrow_account is None:
            return Decimal("0.0000")
        return self.get_balance(session, escrow_account)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _user_account_code(user_id: str, unit: LedgerUnit) -> str:
        return f"user:{user_id}:{unit.value}"

    @staticmethod
    def _position_account_code(user_id: str, player_id: str) -> str:
        return f"position:{user_id}:{player_id}:available"

    @staticmethod
    def _position_escrow_account_code(user_id: str, player_id: str) -> str:
        return f"position:{user_id}:{player_id}:escrow"

    @staticmethod
    def _platform_position_account_code(player_id: str) -> str:
        return f"platform:position:{player_id}:inventory"

    def _get_user_account_balance_by_kind(
        self,
        session: Session,
        user: User,
        unit: LedgerUnit,
        kind: LedgerAccountKind,
    ) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.owner_user_id == user.id,
                LedgerAccount.unit == unit,
                LedgerAccount.kind == kind,
            )
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    @staticmethod
    def _user_escrow_account_code(user_id: str, unit: LedgerUnit) -> str:
        return f"user:{user_id}:{unit.value}:escrow"
