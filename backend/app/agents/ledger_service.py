from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
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

    def spend(
        self,
        session: Session,
        *,
        agent_id: str,
        amount: Decimal,
        funding_sink: LedgerAccount,
        reference: str,
        actor=None,
        source_tag: LedgerSourceTag = LedgerSourceTag.VIDEO_VIEW_SPEND,
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
        source_tag: LedgerSourceTag = LedgerSourceTag.CREATOR_CLIP_REVENUE,
        idempotency_key: str | None = None,
    ) -> str:
        amount = Decimal(str(amount)).quantize(AMOUNT_QUANTUM)
        if amount <= 0:
            raise LedgerError("Agent earnings must be positive.")
        account = self.get_or_create_account(session, agent_id=agent_id, unit=funding_source.unit)
        if funding_source.unit is not account.unit:
            raise LedgerError("Agent earnings accounts must use the same ledger currency.")
        return self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=funding_source, amount=-amount, source_tag=source_tag),
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
