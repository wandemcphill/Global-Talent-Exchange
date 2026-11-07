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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(frozen=True, slots=True)
class AgentSettlementDecision:
    realized_earnings: float
    approved: bool
    reason: str
    quality_score: float
    trust_score: float
    decay_multiplier: float
    payout_eligible: bool = False


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

    min_quality_threshold: float = 0.58
    min_trust_threshold: float = 0.60
    min_decay_multiplier: float = 0.25

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

    def evaluate_settlement(
        self,
        *,
        earnings: float,
        quality_score: float,
        trust_score: float,
        repetition_ratio: float,
    ) -> AgentSettlementDecision:
        normalized_quality = _clamp(quality_score, 0.0, 1.0)
        normalized_trust = _clamp(trust_score, 0.0, 1.0)
        normalized_repetition = _clamp(repetition_ratio, 0.0, 1.0)
        decay_multiplier = round(
            max(1.0 - (normalized_repetition * 0.75), self.min_decay_multiplier),
            4,
        )
        if normalized_trust < self.min_trust_threshold:
            realized = 0.0
            approved = False
            reason = "trust_score_below_floor"
        elif normalized_quality < self.min_quality_threshold:
            realized = 0.0
            approved = False
            reason = "quality_below_floor"
        else:
            realized = max(round(float(earnings) * decay_multiplier, 2), 0.0)
            approved = True
            reason = "approved" if decay_multiplier >= 0.99 else "repetition_decay"

        # Payout eligibility is ALWAYS False by default until explicitly authorized (Requirement 9)
        return AgentSettlementDecision(
            realized_earnings=realized,
            approved=approved,
            reason=reason,
            quality_score=round(normalized_quality, 4),
            trust_score=round(normalized_trust, 4),
            decay_multiplier=decay_multiplier,
            payout_eligible=False,
        )

    def settle(
        self,
        session: Session,
        *,
        agent_id: str,
        earnings: float,
        quality_score: float,
        trust_score: float,
        repetition_ratio: float,
        reference: str,
        actor=None,
    ) -> AgentSettlementDecision:
        decision = self.evaluate_settlement(
            earnings=earnings,
            quality_score=quality_score,
            trust_score=trust_score,
            repetition_ratio=repetition_ratio,
        )
        if decision.approved and decision.realized_earnings > 0.0:
            rewards_pool = self.wallet_service.ensure_rewards_pool_account(session, LedgerUnit.COIN)
            self.earn(
                session,
                agent_id=agent_id,
                amount=Decimal(str(decision.realized_earnings)),
                funding_source=rewards_pool,
                reference=reference,
                actor=actor,
                source_tag=LedgerSourceTag.AGENT_PERFORMANCE_EARNINGS,
                idempotency_key=reference,
            )
        return decision


__all__ = ["AgentLedgerAccountRef", "AgentLedgerService", "AgentSettlementDecision"]
