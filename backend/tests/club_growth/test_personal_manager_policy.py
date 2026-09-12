import pytest

from app.club_growth.personal_manager_policy import (
    PersonalManagerBand,
    quality_bounds,
    validate_personal_manager_creation,
)


def test_personal_manager_quality_bands_match_product_contract() -> None:
    assert quality_bounds(PersonalManagerBand.BAND_60_70) == (60, 70)
    assert quality_bounds(PersonalManagerBand.BAND_71_80) == (71, 80)
    assert quality_bounds(PersonalManagerBand.BAND_81_90) == (81, 90)
    assert quality_bounds(PersonalManagerBand.BAND_91_95) == (91, 95)
    assert quality_bounds(PersonalManagerBand.BAND_96_99) == (96, 99)


def test_personal_manager_is_single_and_non_transferable() -> None:
    created = validate_personal_manager_creation(
        user_id="user-1",
        quality_band=PersonalManagerBand.BAND_91_95,
        fan_coin_price=1000,
        already_exists=False,
    )
    assert created.permanent
    assert not created.transferable
    assert not created.salary_bearing


def test_second_personal_manager_is_rejected() -> None:
    with pytest.raises(ValueError, match="personal_manager_already_exists"):
        validate_personal_manager_creation(
            user_id="user-1",
            quality_band=PersonalManagerBand.BAND_81_90,
            fan_coin_price=500,
            already_exists=True,
        )


def test_personal_manager_price_must_be_positive() -> None:
    with pytest.raises(ValueError, match="personal_manager_price_must_be_positive"):
        validate_personal_manager_creation(
            user_id="user-1",
            quality_band=PersonalManagerBand.BAND_96_99,
            fan_coin_price=0,
            already_exists=False,
        )
