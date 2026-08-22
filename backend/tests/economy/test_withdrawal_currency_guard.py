from types import SimpleNamespace

import pytest

from app.models.economic_conversion import _assert_withdrawable_payout_currency
from app.models.wallet import LedgerUnit


def test_fancoin_payout_is_rejected_by_backend_guard() -> None:
    payout = SimpleNamespace(unit=LedgerUnit.CREDIT)
    with pytest.raises(ValueError, match="FanCoin is never withdrawable"):
        _assert_withdrawable_payout_currency(None, None, payout)


def test_gtex_coin_payout_is_accepted_by_backend_guard() -> None:
    payout = SimpleNamespace(unit=LedgerUnit.COIN)
    _assert_withdrawable_payout_currency(None, None, payout)
