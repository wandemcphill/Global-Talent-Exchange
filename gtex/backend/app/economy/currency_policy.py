from __future__ import annotations

from dataclasses import dataclass

from app.models.wallet import LedgerUnit


class CurrencyPolicyError(ValueError):
    """Raised when a GTEX currency operation violates the economic constitution."""


FANCOIN = LedgerUnit.CREDIT
GTEX_COIN = LedgerUnit.COIN


@dataclass(frozen=True, slots=True)
class GiftCurrencyPolicy:
    source_unit: LedgerUnit = FANCOIN
    destination_unit: LedgerUnit = GTEX_COIN

    def validate_source(self, unit: LedgerUnit) -> None:
        if unit is not self.source_unit:
            raise CurrencyPolicyError("Gifts may only be funded with GTEX FanCoin.")

    def destination(self) -> LedgerUnit:
        return self.destination_unit


GIFT_CURRENCY_POLICY = GiftCurrencyPolicy()


def assert_fancoin(unit: LedgerUnit) -> None:
    if unit is not FANCOIN:
        raise CurrencyPolicyError("This operation requires GTEX FanCoin.")


def assert_gtex_coin(unit: LedgerUnit) -> None:
    if unit is not GTEX_COIN:
        raise CurrencyPolicyError("This operation requires GTEX Coin.")


def assert_not_giftable(unit: LedgerUnit) -> None:
    if unit is GTEX_COIN:
        raise CurrencyPolicyError("GTEX Coin cannot be gifted.")


def gift_source_unit() -> LedgerUnit:
    return GIFT_CURRENCY_POLICY.source_unit


def gift_destination_unit() -> LedgerUnit:
    return GIFT_CURRENCY_POLICY.destination()


def is_withdrawable(unit: LedgerUnit) -> bool:
    """GTEX Coin is the withdrawable economic currency; FanCoin is not."""
    return unit is GTEX_COIN


def is_consumption_currency(unit: LedgerUnit) -> bool:
    """FanCoin is the platform consumption/gifting currency."""
    return unit is FANCOIN


__all__ = [
    "CurrencyPolicyError",
    "FANCOIN",
    "GTEX_COIN",
    "GiftCurrencyPolicy",
    "GIFT_CURRENCY_POLICY",
    "assert_fancoin",
    "assert_gtex_coin",
    "assert_not_giftable",
    "gift_source_unit",
    "gift_destination_unit",
    "is_withdrawable",
    "is_consumption_currency",
]
