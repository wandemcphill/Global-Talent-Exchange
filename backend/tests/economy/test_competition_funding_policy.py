from decimal import Decimal

import pytest

from app.economy.competition_funding_policy import (
    CompetitionFundingMode,
    CompetitionFundingPolicyError,
    validate_competition_funding_contract,
)
from app.models.wallet import LedgerUnit


def test_fancoin_entry_pool_contract_is_non_withdrawable() -> None:
    contract = validate_competition_funding_contract(
        mode=CompetitionFundingMode.FANCOIN_ENTRY_POOL,
        currency=LedgerUnit.CREDIT,
        participant_entry_amount=Decimal("10"),
    )
    assert contract.participants_fund_prize is True
    assert contract.prize_is_withdrawable is False


def test_host_funded_coin_contract_is_withdrawable() -> None:
    contract = validate_competition_funding_contract(
        mode=CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
        currency=LedgerUnit.COIN,
        host_prize_amount=Decimal("100"),
    )
    assert contract.participants_fund_prize is False
    assert contract.prize_is_withdrawable is True


def test_fancoin_pool_rejects_coin_currency() -> None:
    with pytest.raises(CompetitionFundingPolicyError, match="FanCoin/CREDIT"):
        validate_competition_funding_contract(
            mode=CompetitionFundingMode.FANCOIN_ENTRY_POOL,
            currency=LedgerUnit.COIN,
            participant_entry_amount=Decimal("10"),
        )


def test_host_funded_coin_rejects_participant_coin_entry() -> None:
    with pytest.raises(CompetitionFundingPolicyError, match="Participant-funded GTEX Coin"):
        validate_competition_funding_contract(
            mode=CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
            currency=LedgerUnit.COIN,
            participant_entry_amount=Decimal("10"),
            host_prize_amount=Decimal("100"),
        )


def test_host_funded_coin_requires_prize_amount() -> None:
    with pytest.raises(CompetitionFundingPolicyError, match="positive host prize"):
        validate_competition_funding_contract(
            mode=CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
            currency=LedgerUnit.COIN,
            host_prize_amount=Decimal("0"),
        )


def test_fancoin_entry_pool_cannot_also_specify_host_prize() -> None:
    with pytest.raises(CompetitionFundingPolicyError, match="cannot also carry"):
        validate_competition_funding_contract(
            mode=CompetitionFundingMode.FANCOIN_ENTRY_POOL,
            currency=LedgerUnit.CREDIT,
            participant_entry_amount=Decimal("10"),
            host_prize_amount=Decimal("50"),
        )
