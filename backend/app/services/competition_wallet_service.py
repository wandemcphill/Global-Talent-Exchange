from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competition import Competition
from app.models.competition_reward import CompetitionReward
from app.models.competition_wallet_ledger import CompetitionWalletLedger
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
)
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class CompetitionWalletResult:
    status: str
    transaction_id: str | None = None
    reason: str | None = None
    escrow_used_minor: int = 0
    platform_backstop_minor: int = 0


@dataclass(slots=True)
class CompetitionWalletService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)

    def collect_entry_fee(self, *, competition: Competition, participant_user_id: str) -> CompetitionWalletResult:
        amount_minor = max(int(competition.entry_fee_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="free")
        user = self.session.get(User, participant_user_id)
        if user is None or not user.is_active:
            raise InsufficientBalanceError("Competition entry requires an active wallet user.")

        amount = self._minor_to_decimal(amount_minor)
        user_account = self.wallet_service.get_user_account(
            self.session,
            user,
            self._ledger_unit_for_currency(competition.currency),
        )
        if self.wallet_service.get_balance(self.session, user_account) < amount:
            raise InsufficientBalanceError("Available balance is lower than the competition entry fee.")
        escrow_account = self.ensure_competition_escrow_account(competition)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=user_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            reference=f"competition-entry:{competition.id}:{user.id}",
            description=f"Competition entry for {competition.name}",
            external_reference=f"competition-entry:{competition.id}:{user.id}",
            actor=user,
            idempotency_key=f"competition-entry:{competition.id}:{user.id}",
        )
        transaction_id = entries[0].transaction_id if entries else None
        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type="entry_fee_collection",
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=participant_user_id,
            payload_json={"status": "settled", "transaction_id": transaction_id},
        )
        return CompetitionWalletResult(status="settled", transaction_id=transaction_id, escrow_used_minor=amount_minor)

    def refund_entry_fee(
        self,
        *,
        competition: Competition,
        participant_user_id: str,
        amount_minor: int,
    ) -> CompetitionWalletResult:
        amount_minor = max(int(amount_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="free")
        user = self.session.get(User, participant_user_id)
        if user is None or not user.is_active:
            return CompetitionWalletResult(status="unavailable", reason="missing_wallet_user")
        amount = self._minor_to_decimal(amount_minor)
        unit = self._ledger_unit_for_currency(competition.currency)
        escrow_account = self.ensure_competition_escrow_account(competition)
        recipient_account = self.wallet_service.get_user_account(self.session, user, unit)
        if self.wallet_service.get_balance(self.session, escrow_account) < amount:
            raise InsufficientBalanceError("Competition escrow balance is lower than the refundable entry fee.")
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=recipient_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            reference=f"competition-entry-refund:{competition.id}:{user.id}",
            description=f"Competition entry refund for {competition.name}",
            external_reference=f"competition-entry-refund:{competition.id}:{user.id}",
            actor=user,
            idempotency_key=f"competition-entry-refund:{competition.id}:{user.id}",
        )
        transaction_id = entries[0].transaction_id if entries else None
        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type="entry_fee_refund",
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=participant_user_id,
            payload_json={"status": "refunded", "transaction_id": transaction_id},
        )
        return CompetitionWalletResult(status="refunded", transaction_id=transaction_id)

    def escrow_host_funding(
        self,
        *,
        competition: Competition,
        host_user_id: str,
        amount_minor: int,
    ) -> CompetitionWalletResult:
        amount_minor = max(int(amount_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="skipped", reason="zero_amount")
        existing = self._existing_competition_ledger(competition.id, "host_funded_prize_escrow")
        if existing is not None:
            payload = dict(existing.payload_json or {})
            return CompetitionWalletResult(
                status=str(payload.get("status") or "settled"),
                transaction_id=(
                    payload.get("transaction_id") if isinstance(payload.get("transaction_id"), str) else None
                ),
                escrow_used_minor=amount_minor,
            )
        user = self.session.get(User, host_user_id)
        if user is None or not user.is_active:
            raise InsufficientBalanceError("Host-funded competitions require an active host wallet.")
        unit = self._ledger_unit_for_currency(competition.currency)
        amount = self._minor_to_decimal(amount_minor)
        user_account = self.wallet_service.get_user_account(self.session, user, unit)
        if self.wallet_service.get_balance(self.session, user_account) < amount:
            raise InsufficientBalanceError("Host wallet balance is lower than the advertised prize funding.")
        escrow_account = self.ensure_competition_escrow_account(competition)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=user_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
            reference=f"competition-host-funding:{competition.id}:{user.id}",
            description=f"Host-funded prize escrow for {competition.name}",
            external_reference=f"competition-host-funding:{competition.id}:{user.id}",
            actor=user,
            idempotency_key=f"competition-host-funding:{competition.id}:{user.id}",
        )
        transaction_id = entries[0].transaction_id if entries else None
        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type="host_funded_prize_escrow",
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=host_user_id,
            payload_json={"status": "settled", "transaction_id": transaction_id},
        )
        return CompetitionWalletResult(status="settled", transaction_id=transaction_id, escrow_used_minor=amount_minor)

    def refund_host_funding(
        self,
        *,
        competition: Competition,
        host_user_id: str,
        amount_minor: int,
    ) -> CompetitionWalletResult:
        amount_minor = max(int(amount_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="skipped", reason="zero_amount")
        existing = self._existing_competition_ledger(competition.id, "host_funded_prize_refund")
        if existing is not None:
            payload = dict(existing.payload_json or {})
            return CompetitionWalletResult(
                status=str(payload.get("status") or "refunded"),
                transaction_id=(
                    payload.get("transaction_id") if isinstance(payload.get("transaction_id"), str) else None
                ),
                escrow_used_minor=amount_minor,
            )
        user = self.session.get(User, host_user_id)
        if user is None or not user.is_active:
            return CompetitionWalletResult(status="unavailable", reason="missing_wallet_user")
        unit = self._ledger_unit_for_currency(competition.currency)
        amount = self._minor_to_decimal(amount_minor)
        escrow_account = self.ensure_competition_escrow_account(competition)
        recipient_account = self.wallet_service.get_user_account(self.session, user, unit)
        if self.wallet_service.get_balance(self.session, escrow_account) < amount:
            raise InsufficientBalanceError("Competition escrow balance is lower than the host-funded prize refund.")
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=recipient_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
            reference=f"competition-host-funding-refund:{competition.id}:{user.id}",
            description=f"Host-funded prize refund for {competition.name}",
            external_reference=f"competition-host-funding-refund:{competition.id}:{user.id}",
            actor=user,
            idempotency_key=f"competition-host-funding-refund:{competition.id}:{user.id}",
        )
        transaction_id = entries[0].transaction_id if entries else None
        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type="host_funded_prize_refund",
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=host_user_id,
            payload_json={"status": "refunded", "transaction_id": transaction_id},
        )
        return CompetitionWalletResult(status="refunded", transaction_id=transaction_id)

    def settle_reward(
        self,
        *,
        competition: Competition,
        reward: CompetitionReward,
        recipient: User,
        actor: User | None = None,
    ) -> CompetitionWalletResult:
        if reward.ledger_transaction_id:
            return CompetitionWalletResult(status="settled", transaction_id=reward.ledger_transaction_id)
        amount_minor = max(int(reward.amount_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="skipped", reason="zero_amount")
        unit = self._ledger_unit_for_currency(competition.currency)
        target_account = self.wallet_service.get_user_account(self.session, recipient, unit)
        amount = self._minor_to_decimal(amount_minor)
        escrow_used_minor, backstop_minor, funding_postings = self._funding_postings(
            competition=competition,
            amount_minor=amount_minor,
            target_account=target_account,
        )
        if self._is_user_hosted_competition(competition) and backstop_minor > 0:
            raise InsufficientBalanceError("Competition escrow balance is lower than the reward amount.")
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=target_account,
                    amount=amount,
                    source_tag=self._reward_source_tag(unit),
                ),
                *funding_postings,
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=self._reward_source_tag(unit),
            reference=f"competition-reward:{competition.id}:{reward.id}",
            description=f"Competition reward for {competition.name}",
            external_reference=f"competition-reward:{competition.id}:{reward.id}",
            actor=actor or recipient,
            idempotency_key=f"competition-reward:{reward.id}",
        )
        transaction_id = entries[0].transaction_id if entries else None
        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type="reward_payout",
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=reward.id,
            payload_json={
                "transaction_id": transaction_id,
                "recipient_user_id": recipient.id,
                "placement": reward.placement,
                "escrow_used_minor": escrow_used_minor,
                "platform_backstop_minor": backstop_minor,
            },
        )
        return CompetitionWalletResult(
            status="settled",
            transaction_id=transaction_id,
            escrow_used_minor=escrow_used_minor,
            platform_backstop_minor=backstop_minor,
        )

    def settle_fee_distribution(
        self, *, competition: Competition, entry_type: str, amount_minor: int
    ) -> CompetitionWalletResult:
        amount_minor = max(int(amount_minor or 0), 0)
        if amount_minor <= 0:
            return CompetitionWalletResult(status="skipped", reason="zero_amount")
        existing = self._existing_competition_ledger(competition.id, entry_type)
        if existing is not None:
            payload = dict(existing.payload_json or {})
            return CompetitionWalletResult(
                status="settled",
                transaction_id=payload.get("transaction_id"),
                escrow_used_minor=int(payload.get("escrow_used_minor") or 0),
                platform_backstop_minor=int(payload.get("platform_backstop_minor") or 0),
            )

        unit = self._ledger_unit_for_currency(competition.currency)
        platform_account = self.wallet_service.ensure_platform_account(self.session, unit)
        if entry_type == "host_fee_distribution":
            host_user = self.session.get(User, competition.host_user_id) if competition.host_user_id else None
            target_account = (
                self.wallet_service.get_user_account(self.session, host_user, unit)
                if host_user is not None and host_user.is_active
                else platform_account
            )
            actor = host_user
        else:
            target_account = platform_account
            actor = self.session.get(User, competition.host_user_id) if competition.host_user_id else None

        escrow_used_minor, backstop_minor, funding_postings = self._funding_postings(
            competition=competition,
            amount_minor=amount_minor,
            target_account=target_account,
        )
        transaction_id = None
        if target_account.id != platform_account.id or escrow_used_minor > 0:
            payout_minor = amount_minor if target_account.id != platform_account.id else escrow_used_minor
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=target_account,
                        amount=self._minor_to_decimal(payout_minor),
                        source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                    ),
                    *funding_postings,
                ],
                reason=LedgerEntryReason.COMPETITION_REWARD,
                source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                reference=f"competition-fee:{competition.id}:{entry_type}",
                description=f"Competition fee settlement for {competition.name}",
                external_reference=f"competition-fee:{competition.id}:{entry_type}",
                actor=actor,
                idempotency_key=f"competition-fee:{competition.id}:{entry_type}",
            )
            transaction_id = entries[0].transaction_id if entries else None

        self._record_competition_ledger(
            competition_id=competition.id,
            entry_type=entry_type,
            amount_minor=amount_minor,
            currency=competition.currency,
            reference_id=competition.host_user_id,
            payload_json={
                "transaction_id": transaction_id,
                "escrow_used_minor": escrow_used_minor,
                "platform_backstop_minor": backstop_minor,
                "destination_account": target_account.code,
            },
        )
        return CompetitionWalletResult(
            status="settled",
            transaction_id=transaction_id,
            escrow_used_minor=escrow_used_minor,
            platform_backstop_minor=backstop_minor,
        )

    def ensure_competition_escrow_account(self, competition: Competition) -> LedgerAccount:
        code = f"competition:{competition.id}:{self._ledger_unit_for_currency(competition.currency).value}:escrow"
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"{competition.name} Competition Escrow",
                unit=self._ledger_unit_for_currency(competition.currency),
                kind=LedgerAccountKind.ESCROW,
            )
            self.session.add(account)
            self.session.flush()
        return account

    def _funding_postings(
        self,
        *,
        competition: Competition,
        amount_minor: int,
        target_account: LedgerAccount,
    ) -> tuple[int, int, list[LedgerPosting]]:
        unit = self._ledger_unit_for_currency(competition.currency)
        platform_account = self.wallet_service.ensure_platform_account(self.session, unit)
        escrow_account = self.ensure_competition_escrow_account(competition)
        escrow_available_minor = self._decimal_to_minor(self.wallet_service.get_balance(self.session, escrow_account))
        escrow_used_minor = min(amount_minor, escrow_available_minor)
        backstop_minor = max(amount_minor - escrow_used_minor, 0)
        postings: list[LedgerPosting] = []
        if escrow_used_minor > 0:
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-self._minor_to_decimal(escrow_used_minor),
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                )
            )
        if backstop_minor > 0 and target_account.id != platform_account.id:
            postings.append(
                LedgerPosting(
                    account=platform_account,
                    amount=-self._minor_to_decimal(backstop_minor),
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                )
            )
        return escrow_used_minor, backstop_minor, postings

    def _existing_competition_ledger(self, competition_id: str, entry_type: str) -> CompetitionWalletLedger | None:
        return self.session.scalar(
            select(CompetitionWalletLedger).where(
                CompetitionWalletLedger.competition_id == competition_id,
                CompetitionWalletLedger.entry_type == entry_type,
            )
        )

    def _record_competition_ledger(
        self,
        *,
        competition_id: str,
        entry_type: str,
        amount_minor: int,
        currency: str,
        reference_id: str | None,
        payload_json: dict[str, object],
    ) -> None:
        if self._existing_competition_ledger(competition_id, entry_type) is not None and entry_type in {
            "host_fee_distribution",
            "platform_fee_distribution",
        }:
            return
        self.session.add(
            CompetitionWalletLedger(
                competition_id=competition_id,
                entry_type=entry_type,
                amount_minor=amount_minor,
                currency=currency,
                reference_id=reference_id,
                payload_json=payload_json,
            )
        )
        self.session.flush()

    @staticmethod
    def _ledger_unit_for_currency(currency: str) -> LedgerUnit:
        normalized = (currency or "credit").strip().lower()
        return LedgerUnit.COIN if normalized == LedgerUnit.COIN.value else LedgerUnit.CREDIT

    @staticmethod
    def _reward_source_tag(unit: LedgerUnit) -> LedgerSourceTag:
        return (
            LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN
            if unit is LedgerUnit.CREDIT
            else LedgerSourceTag.PLATFORM_COMPETITION_REWARD
        )

    @staticmethod
    def _is_user_hosted_competition(competition: Competition) -> bool:
        normalized = (competition.source_type or "").strip().lower()
        return normalized in {"user", "user_hosted", "creator", "creator_hosted"}

    @staticmethod
    def _minor_to_decimal(amount_minor: int) -> Decimal:
        return (Decimal(amount_minor) / Decimal("10000")).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _decimal_to_minor(amount: Decimal) -> int:
        return int((Decimal(amount).quantize(AMOUNT_QUANTUM)) * Decimal("10000"))


__all__ = ["CompetitionWalletResult", "CompetitionWalletService"]
