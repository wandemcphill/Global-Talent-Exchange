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


def funding_mode_from_prize_mode(prize_mode: str | None) -> CompetitionFundingMode:
    normalized = (prize_mode or "entry_funded").strip().lower()
    if normalized in {
        "host_funded_fixed",
        "host_funded",
        "host_funded_gtex_coin_prize",
        "host_prize",
    }:
        return CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE
    if normalized in {
        "entry_funded",
        "fancoin_entry_pool",
        "participant_funded",
        "pool",
        "dynamic",
    }:
        return CompetitionFundingMode.FANCOIN_ENTRY_POOL
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
        if normalized_currency is not LedgerUnit.CREDIT:
            raise CompetitionFundingPolicyError(
                "FanCoin entry-pool competitions must use FanCoin/CREDIT."
            )
        if host_prize > 0:
            raise CompetitionFundingPolicyError(
                "FanCoin entry-pool competitions cannot also carry a host-funded prize."
            )
        return CompetitionFundingContract(
            mode=normalized_mode,
            currency=normalized_currency,
            participant_entry_amount=entry,
            host_prize_amount=Decimal("0.0000"),
        )

    if normalized_currency is not LedgerUnit.COIN:
        raise CompetitionFundingPolicyError(
            "Host-funded prize competitions must use withdrawable GTEX Coin."
        )
    if entry > 0:
        raise CompetitionFundingPolicyError(
            "Participant-funded GTEX Coin prize pools are prohibited."
        )
    if host_prize <= 0:
        raise CompetitionFundingPolicyError(
            "Host-funded GTEX Coin competitions require a positive host prize amount."
        )

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
