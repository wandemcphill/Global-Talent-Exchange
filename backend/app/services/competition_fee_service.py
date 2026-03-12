from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from backend.app.schemas.competition_responses import CompetitionFeesView, PayoutBreakdown

_FOUR_PLACES = Decimal("0.0001")


@dataclass(slots=True)
class CompetitionFeeService:
    default_platform_fee_pct: Decimal = Decimal("0.10")
    default_host_fee_pct: Decimal = Decimal("0.00")

    def resolve_fees(
        self,
        *,
        entry_fee: Decimal,
        participant_count: int,
        platform_fee_pct: Decimal | None = None,
        host_fee_pct: Decimal | None = None,
    ) -> CompetitionFeesView:
        effective_platform = platform_fee_pct if platform_fee_pct is not None else self.default_platform_fee_pct
        effective_host = host_fee_pct if host_fee_pct is not None else self.default_host_fee_pct
        gross_pool = (entry_fee * Decimal(participant_count)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
        platform_fee = (gross_pool * effective_platform).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
        host_fee = (gross_pool * effective_host).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
        prize_pool = (gross_pool - platform_fee - host_fee).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
        return CompetitionFeesView(
            entry_fee=entry_fee,
            platform_fee_pct=effective_platform,
            platform_fee_amount=platform_fee,
            host_fee_pct=effective_host,
            host_fee_amount=host_fee,
            prize_pool=prize_pool,
        )

    def build_payouts(
        self,
        *,
        prize_pool: Decimal,
        payout_structure: tuple[tuple[int, Decimal], ...],
    ) -> tuple[PayoutBreakdown, ...]:
        payouts: list[PayoutBreakdown] = []
        for place, percent in payout_structure:
            amount = (prize_pool * percent).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
            payouts.append(PayoutBreakdown(place=place, percent=percent, amount=amount))
        return tuple(payouts)
