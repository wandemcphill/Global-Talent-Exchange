from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.wallets.service import LedgerError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class AgentLedgerAccountRef:
    agent_id: str
    unit: LedgerUnit
    account_code: str


class AgentLedgerService:
    """Ledger boundary for creator-agent economics.

    Agent accounts are system-owned accounting identities. The legacy AgentWallet
    dataclass remains a projection and must not be used as the balance authority.
    """

    def __init__(self, wallet_service: WalletService | None = None) -> None:
        self.wallet_service = wallet_service or WalletService()

    @staticmethod
    def account_code(agent_id: str, unit: LedgerUnit = LedgerUnit.COIN) -> str:
        normalized = str(agent_id).strip()
        if not normalized:
            raise LedgerError("Agent ID is required for a ledger account.")
        return f"agent:{normalized}:{unit.value}"

    def get_or_create_account(
        self,
        session: Session,
        *,
        agent_id: str,
        unit: LedgerUnit = LedgerUnit.COIN,
    ) -> LedgerAccount:
        code = self.account_code(agent_id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code).with_for_update())
        if account is not None:
            if account.unit is not unit or account.kind is not LedgerAccountKind.SYSTEM:
                raise LedgerError(f"Agent ledger account {code} has an invalid identity.")
            return account

        account = LedgerAccount(
            owner_user_id=None,
            code=code,
            label=f"Agent {agent_id} {unit.value.capitalize()} Account",
            unit=unit,
            kind=LedgerAccountKind.SYSTEM,
            allow_negative=False,
            is_active=True,
        )
        try:
            with session.begin_nested():
                session.add(account)
                session.flush()
        except IntegrityError:
            account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code).with_for_update())
            if account is None:
                raise
        if account.unit is not unit or account.kind is not LedgerAccountKind.SYSTEM:
            raise LedgerError(f"Agent ledger account {code} has an invalid identity.")
        return account

    def balance(self, session: Session, *, agent_id: str, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        account = self.get_or_create_account(session, agent_id=agent_id, unit=unit)
        return self.wallet_service.get_balance(session, account)

    def tagged_total(
        self,
        session: Session,
        *,
        agent_id: str,
        source_tag: LedgerSourceTag,
        positive_only: bool = False,
    ) -> Decimal:
        account = self.get_or_create_account(session, agent_id=agent_id, unit=LedgerUnit.COIN)
        stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account.id,
            LedgerEntry.source_tag == source_tag,
        )
        if positive_only:
            stmt = stmt.where(LedgerEntry.amount > 0)
        value = session.scalar(stmt) or 0
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    def spend(
        self,
        session: Session,
        *,
        agent_id: str,
        amount: Decimal,
        funding_sink: LedgerAccount,
        reference: str,
        actor=None,
        source_tag: LedgerSourceTag = LedgerSourceTag.AGENT_BOOST_SPEND,
        idempotency_key: str | None = None,
    ) -> str:
        amount = Decimal(str(amount)).quantize(AMOUNT_QUANTUM)
        if amount <= 0:
            raise LedgerError("Agent spend must be positive.")
        account = self.get_or_create_account(session, agent_id=agent_id, unit=funding_sink.unit)
        if funding_sink.unit is not account.unit:
            raise LedgerError("Agent spend accounts must use the same ledger currency.")
        return self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=account, amount=-amount, source_tag=source_tag),
                LedgerPosting(account=funding_sink, amount=amount, source_tag=source_tag),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=reference,
            description=f"Agent {agent_id} economic spend",
            external_reference=reference,
            actor=actor,
            idempotency_key=idempotency_key,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
        )[0].transaction_id

    def earn(
        self,
        session: Session,
        *,
        agent_id: str,
        amount: Decimal,
        funding_source: LedgerAccount,
        reference: str,
        actor=None,
        source_tag: LedgerSourceTag = LedgerSourceTag.AGENT_PERFORMANCE_EARNINGS,
        idempotency_key: str | None = None,
    ) -> str:
        amount = Decimal(str(amount)).quantize(AMOUNT_QUANTUM)
        if amount <= 0:
            raise LedgerError("Agent earnings must be positive.")
        rewards_pool = self.wallet_service.ensure_rewards_pool_account(session, funding_source.unit)
        account = self.get_or_create_account(session, agent_id=agent_id, unit=rewards_pool.unit)
        if rewards_pool.unit is not account.unit:
            raise LedgerError("Agent earnings accounts must use the same ledger currency.")
        return self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=rewards_pool, amount=-amount, source_tag=source_tag),
                LedgerPosting(account=account, amount=amount, source_tag=source_tag),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=reference,
            description=f"Agent {agent_id} economic earnings",
            external_reference=reference,
            actor=actor,
            idempotency_key=idempotency_key,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
        )[0].transaction_id


__all__ = ["AgentLedgerAccountRef", "AgentLedgerService"]
