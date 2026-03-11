from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.user import User
from backend.app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
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


class WalletService:
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
            .where(LedgerAccount.owner_user_id == user.id)
            .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
        ).all()
        if not accounts:
            self.ensure_default_accounts(session, user)
            accounts = session.scalars(
                select(LedgerAccount)
                .where(LedgerAccount.owner_user_id == user.id)
                .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
            ).all()
        return accounts

    def get_user_account(self, session: Session, user: User, unit: LedgerUnit) -> LedgerAccount:
        code = self._user_account_code(user.id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = self.ensure_default_accounts(session, user)[unit]
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
        return event

    def verify_payment_event(self, session: Session, payment_event: PaymentEvent, *, actor: User | None = None) -> PaymentEvent:
        if payment_event.status != PaymentStatus.PENDING:
            raise LedgerError("Only pending payment events can be verified.")

        user = session.get(User, payment_event.user_id)
        if user is None:
            raise LedgerError("Payment event references a missing user.")

        user_account = self.get_user_account(session, user, payment_event.unit)
        platform_account = self.ensure_platform_account(session, payment_event.unit)
        entries = self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=payment_event.amount),
                LedgerPosting(account=platform_account, amount=-payment_event.amount),
            ],
            reason=LedgerEntryReason.DEPOSIT,
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
        return payment_event

    def append_transaction(
        self,
        session: Session,
        *,
        postings: list[LedgerPosting],
        reason: LedgerEntryReason,
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
            normalized_postings.append(LedgerPosting(account=posting.account, amount=amount))
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
        entries = [
            LedgerEntry(
                transaction_id=transaction_id,
                account_id=posting.account.id,
                created_by_user_id=actor.id if actor is not None else None,
                amount=posting.amount,
                unit=posting.account.unit,
                reason=reason,
                reference=reference,
                external_reference=external_reference,
                description=description,
            )
            for posting in normalized_postings
        ]
        session.add_all(entries)
        session.flush()
        return entries

    def get_balance(self, session: Session, account: LedgerAccount) -> Decimal:
        value = session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
        )
        return self._normalize_amount(value)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _user_account_code(user_id: str, unit: LedgerUnit) -> str:
        return f"user:{user_id}:{unit.value}"
