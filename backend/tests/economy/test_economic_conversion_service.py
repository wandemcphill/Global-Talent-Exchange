from decimal import Decimal

import pytest

from app.economy.conversion_service import EconomicConversionError, FanCoinGiftConversionService


@pytest.mark.parametrize(
    ("gross", "fee", "destination", "burn"),
    [
        (Decimal("100"), Decimal("30"), Decimal("70"), Decimal("1")),
        (Decimal("100"), Decimal("10"), Decimal("70"), Decimal("10")),
    ],
)
def test_conversion_rejects_non_reconciling_currency_legs(
    gross: Decimal, fee: Decimal, destination: Decimal, burn: Decimal
) -> None:
    service = FanCoinGiftConversionService(session=None)  # validation completes before DB access
    with pytest.raises(EconomicConversionError, match="reconcile exactly"):
        service.convert(
            source_user_id="sender",
            recipient_user_id="recipient",
            gross_fancoin=gross,
            platform_fee_fancoin=fee,
            destination_coin_amount=destination,
            burn_fancoin=burn,
            conversion_key="test-reconcile",
        )


def test_conversion_rejects_self_conversion_before_db_access() -> None:
    service = FanCoinGiftConversionService(session=None)
    with pytest.raises(EconomicConversionError, match="distinct source and recipient"):
        service.convert(
            source_user_id="same-user",
            recipient_user_id="same-user",
            gross_fancoin=Decimal("100"),
            platform_fee_fancoin=Decimal("30"),
            destination_coin_amount=Decimal("70"),
            conversion_key="test-self",
        )


def test_conversion_rejects_zero_destination_before_db_access() -> None:
    service = FanCoinGiftConversionService(session=None)
    with pytest.raises(EconomicConversionError, match="positive destination"):
        service.convert(
            source_user_id="sender",
            recipient_user_id="recipient",
            gross_fancoin=Decimal("100"),
            platform_fee_fancoin=Decimal("100"),
            destination_coin_amount=Decimal("0"),
            conversion_key="test-zero-destination",
        )
