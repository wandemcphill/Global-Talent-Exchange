from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.models.wallet import LedgerUnit


class CompetitionFundingMode(StrEnum):
    FANCOIN_ENTRY_POOL = "fancoin_entry_pool"
    HOST_FUNDED_GTEX_COIN_PRIZE = "host_funded_gtex_coin_prize"


class CompetitionFundingPolicyError(ValueError):
    """Raised when a competition funding contract violates Phase A economics."""


@dataclass(frozen=True, slots=True)
class CompetitionFundingContract:
    mode: CompetitionFundingMode
    currency: LedgerUnit
    participant_entry_amount: Decimal
    host_prize_amount: Decimal

    @property
    def participants_fund_prize(self) -> bool:
        return self.mode is CompetitionFundingMode.FANCOIN_ENTRY_POOL

    @property
    def prize_is_withdrawable(self) -> bool:
        return self.mode is CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE


_PROHIBITED_ENTRY_POOL_MODES = frozenset(
    {
        "entry_funded",
        "fancoin_entry_pool",
        "participant_funded",
        "pool",
        "dynamic",
    }
)
_ENTRY_POOL_PROHIBITED = (
    "FanCoin entry-pool competitions are prohibited. Prize coin is funded by the host or by GTEX."
)


def funding_mode_from_prize_mode(
    prize_mode: str | None,
) -> CompetitionFundingMode:
    if prize_mode is None or not str(prize_mode).strip():
        return CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE
    normalized = str(prize_mode).strip().lower()
    if normalized in _PROHIBITED_ENTRY_POOL_MODES:
        raise CompetitionFundingPolicyError(_ENTRY_POOL_PROHIBITED)
    if normalized in {
        "host_funded_fixed",
        "host_funded",
        "host_funded_gtex_coin_prize",
        "host_prize",
    }:
        return CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE
    raise CompetitionFundingPolicyError(f"Unsupported competition prize mode: {prize_mode!r}.")


def validate_competition_funding_contract(
    *,
    mode: CompetitionFundingMode | str,
    currency: LedgerUnit | str,
    participant_entry_amount: Decimal | int | float | str = Decimal("0"),
    host_prize_amount: Decimal | int | float | str = Decimal("0"),
) -> CompetitionFundingContract:
    normalized_mode = CompetitionFundingMode(str(mode).strip().lower())
    normalized_currency = LedgerUnit(str(currency).strip().lower())
    entry = _decimal(participant_entry_amount)
    host_prize = _decimal(host_prize_amount)

    if entry < 0 or host_prize < 0:
        raise CompetitionFundingPolicyError("Competition monetary amounts cannot be negative.")

    if normalized_mode is CompetitionFundingMode.FANCOIN_ENTRY_POOL:
        raise CompetitionFundingPolicyError(_ENTRY_POOL_PROHIBITED)

    if normalized_currency is not LedgerUnit.COIN:
        raise CompetitionFundingPolicyError("Host-funded prize competitions must use withdrawable GTEX Coin.")
    if entry > 0:
        raise CompetitionFundingPolicyError("Participant-funded GTEX Coin prize pools are prohibited.")
    if host_prize <= 0:
        raise CompetitionFundingPolicyError("Host-funded GTEX Coin competitions require a positive host prize amount.")

    return CompetitionFundingContract(
        mode=normalized_mode,
        currency=normalized_currency,
        participant_entry_amount=Decimal("0.0000"),
        host_prize_amount=host_prize,
    )


def _decimal(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"))


__all__ = [
    "CompetitionFundingContract",
    "CompetitionFundingMode",
    "CompetitionFundingPolicyError",
    "funding_mode_from_prize_mode",
    "validate_competition_funding_contract",
]
