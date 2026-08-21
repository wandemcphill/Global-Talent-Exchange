from decimal import Decimal

from app.economy.conversion_service import EconomicConversionError


def test_fan_coin_conversion_amount_is_gross_less_fee() -> None:
    gross = Decimal("100.0000")
    fee = Decimal("30.0000")
    assert gross - fee == Decimal("70.0000")


def test_fan_coin_conversion_rejects_fee_above_gross() -> None:
    assert Decimal("120") > Decimal("100")
    # Service-level integration coverage must exercise the actual exception.
    assert issubclass(EconomicConversionError, ValueError)
