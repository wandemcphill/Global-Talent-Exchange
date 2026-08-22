from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hosted_competition import UserHostedCompetition
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")

class HostedCompetitionCoinEscrowError(ValueError):
    """Raised when a host-funded GTEX Coin prize cannot be escrowed or settled."""

@dataclass(slots=True)
class HostedCompetitionCoinEscrowService:
    session: Session
    wallet_service: WalletService

    def _amount(self, value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    def escrow_account(self, competition: UserHostedCompetition) -> LedgerAccount:
        code = f"competition:{competition.id}:coin:escrow"
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"{competition.title} GTEX Coin Prize Escrow",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.ESCROW,
            )
            self.session.add(account)
            self.session.flush()
        elif account.unit is not LedgerUnit.COIN:
            raise HostedCompetitionCoinEscrowError("Hosted competition Coin escrow account has the wrong currency.")
        return account

    def available_balance(self, competition: UserHostedCompetition) -> Decimal:
        return self._amount(self.wallet_service.get_balance(self.session, self.escrow_account(competition)))

    def fund_from_host(self, *, competition: UserHostedCompetition, host: User, gross_prize: Decimal | int | float | str) -> str:
        amount = self._amount(gross_prize)
        if amount <= Decimal("0.0000"):
            raise HostedCompetitionCoinEscrowError("Host-funded GTEX Coin prize must be positive.")
        account = self.wallet_service.get_user_account(self.session, host, LedgerUnit.COIN)
        if self.wallet_service.get_balance(self.session, account) < amount:
            raise InsufficientBalanceError("Host does not have enough withdrawable GTEX Coin to fund the prize.")
        escrow = self.escrow_account(competition)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=account, amount=-amount, source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD),
                LedgerPosting(account=escrow, amount=amount, source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f"hosted-coin-prize-fund:{competition.id}",
            external_reference=f"hosted-coin-prize-fund:{competition.id}",
            description=f"Host-funded GTEX Coin prize for {competition.title}",
            actor=host,
            idempotency_key=f"hosted-coin-prize-fund:{competition.id}",
            metadata={"hosted_competition_id": competition.id, "currency": LedgerUnit.COIN.value, "funding_mode": "host_funded_gtex_coin_prize"},
        )
        competition.host_funding_required_coin = amount
        competition.host_funding_escrowed_coin = amount
        competition.reward_pool_coin = amount
        self.session.flush()
        return entries[0].transaction_id

    def settle(self, *, competition: UserHostedCompetition, winner: User, net_prize: Decimal | int | float | str, platform_fee: Decimal | int | float | str, actor: User) -> str:
        return self.settle_distribution(
            competition=competition,
            payouts=[(winner, self._amount(net_prize))],
            platform_fee=platform_fee,
            actor=actor,
        )

    def settle_distribution(self, *, competition: UserHostedCompetition, payouts: list[tuple[User, Decimal]], platform_fee: Decimal | int | float | str, actor: User) -> str:
        fee = self._amount(platform_fee)
        if fee < Decimal("0.0000"):
            raise HostedCompetitionCoinEscrowError("Platform fee cannot be negative.")
        if not payouts:
            raise HostedCompetitionCoinEscrowError("At least one GTEX Coin payout is required.")
        normalized_payouts: list[tuple[User, Decimal]] = []
        total_payout = Decimal("0.0000")
        for winner, raw_amount in payouts:
            payout = self._amount(raw_amount)
            if payout <= Decimal("0.0000"):
                raise HostedCompetitionCoinEscrowError("GTEX Coin payout must be positive.")
            normalized_payouts.append((winner, payout))
            total_payout += payout
        required = self._amount(total_payout + fee)
        escrow_balance = self.available_balance(competition)
        if required > escrow_balance:
            raise HostedCompetitionCoinEscrowError("GTEX Coin settlement exceeds escrow balance.")
        escrow = self.escrow_account(competition)
        platform = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        postings: list[LedgerPosting] = []
        for winner, payout in normalized_payouts:
            recipient = self.wallet_service.get_user_account(self.session, winner, LedgerUnit.COIN)
            postings.extend([
                LedgerPosting(account=escrow, amount=-payout, source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD),
                LedgerPosting(account=recipient, amount=payout, source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD),
            ])
        if fee > Decimal("0.0000"):
            postings.extend([
                LedgerPosting(account=escrow, amount=-fee, source_tag=LedgerSourceTag.HOSTING_FEE_SPEND),
                LedgerPosting(account=platform, amount=fee, source_tag=LedgerSourceTag.HOSTING_FEE_SPEND),
            ])
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f"hosted-coin-prize-settlement:{competition.id}",
            external_reference=f"hosted-coin-prize-settlement:{competition.id}",
            description=f"GTEX Coin prize settlement for {competition.title}",
            actor=actor,
            idempotency_key=f"hosted-coin-prize-settlement:{competition.id}",
            metadata={
                "hosted_competition_id": competition.id,
                "currency": LedgerUnit.COIN.value,
                "funding_mode": "host_funded_gtex_coin_prize",
                "winner_user_ids": [winner.id for winner, _ in normalized_payouts],
                "gross_prize": str(total_payout + fee),
                "platform_fee": str(fee),
                "net_prize": str(total_payout),
            },
        )
        competition.host_funding_escrowed_coin = self._amount(escrow_balance - required)
        self.session.flush()
        return entries[0].transaction_id

__all__ = ["HostedCompetitionCoinEscrowError", "HostedCompetitionCoinEscrowService"]
