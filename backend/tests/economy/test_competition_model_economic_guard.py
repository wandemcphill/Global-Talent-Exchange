from types import SimpleNamespace

import pytest

from app.models.competition import _validate_competition_economic_contract


def _competition(**overrides: object) -> SimpleNamespace:
    values = {
        "prize_mode": "entry_funded",
        "currency": "credit",
        "entry_fee_minor": 100,
        "host_funded_prize_total_minor": 0,
        "host_funding_required_minor": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_model_guard_rejects_participant_funded_coin_entry() -> None:
    with pytest.raises(ValueError, match="entry fees must use FanCoin"):
        _validate_competition_economic_contract(None, None, _competition(currency="coin"))


def test_model_guard_rejects_host_funded_without_coin() -> None:
    with pytest.raises(ValueError, match="must use GTEX Coin"):
        _validate_competition_economic_contract(
            None,
            None,
            _competition(
                prize_mode="host_funded_fixed",
                currency="credit",
                entry_fee_minor=0,
                host_funded_prize_total_minor=100000,
                host_funding_required_minor=130000,
            ),
        )


def test_model_guard_rejects_host_funded_participant_entry_fee() -> None:
    with pytest.raises(ValueError, match="cannot charge a participant Coin entry fee"):
        _validate_competition_economic_contract(
            None,
            None,
            _competition(
                prize_mode="host_funded_fixed",
                currency="coin",
                entry_fee_minor=100,
                host_funded_prize_total_minor=100000,
                host_funding_required_minor=130000,
            ),
        )


def test_model_guard_rejects_host_funded_without_required_amount() -> None:
    with pytest.raises(ValueError, match="require a positive funded prize"):
        _validate_competition_economic_contract(
            None,
            None,
            _competition(
                prize_mode="host_funded_fixed",
                currency="coin",
                entry_fee_minor=0,
                host_funded_prize_total_minor=0,
                host_funding_required_minor=0,
            ),
        )


def test_model_guard_accepts_host_funded_coin_contract() -> None:
    _validate_competition_economic_contract(
        None,
        None,
        _competition(
            prize_mode="host_funded_fixed",
            currency="coin",
            entry_fee_minor=0,
            host_funded_prize_total_minor=100000,
            host_funding_required_minor=130000,
        ),
    )
