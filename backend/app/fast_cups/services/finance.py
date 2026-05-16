from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.fast_cups.models.domain import FastCup, FastCupEntrant, FastCupResultSummary
from app.models.club_profile import ClubProfile
from app.models.fast_cup_finance import (
    FastCupEscrowStatus,
    FastCupPayout,
    FastCupPayoutStatus,
    FastCupRegistration,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


class FastCupFinanceError(ValueError):
    pass


@dataclass(slots=True)
class FastCupFinanceService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def build_server_entrant(self, *, cup: FastCup, actor: User, club_id: str, now: datetime) -> FastCupEntrant:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise FastCupFinanceError("club_not_found")
        if club.owner_user_id != actor.id:
            raise FastCupFinanceError("club_not_owned_by_user")
        rating = self._rating_for_club(club_id=club.id, user_id=actor.id)
        return FastCupEntrant(
            club_id=club.id,
            club_name=club.club_name,
            division=cup.division,
            rating=rating,
            registered_at=now,
        )

    def escrow_registration(self, *, cup: FastCup, actor: User, club: ClubProfile, now: datetime) -> FastCupRegistration:
        existing = self.session.scalar(
            select(FastCupRegistration).where(
                FastCupRegistration.cup_id == cup.cup_id,
                FastCupRegistration.club_id == club.id,
                FastCupRegistration.cancelled_at.is_(None),
            )
        )
        if existing is not None:
            raise FastCupFinanceError("club_already_registered")

        unit = self._ledger_unit(cup.currency)
        amount = self._amount(cup.buy_in)
        transaction_id: str | None = None
        escrow_status = FastCupEscrowStatus.NONE
        if amount > Decimal("0.0000"):
            user_account = self.wallet_service.get_user_account(self.session, actor, unit)
            escrow_account = self.wallet_service.ensure_named_system_account(
                self.session,
                code=f"fast-cup:{cup.cup_id}:{unit.value}:escrow",
                label=f"Fast Cup {cup.cup_id} {unit.value.capitalize()} Escrow",
                unit=unit,
                allow_negative=False,
            )
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=-amount,
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                    LedgerPosting(
                        account=escrow_account,
                        amount=amount,
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                ],
                reason=LedgerEntryReason.COMPETITION_ENTRY,
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                reference=f"fast-cup-entry:{cup.cup_id}:{club.id}",
                external_reference=cup.cup_id,
                description=f"Fast Cup buy-in escrow for {cup.title}",
                actor=actor,
                idempotency_key=f"fast-cup-entry:{cup.cup_id}:{club.id}:{actor.id}",
                transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                metadata={
                    "fast_cup": {
                        "cup_id": cup.cup_id,
                        "club_id": club.id,
                        "currency": unit.value,
                        "entry_fee_amount": str(amount),
                    }
                },
            )
            transaction_id = entries[0].transaction_id
            escrow_status = FastCupEscrowStatus.ESCROWED

        registration = FastCupRegistration(
            cup_id=cup.cup_id,
            user_id=actor.id,
            club_id=club.id,
            entry_fee_amount=amount,
            entry_fee_currency=unit.value,
            escrow_status=escrow_status,
            wallet_ledger_id=transaction_id,
            registered_at=now,
            metadata_json={
                "source": "fast_cup_hardening_0095",
                "server_validated": True,
                "division": cup.division.value,
                "size": cup.size,
            },
        )
        self.session.add(registration)
        self.session.flush()
        return registration

    def refund_registration(self, *, registration: FastCupRegistration, actor: User | None = None) -> FastCupRegistration:
        if registration.escrow_status == FastCupEscrowStatus.REFUNDED:
            return registration
        amount = self._amount(registration.entry_fee_amount)
        if amount <= Decimal("0.0000"):
            registration.escrow_status = FastCupEscrowStatus.REFUNDED
            registration.cancelled_at = registration.cancelled_at or datetime.now(UTC)
            self.session.flush()
            return registration
        unit = self._ledger_unit(registration.entry_fee_currency)
        user = self.session.get(User, registration.user_id)
        if user is None:
            raise FastCupFinanceError("registration_user_not_found")
        user_account = self.wallet_service.get_user_account(self.session, user, unit)
        escrow_account = self.wallet_service.ensure_named_system_account(
            self.session,
            code=f"fast-cup:{registration.cup_id}:{unit.value}:escrow",
            label=f"Fast Cup {registration.cup_id} {unit.value.capitalize()} Escrow",
            unit=unit,
            allow_negative=False,
        )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=escrow_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                    transaction_type=LedgerTransactionType.MATCH_REWARD,
                ),
                LedgerPosting(
                    account=user_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                    transaction_type=LedgerTransactionType.MATCH_REWARD,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            reference=f"fast-cup-refund:{registration.cup_id}:{registration.club_id}",
            external_reference=registration.cup_id,
            description="Fast Cup buy-in refund",
            actor=actor or user,
            idempotency_key=f"fast-cup-refund:{registration.id}",
            transaction_type=LedgerTransactionType.MATCH_REWARD,
        )
        registration.wallet_ledger_id = entries[0].transaction_id
        registration.escrow_status = FastCupEscrowStatus.REFUNDED
        registration.cancelled_at = registration.cancelled_at or datetime.now(UTC)
        self.session.flush()
        return registration

    def settle_result_summary(self, *, summary: FastCupResultSummary) -> list[FastCupPayout]:
        payouts: list[FastCupPayout] = []
        for reward in summary.rewards:
            registration = self.session.scalar(
                select(FastCupRegistration).where(
                    FastCupRegistration.cup_id == summary.cup_id,
                    FastCupRegistration.club_id == reward.club_id,
                )
            )
            if registration is None:
                continue
            payouts.append(self._settle_reward(summary=summary, registration=registration, reward=reward))
        return payouts

    def _settle_reward(self, *, summary: FastCupResultSummary, registration: FastCupRegistration, reward) -> FastCupPayout:
        idempotency_key = f"fast-cup-payout:{summary.cup_id}:{registration.id}:{reward.finish}"
        existing = self.session.scalar(select(FastCupPayout).where(FastCupPayout.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
        unit = self._ledger_unit(reward.currency)
        amount = self._amount(reward.amount)
        user = self.session.get(User, registration.user_id)
        if user is None:
            raise FastCupFinanceError("registration_user_not_found")
        user_account = self.wallet_service.get_user_account(self.session, user, unit)
        escrow_account = self.wallet_service.ensure_named_system_account(
            self.session,
            code=f"fast-cup:{summary.cup_id}:{unit.value}:escrow",
            label=f"Fast Cup {summary.cup_id} {unit.value.capitalize()} Escrow",
            unit=unit,
            allow_negative=False,
        )
        transaction_id: str | None = None
        if amount > Decimal("0.0000"):
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=escrow_account,
                        amount=-amount,
                        source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                        transaction_type=LedgerTransactionType.MATCH_REWARD,
                    ),
                    LedgerPosting(
                        account=user_account,
                        amount=amount,
                        source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                        transaction_type=LedgerTransactionType.MATCH_REWARD,
                    ),
                ],
                reason=LedgerEntryReason.COMPETITION_REWARD,
                source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                reference=f"fast-cup-payout:{summary.cup_id}:{reward.club_id}:{reward.finish}",
                external_reference=summary.cup_id,
                description=f"Fast Cup {reward.finish} payout",
                actor=user,
                idempotency_key=idempotency_key,
                transaction_type=LedgerTransactionType.MATCH_REWARD,
            )
            transaction_id = entries[0].transaction_id
        payout = FastCupPayout(
            cup_id=summary.cup_id,
            registration_id=registration.id,
            user_id=registration.user_id,
            club_id=registration.club_id,
            finish=reward.finish,
            payout_amount=amount,
            payout_currency=unit.value,
            payout_status=FastCupPayoutStatus.PAID,
            wallet_ledger_id=transaction_id,
            idempotency_key=idempotency_key,
            metadata_json={"source": "fast_cup_result_summary", "reward_club_name": reward.club_name},
            paid_at=datetime.now(UTC),
        )
        registration.escrow_status = FastCupEscrowStatus.RELEASED
        self.session.add(payout)
        self.session.flush()
        return payout

    def _ledger_unit(self, value: str) -> LedgerUnit:
        return LedgerUnit.COIN if str(value).lower() == LedgerUnit.COIN.value else LedgerUnit.CREDIT

    def _amount(self, value) -> Decimal:
        return Decimal(str(value or "0")).quantize(Decimal("0.0001"))

    def _rating_for_club(self, *, club_id: str, user_id: str) -> int:
        digest = sha256(f"{club_id}:{user_id}:fast-cup-rating".encode("utf-8")).hexdigest()
        return 1200 + (int(digest[:6], 16) % 1200)
