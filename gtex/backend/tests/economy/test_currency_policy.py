from app.economy.currency_policy import (
    CurrencyPolicyError,
    assert_fancoin,
    assert_gtex_coin,
    assert_not_giftable,
    gift_destination_unit,
    gift_source_unit,
    is_consumption_currency,
    is_withdrawable,
)
from app.models.wallet import LedgerUnit


def test_fancoin_is_consumption_currency_and_not_withdrawable() -> None:
    assert gift_source_unit() is LedgerUnit.CREDIT
    assert is_consumption_currency(LedgerUnit.CREDIT) is True
    assert is_withdrawable(LedgerUnit.CREDIT) is False


def test_gtex_coin_is_withdrawable_and_not_consumption_currency() -> None:
    assert gift_destination_unit() is LedgerUnit.COIN
    assert is_withdrawable(LedgerUnit.COIN) is True
    assert is_consumption_currency(LedgerUnit.COIN) is False


def test_gifts_require_fancoin() -> None:
    assert_fancoin(LedgerUnit.CREDIT)
    try:
        assert_fancoin(LedgerUnit.COIN)
    except CurrencyPolicyError as exc:
        assert "FanCoin" in str(exc)
    else:
        raise AssertionError("GTEX Coin must not be accepted as gift funding")


def test_gtex_coin_cannot_be_gifted() -> None:
    assert_not_giftable(LedgerUnit.CREDIT)
    try:
        assert_not_giftable(LedgerUnit.COIN)
    except CurrencyPolicyError as exc:
        assert "cannot be gifted" in str(exc)
    else:
        raise AssertionError("GTEX Coin gifting must be rejected")


def test_gtex_coin_requirement_is_explicit() -> None:
    assert_gtex_coin(LedgerUnit.COIN)
    try:
        assert_gtex_coin(LedgerUnit.CREDIT)
    except CurrencyPolicyError as exc:
        assert "GTEX Coin" in str(exc)
    else:
        raise AssertionError("FanCoin must not satisfy a GTEX Coin requirement")
