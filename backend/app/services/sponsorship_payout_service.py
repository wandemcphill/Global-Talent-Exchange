from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import ceil
from uuid import uuid4

from app.common.enums.sponsorship_status import SponsorshipStatus
from app.schemas.sponsorship_core import ClubSponsorshipContractView, ClubSponsorshipPayoutView
from app.services.club_finance_service import ClubFinanceService, get_club_finance_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SponsorshipPayoutService:
    def __init__(self, *, finance_service: ClubFinanceService | None = None) -> None:
        self.finance_service = finance_service or get_club_finance_service()

    def build_schedule(
        self,
        *,
        contract_id: str,
        total_amount_minor: int,
        duration_months: int,
        payout_schedule: str,
        start_at: datetime,
    ) -> tuple[ClubSponsorshipPayoutView, ...]:
        if payout_schedule == "upfront":
            period_count = 1
            spacing_days = 0
        elif payout_schedule == "quarterly":
            period_count = max(1, ceil(duration_months / 3))
            spacing_days = 90
        else:
            period_count = max(1, duration_months)
            spacing_days = 30

        base_amount = total_amount_minor // period_count
        remainder = total_amount_minor % period_count
        payouts: list[ClubSponsorshipPayoutView] = []
        for index in range(period_count):
            payouts.append(
                ClubSponsorshipPayoutView(
                    id=f"pay-{uuid4().hex[:12]}",
                    contract_id=contract_id,
                    due_at=start_at + timedelta(days=spacing_days * index),
                    amount_minor=base_amount + (1 if index < remainder else 0),
                    status="pending",
                    settled_at=None,
                )
            )
        return tuple(payouts)

    def settle_due_payouts(
        self,
        *,
        club_id: str,
        contract: ClubSponsorshipContractView,
        payouts: tuple[ClubSponsorshipPayoutView, ...],
        as_of: datetime | None = None,
    ) -> tuple[ClubSponsorshipPayoutView, ...]:
        settled_at = as_of or _utcnow()
        if contract.status != SponsorshipStatus.ACTIVE:
            contract.payouts = payouts
            contract.settled_amount_minor = sum(payout.amount_minor for payout in payouts if payout.status == "settled")
            contract.outstanding_amount_minor = max(0, contract.contract_amount_minor - contract.settled_amount_minor)
            return payouts

        for payout in payouts:
            if payout.status == "pending" and payout.due_at <= settled_at:
                payout.status = "settled"
                payout.settled_at = settled_at
                self.finance_service.record_sponsorship_credit(
                    club_id,
                    amount_minor=payout.amount_minor,
                    reference_id=contract.id,
                    description=f"Sponsorship payout from {contract.sponsor_name} posted to the club budget.",
                )

        contract.payouts = payouts
        contract.settled_amount_minor = sum(payout.amount_minor for payout in payouts if payout.status == "settled")
        contract.outstanding_amount_minor = max(0, contract.contract_amount_minor - contract.settled_amount_minor)
        if contract.outstanding_amount_minor == 0 and contract.status == SponsorshipStatus.ACTIVE:
            contract.status = SponsorshipStatus.COMPLETED
        return payouts


@lru_cache
def get_sponsorship_payout_service() -> SponsorshipPayoutService:
    return SponsorshipPayoutService(finance_service=get_club_finance_service())


__all__ = ["SponsorshipPayoutService", "get_sponsorship_payout_service"]
